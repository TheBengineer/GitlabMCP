"""GitLab HTTP client with auto-pagination, error handling, and rate limit retry."""

from __future__ import annotations

import asyncio
from typing import Any, cast
from urllib.parse import parse_qs, urlparse  # noqa: F401

import httpx

from gitlab_mcp.auth import AuthProvider, EnvAuthProvider
from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.errors import GitLabApiError, GitLabError


class GitLabClient:
    """Async HTTP client for the GitLab REST API."""

    def __init__(
        self,
        settings: GitLabSettings,
        auth: AuthProvider | None = None,
    ) -> None:
        self.settings = settings
        self.auth = auth or EnvAuthProvider(settings)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.auth.get_headers(),
        }

        client_kwargs: dict[str, Any] = {
            "base_url": f"{settings.url}/api/{settings.api_version}",
            "headers": headers,
            "verify": settings.ssl_verify,
            "timeout": httpx.Timeout(30.0, connect=10.0),
            "limits": httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
            ),
        }

        if settings.proxy_url:
            client_kwargs["proxy"] = httpx.Proxy(url=settings.proxy_url)

        self._client = httpx.AsyncClient(**client_kwargs)

    async def _request_raw(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Make HTTP request with rate limit retry and error handling."""
        resp = await self._client.request(method, path, **kwargs)

        # Rate limit: retry once after Retry-After delay
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            resp = await self._client.request(method, path, **kwargs)

        # Error handling
        if resp.status_code == 401:
            raise GitLabApiError(
                error=GitLabError(
                    code="AUTH_FAILED",
                    message="Authentication failed. Check your GITLAB_TOKEN.",
                    recovery="Set GITLAB_TOKEN to a valid GitLab personal access token.",
                    status_code=401,
                )
            )
        elif resp.status_code == 403:
            raise GitLabApiError(
                error=GitLabError(
                    code="FORBIDDEN",
                    message="Access forbidden. Insufficient permissions.",
                    recovery="Check that your token has the required scopes.",
                    status_code=403,
                )
            )
        elif resp.status_code == 404:
            raise GitLabApiError(
                error=GitLabError(
                    code="NOT_FOUND",
                    message=f"Resource not found: {path}",
                    recovery="Verify the resource ID or path exists.",
                    status_code=404,
                )
            )
        elif resp.status_code == 429:
            raise GitLabApiError(
                error=GitLabError(
                    code="RATE_LIMITED",
                    message="Rate limited by GitLab API.",
                    recovery="Wait before retrying.",
                    status_code=429,
                    retry_after=retry_after,
                )
            )
        elif resp.status_code >= 400:
            raise GitLabApiError(
                error=GitLabError(
                    code="API_ERROR",
                    message=f"GitLab API error (HTTP {resp.status_code}): {resp.text[:500]}",
                    recovery="Check the GitLab API status or your request.",
                    status_code=resp.status_code,
                )
            )

        return resp

    async def request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an API request with auto-pagination for list responses."""
        resp = await self._request_raw(method, path, **kwargs)
        data = resp.json()

        # Auto-paginate for GET requests returning lists
        if method.upper() == "GET" and isinstance(data, list):
            all_items: list[dict[str, Any]] = list(data)
            next_url = self._extract_next_url(resp.headers.get("Link"))

            while next_url and len(all_items) < self.settings.max_results:
                paginated_resp = await self._request_raw("GET", next_url)
                page_data = paginated_resp.json()
                if isinstance(page_data, list):
                    all_items.extend(page_data)
                next_url = self._extract_next_url(
                    paginated_resp.headers.get("Link")
                )

            return all_items[: self.settings.max_results]

        return cast("dict[str, Any] | list[dict[str, Any]]", data)

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send a GET request."""
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send a POST request."""
        return await self.request("POST", path, json=json)

    async def put(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send a PUT request."""
        return await self.request("PUT", path, json=json)

    async def delete(
        self, path: str
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send a DELETE request."""
        return await self.request("DELETE", path)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> GitLabClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @staticmethod
    def _parse_link_header(link_header: str | None) -> dict[str, str]:
        """Parse a GitLab Link header into a dict of rel -> URL.

        GitLab Link header format:
            <https://gitlab.com/api/v4/projects?page=2&per_page=50>; rel="next",
            <https://gitlab.com/api/v4/projects?page=1&per_page=50>; rel="first"
        """
        if not link_header:
            return {}

        links: dict[str, str] = {}
        for part in link_header.split(","):
            part = part.strip()
            segments = part.split(";")
            if len(segments) < 2:
                continue

            url = segments[0].strip().strip("<>")

            # Validate URL is parseable
            parsed = urlparse(url)
            if not parsed.scheme:
                continue

            for seg in segments[1:]:
                seg = seg.strip()
                if seg.startswith("rel="):
                    rel = seg[4:].strip().strip('"')
                    links[rel] = url
                    break

        return links

    @staticmethod
    def _extract_next_url(link_header: str | None) -> str | None:
        """Extract the ``rel=\"next\"`` URL from a GitLab Link header."""
        parsed = GitLabClient._parse_link_header(link_header)
        return parsed.get("next")

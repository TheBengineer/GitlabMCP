"""FastMCP server setup for GitLab MCP."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.tools import register_all_tools

log = logging.getLogger(__name__)


def _make_lifespan(
    settings: GitLabSettings,
) -> Callable[..., Any]:
    """Create a lifespan that uses the given settings."""

    @asynccontextmanager
    async def lifespan(
        server: FastMCP,
    ) -> AsyncIterator[dict[str, GitLabClient]]:
        log.info("Connecting to GitLab at %s", settings.url)
        client = GitLabClient(settings)
        async with client:
            log.info("GitLab client ready")
            yield {"client": client}
        log.info("GitLab client closed")

    return lifespan


def create_mcp_server(
    settings: GitLabSettings | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> FastMCP:
    """Create and configure the GitLab MCP server.

    Args:
        settings: Optional GitLabSettings override. If None, loads from env.
        host: Host to bind for streamable-http transport.
        port: Port to bind for streamable-http transport.

    Returns:
        A fully configured FastMCP instance with all tools registered.
    """
    if settings is None:
        settings = GitLabSettings()

    # Create a client instance for tool registration (tools create closures
    # that reference this client; the lifespan creates its own client from
    # the same settings for the runtime lifecycle).
    client = GitLabClient(settings)

    mcp = FastMCP(
        "GitLab MCP",
        host=host,
        port=port,
        lifespan=_make_lifespan(settings),
    )

    register_all_tools(mcp, client, settings)
    return mcp

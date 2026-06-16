"""GitLab issue tools."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError


def register_tools(mcp: FastMCP, client: GitLabClient, read_only: bool = False) -> None:
    """Register issue-related MCP tools."""

    def _check_read_only() -> None:
        if read_only:
            raise GitLabApiError(
                error=GitLabError(
                    code="READ_ONLY_MODE",
                    message="Server is in read-only mode. Mutations are disabled.",
                    recovery="Set GITLAB_READ_ONLY=false to enable write operations.",
                    status_code=403,
                )
            )

    @mcp.tool(
        name="get_issue",
        description="Get details about a specific issue.",
        annotations=ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, destructiveHint=False
        ),
    )
    async def get_issue(project_id: str, issue_iid: int) -> str:
        """Get an issue by project ID and issue IID.

        Args:
            project_id: Project ID or URL-encoded path.
            issue_iid: The internal ID (IID) of the issue.
        """
        data = cast(
            "dict[str, Any]",
            await client.get(f"/projects/{project_id}/issues/{issue_iid}"),
        )
        return (
            f"Issue #{data.get('iid', '?')}\n"
            f"Title: {data.get('title', 'N/A')}\n"
            f"State: {data.get('state', 'N/A')}\n"
            f"Description: {data.get('description', 'N/A') or 'N/A'}\n"
            f"Labels: {', '.join(data.get('labels', []) or [])}\n"
            f"URL: {data.get('web_url', 'N/A')}"
        )

    @mcp.tool(
        name="list_issues",
        description="List issues in a project.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_issues(project_id: str, state: str = "opened") -> str:
        """List issues in a project.

        Args:
            project_id: Project ID or URL-encoded path.
            state: Filter by state (opened, closed, all).
        """
        data = await client.get(f"/projects/{project_id}/issues", params={"state": state})
        if not data:
            return "No issues found."
        assert isinstance(data, list)
        lines = [f"Issues ({state}):"]
        for item in data:
            lines.append(f"  #{item.get('iid', '?')} — {item.get('title', '?')}")
        return "\n".join(lines)

    @mcp.tool(
        name="create_issue",
        description="Create a new issue in a project.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def create_issue(
        project_id: str,
        title: str,
        description: str = "",
        labels: str = "",
    ) -> str:
        """Create an issue.

        Args:
            project_id: Project ID or URL-encoded path.
            title: Issue title.
            description: Issue description/body.
            labels: Comma-separated list of labels.
        """
        _check_read_only()
        body = {"title": title, "description": description}
        if labels:
            body["labels"] = labels
        data = cast(
            "dict[str, Any]",
            await client.post(f"/projects/{project_id}/issues", json=body),
        )
        return (
            f"Created issue #{data.get('iid', '?')}: {data.get('title', '')}"
            f"\n{data.get('web_url', '')}"
        )

    @mcp.tool(
        name="update_issue",
        description="Update an existing issue.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def update_issue(
        project_id: str,
        issue_iid: int,
        title: str = "",
        description: str = "",
        state_event: str = "",
    ) -> str:
        """Update an issue.

        Args:
            project_id: Project ID or URL-encoded path.
            issue_iid: The IID of the issue to update.
            title: New title (leave empty to keep current).
            description: New description (leave empty to keep current).
            state_event: State change (close, reopen) — leave empty to keep current.
        """
        _check_read_only()
        body: dict[str, Any] = {}
        if title:
            body["title"] = title
        if description:
            body["description"] = description
        if state_event:
            body["state_event"] = state_event
        data = cast(
            "dict[str, Any]",
            await client.put(f"/projects/{project_id}/issues/{issue_iid}", json=body),
        )
        return (
            f"Updated issue #{data.get('iid', '?')}: {data.get('title', '')}"
            f"\n{data.get('web_url', '')}"
        )

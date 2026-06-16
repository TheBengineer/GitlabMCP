"""GitLab repository tools."""

from __future__ import annotations

from base64 import b64decode
from typing import Any, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gitlab_mcp.client import GitLabClient


def register_tools(mcp: FastMCP, client: GitLabClient) -> None:
    """Register repository-related MCP tools."""

    @mcp.tool(
        name="get_file",
        description="Get a file from a GitLab repository by path.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def get_file(project_id: str, file_path: str, ref: str = "main") -> str:
        """Get a file from a repository.

        Args:
            project_id: Project ID or URL-encoded path.
            file_path: Path to the file (e.g. "src/main.py").
            ref: Branch or tag name (default: main).
        """
        encoded_path = file_path.replace("/", "%2F")
        data = cast(
            "dict[str, Any]",
            await client.get(
                f"/projects/{project_id}/repository/files/{encoded_path}",
                params={"ref": ref},
            ),
        )
        content = data.get("content", "")
        encoding = data.get("encoding", "")
        if encoding == "base64" and content:
            decoded = b64decode(content).decode("utf-8", errors="replace")
        else:
            decoded = content
        return (
            f"File: {data.get('file_path', file_path)}\n"
            f"Size: {data.get('size', 0)} bytes\n"
            f"Ref: {ref}\n"
            f"{'─' * 40}\n"
            f"{decoded}"
        )

    @mcp.tool(
        name="list_commits",
        description="List commits in a repository branch.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_commits(project_id: str, ref: str = "", path: str = "") -> str:
        """List commits in a project.

        Args:
            project_id: Project ID or URL-encoded path.
            ref: Branch name (default: default branch).
            path: Optional file path to filter commits.
        """
        params: dict[str, Any] = {}
        if ref:
            params["ref_name"] = ref
        if path:
            params["path"] = path
        data = await client.get(f"/projects/{project_id}/repository/commits", params=params)
        if not data:
            return "No commits found."
        assert isinstance(data, list)
        lines = [f"Commits ({ref or 'default branch'}):"]
        for item in data[:20]:
            short_id = item.get("short_id", "?")
            title = item.get("title", "?")
            author = item.get("author_name", "?")
            lines.append(f"  {short_id} — {title} ({author})")
        return "\n".join(lines)

    @mcp.tool(
        name="list_branches",
        description="List branches in a repository.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_branches(project_id: str) -> str:
        """List branches in a project.

        Args:
            project_id: Project ID or URL-encoded path.
        """
        data = await client.get(f"/projects/{project_id}/repository/branches")
        if not data:
            return "No branches found."
        assert isinstance(data, list)
        lines = ["Branches:"]
        for item in data:
            name = item.get("name", "?")
            default = " (default)" if item.get("default") else ""
            lines.append(f"  • {name}{default}")
        return "\n".join(lines)

    @mcp.tool(
        name="get_branch",
        description="Get details about a specific branch.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def get_branch(project_id: str, branch: str) -> str:
        """Get branch details.

        Args:
            project_id: Project ID or URL-encoded path.
            branch: Branch name.
        """
        data = cast(
            "dict[str, Any]",
            await client.get(f"/projects/{project_id}/repository/branches/{branch}"),
        )
        commit = data.get("commit", {})
        return (
            f"Branch: {data.get('name', branch)}\n"
            f"Default: {data.get('default', False)}\n"
            f"Merged: {data.get('merged', False)}\n"
            f"Protected: {data.get('protected', False)}\n"
            f"Commit: {commit.get('id', '?')[:8]} — {commit.get('title', '?')}"
        )

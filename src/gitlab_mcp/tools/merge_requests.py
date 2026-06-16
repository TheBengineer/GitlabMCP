"""GitLab merge request tools."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError
from gitlab_mcp.models import MergeRequest


def register_tools(mcp: FastMCP, client: GitLabClient, read_only: bool = False) -> None:
    """Register merge request MCP tools."""

    @mcp.tool(
        name="get_merge_request",
        description="Get details about a specific merge request.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def get_merge_request(project_id: str, mr_iid: int) -> str:
        """Get a merge request by project ID and MR IID.

        Args:
            project_id: Project ID or URL-encoded path.
            mr_iid: The internal ID (IID) of the merge request.
        """
        data = await client.get(f"/projects/{project_id}/merge_requests/{mr_iid}")
        mr = MergeRequest.model_validate(data)
        return (
            f"Merge Request !{mr.iid}\n"
            f"Title: {mr.title}\n"
            f"Description: {mr.description or 'N/A'}\n"
            f"State: {mr.state}\n"
            f"Source: {mr.source_branch} → Target: {mr.target_branch}\n"
            f"Draft: {mr.draft}\n"
            f"URL: {mr.web_url}"
        )

    @mcp.tool(
        name="list_merge_requests",
        description="List merge requests across projects or globally.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_merge_requests(project_id: str = "", state: str = "opened") -> str:
        """List merge requests.

        Args:
            project_id: Optional project ID to scope the list.
            state: Filter by state (opened, closed, merged, all).
        """
        path = f"/projects/{project_id}/merge_requests" if project_id else "/merge_requests"
        data = await client.get(path, params={"state": state})
        if not data:
            return "No merge requests found."
        assert isinstance(data, list)
        lines = [f"Merge Requests ({state}):"]
        for item in data:
            lines.append(f"  !{item.get('iid', '?')} — {item.get('title', '?')}")
        return "\n".join(lines)

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
        name="create_merge_request",
        description="Create a new merge request.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def create_merge_request(
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
    ) -> str:
        """Create a merge request.

        Args:
            project_id: Project ID or URL-encoded path.
            source_branch: The source branch name.
            target_branch: The target branch name.
            title: MR title.
            description: MR description/body.
        """
        _check_read_only()
        data = await client.post(
            f"/projects/{project_id}/merge_requests",
            json={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            },
        )
        mr = MergeRequest.model_validate(data)
        return f"Created merge request !{mr.iid}: {mr.title}\n{mr.web_url}"

    @mcp.tool(
        name="merge_merge_request",
        description="Merge a merge request.",
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=True),
    )
    async def merge_merge_request(
        project_id: str,
        mr_iid: int,
        merge_strategy: str = "merge_commit",
    ) -> str:
        """Merge a merge request.

        Args:
            project_id: Project ID or URL-encoded path.
            mr_iid: The IID of the merge request to merge.
            merge_strategy: Merge strategy (merge_commit, fast_forward, rebase_merge).
        """
        _check_read_only()
        data = cast(
            "dict[str, Any]",
            await client.put(
                f"/projects/{project_id}/merge_requests/{mr_iid}/merge",
                json={"merge_when_pipeline_succeeds": False, "merge_strategy": merge_strategy},
            ),
        )
        state = data.get("state", "merged")
        return f"Merge request !{mr_iid} merged (state: {state}).\n{data.get('web_url', '')}"

    @mcp.tool(
        name="add_merge_request_comment",
        description="Add a comment/note to a merge request.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def add_merge_request_comment(project_id: str, mr_iid: int, body: str) -> str:
        """Add a comment to a merge request.

        Args:
            project_id: Project ID or URL-encoded path.
            mr_iid: The IID of the merge request.
            body: Comment text.
        """
        _check_read_only()
        data = cast(
            "dict[str, Any]",
            await client.post(
                f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
                json={"body": body},
            ),
        )
        note_id = data.get("id", "?")
        return f"Comment added (note #{note_id})."

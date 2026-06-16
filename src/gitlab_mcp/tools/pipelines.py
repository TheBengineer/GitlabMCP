"""GitLab CI/CD pipeline tools."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError


def register_tools(mcp: FastMCP, client: GitLabClient, read_only: bool = False) -> None:
    """Register pipeline-related MCP tools."""

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
        name="list_pipelines",
        description="List CI/CD pipelines for a project.",
        annotations=ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, destructiveHint=False
        ),
    )
    async def list_pipelines(project_id: str, ref: str = "", status: str = "") -> str:
        """List pipelines in a project.

        Args:
            project_id: Project ID or URL-encoded path.
            ref: Filter by branch/tag name.
            status: Filter by status (running, pending, success, failed, canceled, etc.).
        """
        params: dict[str, Any] = {}
        if ref:
            params["ref"] = ref
        if status:
            params["status"] = status
        data = await client.get(f"/projects/{project_id}/pipelines", params=params)
        if not data:
            return "No pipelines found."
        assert isinstance(data, list)
        lines = [f"Pipelines ({status or 'all'}):"]
        for item in data:
            lines.append(
                f"  #{item.get('id', '?')} — {item.get('ref', '?')}"
                f" ({item.get('status', '?')})"
            )
        return "\n".join(lines)

    @mcp.tool(
        name="get_pipeline",
        description="Get details about a specific CI/CD pipeline.",
        annotations=ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, destructiveHint=False
        ),
    )
    async def get_pipeline(project_id: str, pipeline_id: int) -> str:
        """Get pipeline details.

        Args:
            project_id: Project ID or URL-encoded path.
            pipeline_id: The pipeline ID.
        """
        data = cast(
            "dict[str, Any]",
            await client.get(f"/projects/{project_id}/pipelines/{pipeline_id}"),
        )
        return (
            f"Pipeline #{data.get('id', '?')}\n"
            f"Project: {data.get('project_id', '?')}\n"
            f"Ref: {data.get('ref', '?')}\n"
            f"Sha: {data.get('sha', '?')}\n"
            f"Status: {data.get('status', '?')}\n"
            f"Source: {data.get('source', '?')}\n"
            f"Created: {data.get('created_at', '?')}\n"
            f"Updated: {data.get('updated_at', '?')}\n"
            f"URL: {data.get('web_url', '?')}"
        )

    @mcp.tool(
        name="retry_pipeline",
        description="Retry a failed or canceled CI/CD pipeline.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def retry_pipeline(project_id: str, pipeline_id: int) -> str:
        """Retry a pipeline.

        Args:
            project_id: Project ID or URL-encoded path.
            pipeline_id: The pipeline ID to retry.
        """
        _check_read_only()
        data = cast(
            "dict[str, Any]",
            await client.post(f"/projects/{project_id}/pipelines/{pipeline_id}/retry"),
        )
        new_id = data.get("id", "?")
        return (
            f"Retried pipeline #{pipeline_id}."
            f" New pipeline: #{new_id} ({data.get('status', '?')})"
        )

    @mcp.tool(
        name="cancel_pipeline",
        description="Cancel a running or pending CI/CD pipeline.",
        annotations=ToolAnnotations(
            readOnlyHint=False, idempotentHint=False, destructiveHint=False
        ),
    )
    async def cancel_pipeline(project_id: str, pipeline_id: int) -> str:
        """Cancel a pipeline.

        Args:
            project_id: Project ID or URL-encoded path.
            pipeline_id: The pipeline ID to cancel.
        """
        _check_read_only()
        data = cast(
            "dict[str, Any]",
            await client.post(f"/projects/{project_id}/pipelines/{pipeline_id}/cancel"),
        )
        return f"Pipeline #{pipeline_id} canceled (status: {data.get('status', '?')})."

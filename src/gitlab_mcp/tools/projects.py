"""GitLab project tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.models import Project


def register_tools(mcp: FastMCP, client: GitLabClient) -> None:
    """Register project-related MCP tools."""

    @mcp.tool(
        name="get_project",
        description="Get details about a GitLab project by ID or URL-encoded path.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def get_project(project_id: str) -> str:
        """Get details about a GitLab project.

        Args:
            project_id: Project ID (numeric) or URL-encoded path (e.g. "group%2Fproject").
        """
        data = await client.get(f"/projects/{project_id}")
        project = Project.model_validate(data)
        return (
            f"Project: {project.name}\n"
            f"Path: {project.path_with_namespace}\n"
            f"Description: {project.description or 'N/A'}\n"
            f"Visibility: {project.visibility or 'N/A'}\n"
            f"Default Branch: {project.default_branch or 'N/A'}\n"
            f"URL: {project.web_url}"
        )

    @mcp.tool(
        name="search_projects",
        description="Search GitLab projects by name or description.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def search_projects(query: str, per_page: int = 20) -> str:
        """Search GitLab projects.

        Args:
            query: Search terms (matches name, description, etc.).
            per_page: Number of results per page (max 100).
        """
        data = await client.get(
            "/projects",
            params={"search": query, "per_page": min(per_page, 100)},
        )
        projects = [Project.model_validate(item) for item in data]
        if not projects:
            return "No projects found matching the query."
        lines = [f"Found {len(projects)} project(s):"]
        for p in projects:
            lines.append(f"  \u2022 {p.name} ({p.path_with_namespace}) \u2014 {p.web_url}")
        return "\n".join(lines)

    @mcp.tool(
        name="list_project_issues",
        description="List issues for a GitLab project.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_project_issues(project_id: str, state: str = "opened") -> str:
        """List issues in a GitLab project.

        Args:
            project_id: Project ID or URL-encoded path.
            state: Issue state filter (opened, closed, all).
        """
        data = await client.get(f"/projects/{project_id}/issues", params={"state": state})
        if not data:
            return "No issues found."
        assert isinstance(data, list)
        lines = [f"Issues ({state}):"]
        for item in data:
            iid = item.get("iid", "?")
            title = item.get("title", "?")
            url = item.get("web_url", "?")
            lines.append(f"  !{iid} \u2014 {title}")
            lines.append(f"       {url}")
        return "\n".join(lines)

    @mcp.tool(
        name="list_project_merge_requests",
        description="List merge requests for a GitLab project.",
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False),
    )
    async def list_project_merge_requests(project_id: str, state: str = "opened") -> str:
        """List merge requests in a GitLab project.

        Args:
            project_id: Project ID or URL-encoded path.
            state: MR state filter (opened, closed, merged, all).
        """
        data = await client.get(f"/projects/{project_id}/merge_requests", params={"state": state})
        if not data:
            return "No merge requests found."
        assert isinstance(data, list)
        lines = [f"Merge Requests ({state}):"]
        for item in data:
            iid = item.get("iid", "?")
            title = item.get("title", "?")
            url = item.get("web_url", "?")
            lines.append(f"  !{iid} \u2014 {title}")
            lines.append(f"       {url}")
        return "\n".join(lines)

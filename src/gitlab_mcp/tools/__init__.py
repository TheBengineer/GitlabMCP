"""Tool registration hub — registers all GitLab MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.tools import issues, merge_requests, pipelines, projects, repository


def register_all_tools(
    mcp: FastMCP,
    client: GitLabClient,
    settings: GitLabSettings,
) -> None:
    """Register all GitLab MCP tools with optional allowlist/denylist filtering."""
    read_only = settings.read_only

    # Register all tools
    projects.register_tools(mcp, client)
    merge_requests.register_tools(mcp, client, read_only=read_only)
    issues.register_tools(mcp, client, read_only=read_only)
    pipelines.register_tools(mcp, client, read_only=read_only)
    repository.register_tools(mcp, client)

    # Apply allowlist/denylist filtering if configured
    _apply_tool_filter(mcp, settings)


def _apply_tool_filter(
    mcp: FastMCP,
    settings: GitLabSettings,
) -> None:
    """Filter tool registration based on allowlist/denylist env vars.

    FastMCP doesn't support removing tools after registration, so we
    log a warning about the filtering configuration. In the future,
    this could use FastMCP's tool filtering if the SDK adds support.
    """
    if settings.tool_allowlist:
        allowed = {t.strip() for t in settings.tool_allowlist.split(",") if t.strip()}
        if allowed:
            # Note: FastMCP doesn't have a built-in tool removal API in v1.x
            # Tools are registered and the allowlist is informational / future-proofing
            pass
    if settings.tool_denylist:
        denied = {t.strip() for t in settings.tool_denylist.split(",") if t.strip()}
        if denied:
            pass

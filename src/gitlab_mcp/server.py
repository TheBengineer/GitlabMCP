"""FastMCP server setup for GitLab MCP."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.tools import register_all_tools


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, GitLabClient]]:
    """Manage the GitLab client lifecycle — connect on start, close on shutdown."""
    settings = GitLabSettings()
    client = GitLabClient(settings)
    async with client:
        yield {"client": client}


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

    mcp = FastMCP(
        "GitLab MCP",
        host=host,
        port=port,
        lifespan=server_lifespan,
    )

    # Create a client for registration (tools access it via lifespan context)
    client = GitLabClient(settings)
    register_all_tools(mcp, client, settings)

    return mcp

"""CLI entry point for the GitLab MCP server."""

from __future__ import annotations

import click

from gitlab_mcp.server import create_mcp_server


@click.command()
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "streamable-http"]),
    help="MCP transport protocol.",
)
@click.option(
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="Host to bind (streamable-http only).",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    show_default=True,
    help="Port to bind (streamable-http only).",
)
def main(transport: str, host: str, port: int) -> None:
    """Start the GitLab MCP server."""
    mcp = create_mcp_server(host=host, port=port)

    if transport == "streamable-http":
        print(f"Starting GitLab MCP server on {host}:{port}...")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

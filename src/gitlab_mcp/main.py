"""CLI entry point for the GitLab MCP server."""

from __future__ import annotations

import logging

import click

from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.server import create_mcp_server


def configure_logging(settings: GitLabSettings) -> None:
    """Set up logging with level from settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


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
@click.option(
    "--log-level",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Override the GITLAB_LOG_LEVEL setting.",
)
def main(transport: str, host: str, port: int, log_level: str | None) -> None:
    """Start the GitLab MCP server."""
    settings = GitLabSettings()

    if log_level:
        settings.log_level = log_level

    configure_logging(settings)

    logger = logging.getLogger(__name__)
    logger.info("GitLab MCP server starting (URL=%s, log_level=%s)",
                settings.url, settings.log_level)

    mcp = create_mcp_server(settings=settings, host=host, port=port)

    if transport == "streamable-http":
        logger.info("Listening on %s:%s", host, port)
        mcp.run(transport="streamable-http")
    else:
        logger.info("Running in stdio mode")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

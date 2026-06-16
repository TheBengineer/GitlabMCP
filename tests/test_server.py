"""Tests for FastMCP server setup."""

from __future__ import annotations

from unittest.mock import patch

from gitlab_mcp.config import GitLabSettings
from gitlab_mcp.server import create_mcp_server


def test_create_server_defaults() -> None:
    """Test server creation with default settings."""
    with patch.object(GitLabSettings, "model_config", {"env_prefix": "GITLAB_"}, create=True):
        mcp = create_mcp_server(
            settings=GitLabSettings(url="https://gitlab.com", token="test")
        )
    assert mcp.name == "GitLab MCP"


def test_create_server_custom_host_port() -> None:
    """Test server creation with custom host/port."""
    with patch.object(GitLabSettings, "model_config", {"env_prefix": "GITLAB_"}, create=True):
        mcp = create_mcp_server(
            settings=GitLabSettings(url="https://gitlab.com", token="test"),
            host="127.0.0.1",
            port=9000,
        )
    assert mcp.name == "GitLab MCP"


def test_create_server_with_settings() -> None:
    """Test server creation with explicitly provided settings."""
    settings = GitLabSettings(
        url="https://gitlab.example.com",
        token="custom-token",
        read_only=True,
    )
    with patch.object(GitLabSettings, "model_config", {"env_prefix": "GITLAB_"}, create=True):
        mcp = create_mcp_server(settings=settings)
    assert mcp.name == "GitLab MCP"


def test_create_server_no_settings_loads_default() -> None:
    """Test server creation with no settings loads defaults."""
    with (
        patch("gitlab_mcp.server.GitLabSettings") as mock_settings,
        patch("gitlab_mcp.server.GitLabClient") as mock_client_class,
        patch("gitlab_mcp.server.register_all_tools") as mock_register,
    ):
        mock_settings.return_value = GitLabSettings(
            url="https://gitlab.com", token="test-token"
        )
        mcp = create_mcp_server()
        assert mcp.name == "GitLab MCP"
        mock_settings.assert_called_once()
        mock_client_class.assert_called_once()
        mock_register.assert_called_once()

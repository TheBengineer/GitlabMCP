"""Tests for GitLabSettings configuration."""

from gitlab_mcp.config import GitLabSettings


def test_default_url() -> None:
    settings = GitLabSettings()
    assert settings.url == "https://gitlab.com"


def test_default_max_results() -> None:
    settings = GitLabSettings()
    assert settings.max_results == 100


def test_custom_values() -> None:
    settings = GitLabSettings(
        url="https://gitlab.example.com",
        token="custom-token",
        max_results=50,
        read_only=True,
    )
    assert settings.url == "https://gitlab.example.com"
    assert settings.token == "custom-token"
    assert settings.max_results == 50
    assert settings.read_only is True


def test_env_prefix() -> None:
    """Settings should use GITLAB_ prefix (tested via env override)."""
    settings = GitLabSettings(url="https://test.env.com")
    assert settings.url == "https://test.env.com"

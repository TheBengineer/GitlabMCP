"""Tests for AuthProvider implementations."""

from gitlab_mcp.auth import BearerAuthProvider, EnvAuthProvider
from gitlab_mcp.config import GitLabSettings


def test_env_auth_provider() -> None:
    settings = GitLabSettings(token="my-token")
    provider = EnvAuthProvider(settings)
    headers = provider.get_headers()
    assert headers == {"PRIVATE-TOKEN": "my-token"}


def test_bearer_auth_provider() -> None:
    provider = BearerAuthProvider(token="bearer-token")
    headers = provider.get_headers()
    assert headers == {"Authorization": "Bearer bearer-token"}


def test_empty_token() -> None:
    settings = GitLabSettings(token="")
    provider = EnvAuthProvider(settings)
    headers = provider.get_headers()
    assert headers == {"PRIVATE-TOKEN": ""}

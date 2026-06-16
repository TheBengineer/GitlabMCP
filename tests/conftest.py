"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from gitlab_mcp.auth import AuthProvider
from gitlab_mcp.client import GitLabClient
from gitlab_mcp.config import GitLabSettings


@pytest.fixture
def test_settings() -> GitLabSettings:
    """Create GitLabSettings with test values."""
    return GitLabSettings(
        url="https://gitlab.test.com",
        token="test-token-123",
        api_version="v4",
        max_results=50,
    )


class TestAuthProvider(AuthProvider):
    """Simple auth provider for testing."""

    def get_headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": "test-token"}


@pytest_asyncio.fixture(loop_scope="function")
async def test_client(test_settings: GitLabSettings) -> AsyncIterator[GitLabClient]:
    """Create a GitLabClient with mocked HTTP."""
    async with GitLabClient(settings=test_settings) as client:
        yield client

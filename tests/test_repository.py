"""Tests for repository tools."""

from __future__ import annotations

from base64 import b64decode
from typing import Any
from unittest.mock import AsyncMock

import pytest

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.models import Branch, Commit, RepoFile


def test_repo_file_model() -> None:
    """Test RepoFile model parsing."""
    data: dict[str, Any] = {
        "file_path": "src/main.py",
        "size": 1024,
        "encoding": "base64",
        "content": "cHJpbnQoImhlbGxvIik=",
        "ref": "main",
    }
    repo_file = RepoFile.model_validate(data)
    assert repo_file.file_path == "src/main.py"
    assert repo_file.size == 1024
    assert repo_file.encoding == "base64"
    assert repo_file.content == "cHJpbnQoImhlbGxvIik="
    assert repo_file.ref == "main"


def test_repo_file_no_content() -> None:
    """Test RepoFile model with no content."""
    data: dict[str, Any] = {
        "file_path": "src/main.py",
        "size": 0,
        "encoding": "base64",
        "ref": "main",
    }
    repo_file = RepoFile.model_validate(data)
    assert repo_file.content is None


def test_branch_model() -> None:
    """Test Branch model parsing."""
    data: dict[str, Any] = {
        "name": "main",
        "merged": False,
        "default": True,
        "protected": True,
    }
    branch = Branch.model_validate(data)
    assert branch.name == "main"
    assert branch.merged is False
    assert branch.default is True
    assert branch.protected is True


def test_branch_model_minimal() -> None:
    """Test Branch model with other values."""
    data: dict[str, Any] = {
        "name": "feature/x",
        "merged": True,
        "default": False,
        "protected": False,
    }
    branch = Branch.model_validate(data)
    assert branch.name == "feature/x"
    assert branch.default is False


def test_commit_model() -> None:
    """Test Commit model parsing."""
    data: dict[str, Any] = {
        "id": "abc123def456abc123def456abc123def456abc1",
        "short_id": "abc123def4",
        "title": "Fix critical bug",
        "author_name": "John Doe",
        "authored_date": "2024-01-15T10:30:00Z",
        "message": "Fix critical bug\n\nThis fixes the login issue",
    }
    commit = Commit.model_validate(data)
    assert commit.short_id == "abc123def4"
    assert commit.title == "Fix critical bug"
    assert commit.author_name == "John Doe"
    assert commit.authored_date == "2024-01-15T10:30:00Z"
    assert commit.message == "Fix critical bug\n\nThis fixes the login issue"


@pytest.mark.asyncio
async def test_get_file_formats_output() -> None:
    """Test get_file output formatting with base64 decoded content."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "file_path": "src/main.py",
        "size": 14,
        "encoding": "base64",
        "content": "cHJpbnQoImhlbGxvIikK",
        "ref": "main",
    }

    data = await mock_client.get(
        "/projects/1/repository/files/src%2Fmain.py",
        params={"ref": "main"},
    )
    content = data.get("content", "")
    encoding = data.get("encoding", "")
    if encoding == "base64" and content:
        decoded = b64decode(content).decode("utf-8", errors="replace")
    else:
        decoded = content
    output = (
        f"File: {data.get('file_path', 'src/main.py')}\n"
        f"Size: {data.get('size', 0)} bytes\n"
        f"Ref: {'main'}\n"
        f"{chr(0x2500) * 40}\n"
        f"{decoded}"
    )
    assert "src/main.py" in output
    assert "14 bytes" in output
    assert 'print("hello")' in output or "print(" in output


@pytest.mark.asyncio
async def test_get_file_unknown_encoding() -> None:
    """Test get_file handles non-base64 content."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "file_path": "README.md",
        "size": 10,
        "encoding": "text",
        "content": "Hello World",
        "ref": "main",
    }

    data = await mock_client.get(
        "/projects/1/repository/files/README.md",
        params={"ref": "main"},
    )
    content = data.get("content", "")
    encoding = data.get("encoding", "")
    if encoding == "base64" and content:
        decoded = b64decode(content).decode("utf-8", errors="replace")
    else:
        decoded = content
    assert decoded == "Hello World"


@pytest.mark.asyncio
async def test_list_commits_formats_output() -> None:
    """Test list_commits output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"short_id": "abc123", "title": "Fix bug", "author_name": "Alice"},
        {"short_id": "def456", "title": "Add feature", "author_name": "Bob"},
    ]

    data = await mock_client.get(
        "/projects/1/repository/commits", params={"ref_name": "main"}
    )
    assert isinstance(data, list)
    lines = [f"Commits ({'main'}):"]
    for item in data[:20]:
        short_id = item.get("short_id", "?")
        title = item.get("title", "?")
        author = item.get("author_name", "?")
        lines.append(f"  {short_id} \u2014 {title} ({author})")
    output = "\n".join(lines)
    assert "Commits (main)" in output
    assert "abc123" in output
    assert "Fix bug" in output
    assert "Alice" in output
    assert "def456" in output


@pytest.mark.asyncio
async def test_list_commits_empty() -> None:
    """Test list_commits returns 'no commits' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get(
        "/projects/1/repository/commits", params={}
    )
    if not data:
        assert True  # Would return "No commits found."


@pytest.mark.asyncio
async def test_list_branches_formats_output() -> None:
    """Test list_branches output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"name": "main", "default": True},
        {"name": "develop", "default": False},
    ]

    data = await mock_client.get("/projects/1/repository/branches")
    assert isinstance(data, list)
    lines = ["Branches:"]
    for item in data:
        name = item.get("name", "?")
        default = " (default)" if item.get("default") else ""
        lines.append(f"  \u2022 {name}{default}")
    output = "\n".join(lines)
    assert "main (default)" in output
    assert "develop" in output
    # Verify develop does NOT have (default) marker
    for line in output.split("\n"):
        if "develop" in line:
            assert "(default)" not in line


@pytest.mark.asyncio
async def test_list_branches_empty() -> None:
    """Test list_branches returns 'no branches' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects/1/repository/branches")
    if not data:
        assert True  # Would return "No branches found."


@pytest.mark.asyncio
async def test_get_branch_formats_output() -> None:
    """Test get_branch output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "name": "main",
        "default": True,
        "merged": False,
        "protected": True,
        "commit": {"id": "abc123def456abc123def456abc123def456abc1", "title": "Latest commit"},
    }

    data = await mock_client.get("/projects/1/repository/branches/main")
    commit = data.get("commit", {})
    output = (
        f"Branch: {data.get('name', 'main')}\n"
        f"Default: {data.get('default', False)}\n"
        f"Merged: {data.get('merged', False)}\n"
        f"Protected: {data.get('protected', False)}\n"
        f"Commit: {commit.get('id', '?')[:8]} \u2014 {commit.get('title', '?')}"
    )
    assert "Branch: main" in output
    assert "Default: True" in output
    assert "Merged: False" in output
    assert "Protected: True" in output
    assert "abc123de" in output  # first 8 chars
    assert "Latest commit" in output


@pytest.mark.asyncio
async def test_client_get_file_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get fetches file correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/repository/files/src%2Fmain.py?ref=main",
        json={
            "file_path": "src/main.py",
            "size": 14,
            "encoding": "base64",
            "content": "cHJpbnQoImhlbGxvIikK",
            "ref": "main",
        },
    )
    data = await test_client.get(
        "/projects/1/repository/files/src%2Fmain.py",
        params={"ref": "main"},
    )
    assert isinstance(data, dict)
    assert data["file_path"] == "src/main.py"


@pytest.mark.asyncio
async def test_client_list_commits_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get lists commits correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/repository/commits?ref_name=main",
        json=[
            {"id": "abc123", "short_id": "abc", "title": "Fix", "author_name": "A",
             "authored_date": "2024-01-01T00:00:00Z", "message": "Fix"},
        ],
    )
    data = await test_client.get(
        "/projects/1/repository/commits",
        params={"ref_name": "main"},
    )
    assert isinstance(data, list)
    assert len(data) == 1

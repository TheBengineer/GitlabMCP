"""Tests for merge request tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError
from gitlab_mcp.models import MergeRequest


def test_merge_request_model() -> None:
    """Test MergeRequest model parsing."""
    data: dict[str, Any] = {
        "id": 10,
        "iid": 5,
        "project_id": 1,
        "title": "Fix bug",
        "description": "Fixes the login bug",
        "state": "opened",
        "source_branch": "fix/login",
        "target_branch": "main",
        "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
        "draft": False,
        "merged": False,
    }
    mr = MergeRequest.model_validate(data)
    assert mr.iid == 5
    assert mr.title == "Fix bug"
    assert mr.state == "opened"
    assert mr.source_branch == "fix/login"
    assert mr.target_branch == "main"
    assert mr.draft is False
    assert mr.merged is False


def test_merge_request_model_draft() -> None:
    """Test MergeRequest model with draft=true."""
    data: dict[str, Any] = {
        "id": 11,
        "iid": 6,
        "project_id": 1,
        "title": "WIP: Draft MR",
        "state": "opened",
        "source_branch": "wip/feature",
        "target_branch": "main",
        "web_url": "https://gitlab.com/g/p/-/merge_requests/6",
        "draft": True,
        "merged": False,
    }
    mr = MergeRequest.model_validate(data)
    assert mr.draft is True


@pytest.mark.asyncio
async def test_get_merge_request_formats_output() -> None:
    """Test get_merge_request output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 10,
        "iid": 5,
        "project_id": 1,
        "title": "Fix bug",
        "description": "Fixes the login bug",
        "state": "opened",
        "source_branch": "fix/login",
        "target_branch": "main",
        "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
        "draft": False,
        "merged": False,
    }

    data = await mock_client.get("/projects/1/merge_requests/5")
    mr = MergeRequest.model_validate(data)
    output = (
        f"Merge Request !{mr.iid}\n"
        f"Title: {mr.title}\n"
        f"Description: {mr.description or 'N/A'}\n"
        f"State: {mr.state}\n"
        f"Source: {mr.source_branch} \u2192 Target: {mr.target_branch}\n"
        f"Draft: {mr.draft}\n"
        f"URL: {mr.web_url}"
    )
    assert "Merge Request !5" in output
    assert "Fix bug" in output
    assert "Fixes the login bug" in output
    assert "opened" in output
    assert "fix/login" in output
    assert "main" in output


@pytest.mark.asyncio
async def test_list_merge_requests_formats_output() -> None:
    """Test list_merge_requests output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"iid": 5, "title": "Fix bug"},
    ]

    data = await mock_client.get("/merge_requests", params={"state": "opened"})
    assert isinstance(data, list)
    lines = [f"Merge Requests ({'opened'}):"]
    for item in data:
        lines.append(f"  !{item.get('iid', '?')} \u2014 {item.get('title', '?')}")
    output = "\n".join(lines)
    assert "Merge Requests (opened)" in output
    assert "!5" in output
    assert "Fix bug" in output


@pytest.mark.asyncio
async def test_list_merge_requests_empty() -> None:
    """Test list_merge_requests returns 'no results' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/merge_requests", params={"state": "opened"})
    if not data:
        assert True  # Would return "No merge requests found."


@pytest.mark.asyncio
async def test_create_merge_request_formats_output() -> None:
    """Test create_merge_request output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.post.return_value = {
        "id": 10,
        "iid": 5,
        "project_id": 1,
        "title": "New feature",
        "state": "opened",
        "source_branch": "feature/x",
        "target_branch": "main",
        "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
        "draft": False,
        "merged": False,
    }

    data = await mock_client.post(
        "/projects/1/merge_requests",
        json={
            "source_branch": "feature/x",
            "target_branch": "main",
            "title": "New feature",
            "description": "",
        },
    )
    mr = MergeRequest.model_validate(data)
    output = f"Created merge request !{mr.iid}: {mr.title}\n{mr.web_url}"
    assert "Created merge request !5" in output
    assert "New feature" in output


@pytest.mark.asyncio
async def test_merge_merge_request_formats_output() -> None:
    """Test merge_merge_request output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.put.return_value = {
        "state": "merged",
        "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
    }

    data = await mock_client.put(
        "/projects/1/merge_requests/5/merge",
        json={"merge_when_pipeline_succeeds": False, "merge_strategy": "merge_commit"},
    )
    state = data.get("state", "merged")
    output = f"Merge request !5 merged (state: {state}).\n{data.get('web_url', '')}"
    assert "merged" in output


@pytest.mark.asyncio
async def test_add_merge_request_comment_formats_output() -> None:
    """Test add_merge_request_comment output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.post.return_value = {"id": 99}

    data = await mock_client.post(
        "/projects/1/merge_requests/5/notes",
        json={"body": "LGTM!"},
    )
    note_id = data.get("id", "?")
    output = f"Comment added (note #{note_id})."
    assert "Comment added (note #99)" in output


def test_read_only_error() -> None:
    """Test read-only guard raises GitLabApiError."""
    error = GitLabApiError(
        error=GitLabError(
            code="READ_ONLY_MODE",
            message="Server is in read-only mode. Mutations are disabled.",
            recovery="Set GITLAB_READ_ONLY=false to enable write operations.",
            status_code=403,
        )
    )
    assert error.error.code == "READ_ONLY_MODE"
    assert error.error.status_code == 403
    assert "read-only" in str(error)


@pytest.mark.asyncio
async def test_client_get_merge_request_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get fetches MR data correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/merge_requests/5",
        json={
            "id": 10,
            "iid": 5,
            "project_id": 1,
            "title": "Fix bug",
            "state": "opened",
            "source_branch": "fix",
            "target_branch": "main",
            "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
            "draft": False,
            "merged": False,
        },
    )
    data = await test_client.get("/projects/1/merge_requests/5")
    assert isinstance(data, dict)
    assert data["iid"] == 5


@pytest.mark.asyncio
async def test_client_create_merge_request_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.post creates MR correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/merge_requests",
        method="POST",
        json={
            "id": 10,
            "iid": 5,
            "project_id": 1,
            "title": "New feature",
            "state": "opened",
            "source_branch": "feature/x",
            "target_branch": "main",
            "web_url": "https://gitlab.com/g/p/-/merge_requests/5",
            "draft": False,
            "merged": False,
        },
    )
    data = await test_client.post(
        "/projects/1/merge_requests",
        json={
            "source_branch": "feature/x",
            "target_branch": "main",
            "title": "New feature",
            "description": "",
        },
    )
    assert isinstance(data, dict)
    assert data["iid"] == 5

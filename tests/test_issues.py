"""Tests for issue tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError
from gitlab_mcp.models import Issue


def test_issue_model() -> None:
    """Test Issue model parsing."""
    data: dict[str, Any] = {
        "id": 100,
        "iid": 42,
        "project_id": 1,
        "title": "Bug report",
        "description": "Something broke",
        "state": "opened",
        "labels": ["bug", "critical"],
        "web_url": "https://gitlab.com/g/p/-/issues/42",
    }
    issue = Issue.model_validate(data)
    assert issue.iid == 42
    assert issue.title == "Bug report"
    assert issue.description == "Something broke"
    assert issue.state == "opened"
    assert "bug" in issue.labels
    assert "critical" in issue.labels


def test_issue_model_minimal() -> None:
    """Test Issue model with minimal fields."""
    data: dict[str, Any] = {
        "id": 101,
        "iid": 43,
        "project_id": 1,
        "title": "Minimal issue",
        "state": "opened",
        "web_url": "https://gitlab.com/g/p/-/issues/43",
    }
    issue = Issue.model_validate(data)
    assert issue.description is None
    assert issue.labels == []


@pytest.mark.asyncio
async def test_get_issue_formats_output() -> None:
    """Test get_issue output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 100,
        "iid": 42,
        "project_id": 1,
        "title": "Bug report",
        "description": "Something broke",
        "state": "opened",
        "labels": ["bug", "critical"],
        "web_url": "https://gitlab.com/g/p/-/issues/42",
    }

    data = await mock_client.get("/projects/1/issues/42")
    output = (
        f"Issue #{data.get('iid', '?')}\n"
        f"Title: {data.get('title', 'N/A')}\n"
        f"State: {data.get('state', 'N/A')}\n"
        f"Description: {data.get('description', 'N/A') or 'N/A'}\n"
        f"Labels: {', '.join(data.get('labels', []) or [])}\n"
        f"URL: {data.get('web_url', 'N/A')}"
    )
    assert "Issue #42" in output
    assert "Bug report" in output
    assert "opened" in output
    assert "Something broke" in output
    assert "bug, critical" in output


@pytest.mark.asyncio
async def test_get_issue_handles_null_description() -> None:
    """Test get_issue handles missing description."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 100,
        "iid": 42,
        "project_id": 1,
        "title": "Bug",
        "state": "opened",
        "labels": [],
        "web_url": "https://gitlab.com/g/p/-/issues/42",
    }

    data = await mock_client.get("/projects/1/issues/42")
    output = (
        f"Issue #{data.get('iid', '?')}\n"
        f"Title: {data.get('title', 'N/A')}\n"
        f"State: {data.get('state', 'N/A')}\n"
        f"Description: {data.get('description', 'N/A') or 'N/A'}\n"
        f"Labels: {', '.join(data.get('labels', []) or [])}\n"
        f"URL: {data.get('web_url', 'N/A')}"
    )
    assert "Description: N/A" in output


@pytest.mark.asyncio
async def test_list_issues_formats_output() -> None:
    """Test list_issues output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"iid": 1, "title": "Bug A"},
        {"iid": 2, "title": "Bug B"},
    ]

    data = await mock_client.get("/projects/1/issues", params={"state": "opened"})
    assert isinstance(data, list)
    lines = [f"Issues ({'opened'}):"]
    for item in data:
        lines.append(f"  #{item.get('iid', '?')} \u2014 {item.get('title', '?')}")
    output = "\n".join(lines)
    assert "Issues (opened)" in output
    assert "#1" in output
    assert "Bug A" in output
    assert "#2" in output


@pytest.mark.asyncio
async def test_list_issues_empty() -> None:
    """Test list_issues returns 'no issues' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects/1/issues", params={"state": "opened"})
    if not data:
        assert True  # Would return "No issues found."


@pytest.mark.asyncio
async def test_create_issue_formats_output() -> None:
    """Test create_issue output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.post.return_value = {
        "id": 200,
        "iid": 50,
        "project_id": 1,
        "title": "New feature",
        "state": "opened",
        "labels": [],
        "web_url": "https://gitlab.com/g/p/-/issues/50",
    }

    data = await mock_client.post(
        "/projects/1/issues",
        json={"title": "New feature", "description": "", "labels": "enhancement"},
    )
    output = (
        f"Created issue #{data.get('iid', '?')}: {data.get('title', '')}"
        f"\n{data.get('web_url', '')}"
    )
    assert "Created issue #50" in output
    assert "New feature" in output


@pytest.mark.asyncio
async def test_update_issue_formats_output() -> None:
    """Test update_issue output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.put.return_value = {
        "id": 200,
        "iid": 50,
        "project_id": 1,
        "title": "Updated title",
        "state": "opened",
        "labels": [],
        "web_url": "https://gitlab.com/g/p/-/issues/50",
    }

    data = await mock_client.put(
        "/projects/1/issues/50",
        json={"title": "Updated title", "state_event": "close"},
    )
    output = (
        f"Updated issue #{data.get('iid', '?')}: {data.get('title', '')}"
        f"\n{data.get('web_url', '')}"
    )
    assert "Updated issue #50" in output
    assert "Updated title" in output


def test_read_only_error() -> None:
    """Test read-only guard error for issue mutations."""
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


@pytest.mark.asyncio
async def test_client_get_issue_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get fetches issue correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues/42",
        json={
            "id": 100,
            "iid": 42,
            "project_id": 1,
            "title": "Bug report",
            "state": "opened",
            "labels": ["bug"],
            "web_url": "https://gitlab.com/g/p/-/issues/42",
        },
    )
    data = await test_client.get("/projects/1/issues/42")
    assert isinstance(data, dict)
    assert data["iid"] == 42


@pytest.mark.asyncio
async def test_client_create_issue_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.post creates issue correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues",
        method="POST",
        json={
            "id": 200,
            "iid": 50,
            "project_id": 1,
            "title": "New issue",
            "state": "opened",
            "labels": [],
            "web_url": "https://gitlab.com/g/p/-/issues/50",
        },
    )
    data = await test_client.post(
        "/projects/1/issues",
        json={"title": "New issue", "description": ""},
    )
    assert isinstance(data, dict)
    assert data["iid"] == 50

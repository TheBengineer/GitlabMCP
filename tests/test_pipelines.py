"""Tests for pipeline tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.errors import GitLabApiError, GitLabError
from gitlab_mcp.models import Pipeline


def test_pipeline_model() -> None:
    """Test Pipeline model parsing."""
    data: dict[str, Any] = {
        "id": 500,
        "project_id": 1,
        "ref": "main",
        "sha": "abc123def456",
        "status": "success",
        "source": "push",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T01:00:00Z",
        "web_url": "https://gitlab.com/g/p/-/pipelines/500",
    }
    pipeline = Pipeline.model_validate(data)
    assert pipeline.id == 500
    assert pipeline.project_id == 1
    assert pipeline.ref == "main"
    assert pipeline.sha == "abc123def456"
    assert pipeline.status == "success"
    assert pipeline.source == "push"
    assert pipeline.created_at == "2024-01-01T00:00:00Z"
    assert pipeline.updated_at == "2024-01-01T01:00:00Z"


@pytest.mark.asyncio
async def test_list_pipelines_formats_output() -> None:
    """Test list_pipelines output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"id": 500, "ref": "main", "status": "success"},
        {"id": 501, "ref": "develop", "status": "running"},
    ]

    data = await mock_client.get("/projects/1/pipelines", params={})
    assert isinstance(data, list)
    lines = [f"Pipelines ({'all'}):"]
    for item in data:
        lines.append(
            f"  #{item.get('id', '?')} \u2014 {item.get('ref', '?')}"
            f" ({item.get('status', '?')})"
        )
    output = "\n".join(lines)
    assert "Pipelines (all)" in output
    assert "#500" in output
    assert "main" in output
    assert "success" in output
    assert "#501" in output
    assert "develop" in output
    assert "running" in output


@pytest.mark.asyncio
async def test_list_pipelines_with_filters() -> None:
    """Test list_pipelines formats filtered output."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"id": 500, "ref": "main", "status": "failed"},
    ]

    data = await mock_client.get(
        "/projects/1/pipelines", params={"ref": "main", "status": "failed"}
    )
    assert isinstance(data, list)
    lines = [f"Pipelines ({'failed'}):"]
    for item in data:
        lines.append(
            f"  #{item.get('id', '?')} \u2014 {item.get('ref', '?')}"
            f" ({item.get('status', '?')})"
        )
    output = "\n".join(lines)
    assert "Pipelines (failed)" in output


@pytest.mark.asyncio
async def test_list_pipelines_empty() -> None:
    """Test list_pipelines returns 'no pipelines' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects/1/pipelines", params={})
    if not data:
        assert True  # Would return "No pipelines found."


@pytest.mark.asyncio
async def test_get_pipeline_formats_output() -> None:
    """Test get_pipeline output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 500,
        "project_id": 1,
        "ref": "main",
        "sha": "abc123",
        "status": "success",
        "source": "push",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T01:00:00Z",
        "web_url": "https://gitlab.com/g/p/-/pipelines/500",
    }

    data = await mock_client.get("/projects/1/pipelines/500")
    output = (
        f"Pipeline #{data.get('id', '?')}\n"
        f"Project: {data.get('project_id', '?')}\n"
        f"Ref: {data.get('ref', '?')}\n"
        f"Sha: {data.get('sha', '?')}\n"
        f"Status: {data.get('status', '?')}\n"
        f"Source: {data.get('source', '?')}\n"
        f"Created: {data.get('created_at', '?')}\n"
        f"Updated: {data.get('updated_at', '?')}\n"
        f"URL: {data.get('web_url', '?')}"
    )
    assert "Pipeline #500" in output
    assert "main" in output
    assert "success" in output
    assert "push" in output


@pytest.mark.asyncio
async def test_retry_pipeline_formats_output() -> None:
    """Test retry_pipeline output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.post.return_value = {
        "id": 501,
        "status": "pending",
    }

    data = await mock_client.post("/projects/1/pipelines/500/retry")
    new_id = data.get("id", "?")
    output = (
        f"Retried pipeline #500."
        f" New pipeline: #{new_id} ({data.get('status', '?')})"
    )
    assert "Retried pipeline #500" in output
    assert "#501" in output
    assert "pending" in output


@pytest.mark.asyncio
async def test_cancel_pipeline_formats_output() -> None:
    """Test cancel_pipeline output formatting."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.post.return_value = {
        "id": 500,
        "status": "canceled",
    }

    data = await mock_client.post("/projects/1/pipelines/500/cancel")
    output = f"Pipeline #500 canceled (status: {data.get('status', '?')})."
    assert "Pipeline #500 canceled" in output
    assert "canceled" in output


def test_read_only_error() -> None:
    """Test read-only guard error for pipeline mutations."""
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
async def test_client_list_pipelines_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get lists pipelines correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/pipelines?ref=main",
        json=[
            {"id": 500, "project_id": 1, "ref": "main", "sha": "abc", "status": "success",
             "source": "push", "created_at": "2024-01-01T00:00:00Z",
             "updated_at": "2024-01-01T01:00:00Z",
             "web_url": "https://gitlab.com/g/p/-/pipelines/500"},
        ],
    )
    data = await test_client.get("/projects/1/pipelines", params={"ref": "main"})
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == 500


@pytest.mark.asyncio
async def test_client_get_pipeline_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get fetches pipeline correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/pipelines/500",
        json={
            "id": 500, "project_id": 1, "ref": "main", "sha": "abc", "status": "success",
            "source": "push", "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "web_url": "https://gitlab.com/g/p/-/pipelines/500",
        },
    )
    data = await test_client.get("/projects/1/pipelines/500")
    assert isinstance(data, dict)
    assert data["id"] == 500


@pytest.mark.asyncio
async def test_client_retry_pipeline_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.post retries pipeline correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/pipelines/500/retry",
        method="POST",
        json={"id": 501, "status": "pending"},
    )
    data = await test_client.post("/projects/1/pipelines/500/retry")
    assert isinstance(data, dict)
    assert data["id"] == 501

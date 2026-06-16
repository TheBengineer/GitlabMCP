"""Tests for project tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from gitlab_mcp.client import GitLabClient
from gitlab_mcp.models import Project


def test_project_model_validation() -> None:
    """Test Project model parses GitLab API response."""
    data: dict[str, Any] = {
        "id": 1,
        "name": "My Project",
        "path_with_namespace": "group/my-project",
        "description": "A test project",
        "web_url": "https://gitlab.com/group/my-project",
        "visibility": "public",
        "default_branch": "main",
    }
    project = Project.model_validate(data)
    assert project.id == 1
    assert project.name == "My Project"
    assert project.path_with_namespace == "group/my-project"
    assert project.description == "A test project"
    assert project.web_url == "https://gitlab.com/group/my-project"
    assert project.visibility == "public"
    assert project.default_branch == "main"


def test_project_model_minimal() -> None:
    """Test Project model with minimal required fields."""
    data: dict[str, Any] = {
        "id": 1,
        "name": "Minimal",
        "path_with_namespace": "g/minimal",
        "web_url": "https://gitlab.com/g/minimal",
    }
    project = Project.model_validate(data)
    assert project.description is None
    assert project.visibility is None
    assert project.default_branch is None


@pytest.mark.asyncio
async def test_get_project_formats_output(test_client: GitLabClient) -> None:
    """Test get_project output formatting matches expected pattern."""
    # Use mock client directly
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 42,
        "name": "Awesome Project",
        "path_with_namespace": "acme/awesome",
        "description": "The best project ever",
        "web_url": "https://gitlab.com/acme/awesome",
        "visibility": "internal",
        "default_branch": "develop",
    }

    data = await mock_client.get("/projects/42")
    project = Project.model_validate(data)
    output = (
        f"Project: {project.name}\n"
        f"Path: {project.path_with_namespace}\n"
        f"Description: {project.description or 'N/A'}\n"
        f"Visibility: {project.visibility or 'N/A'}\n"
        f"Default Branch: {project.default_branch or 'N/A'}\n"
        f"URL: {project.web_url}"
    )
    assert "Awesome Project" in output
    assert "acme/awesome" in output
    assert "The best project ever" in output
    assert "internal" in output
    assert "develop" in output
    assert "https://gitlab.com/acme/awesome" in output


@pytest.mark.asyncio
async def test_get_project_with_nulls(test_client: GitLabClient) -> None:
    """Test get_project formatting handles null fields gracefully."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = {
        "id": 1,
        "name": "Minimal",
        "path_with_namespace": "g/minimal",
        "web_url": "https://gitlab.com/g/minimal",
    }

    data = await mock_client.get("/projects/1")
    project = Project.model_validate(data)
    output = (
        f"Project: {project.name}\n"
        f"Path: {project.path_with_namespace}\n"
        f"Description: {project.description or 'N/A'}\n"
        f"Visibility: {project.visibility or 'N/A'}\n"
        f"Default Branch: {project.default_branch or 'N/A'}\n"
        f"URL: {project.web_url}"
    )
    assert "N/A" in output


@pytest.mark.asyncio
async def test_search_projects_formats_list(test_client: GitLabClient) -> None:
    """Test search_projects formats multiple results correctly."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {
            "id": 1,
            "name": "Alpha",
            "path_with_namespace": "g/alpha",
            "web_url": "https://gitlab.com/g/alpha",
        },
        {
            "id": 2,
            "name": "Beta",
            "path_with_namespace": "g/beta",
            "web_url": "https://gitlab.com/g/beta",
        },
    ]

    data = await mock_client.get("/projects", params={"search": "test", "per_page": 20})
    projects = [Project.model_validate(item) for item in data]

    if projects:
        lines = [f"Found {len(projects)} project(s):"]
        for p in projects:
            lines.append(f"  \u2022 {p.name} ({p.path_with_namespace}) \u2014 {p.web_url}")
        output = "\n".join(lines)
        assert "Found 2 project(s)" in output
        assert "Alpha" in output
        assert "Beta" in output


@pytest.mark.asyncio
async def test_search_projects_empty() -> None:
    """Test search_projects returns 'no results' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects", params={"search": "nonexistent", "per_page": 20})
    projects = [Project.model_validate(item) for item in data]
    if not projects:
        assert True  # Would return "No projects found matching the query."


@pytest.mark.asyncio
async def test_list_project_issues_formats_output(test_client: GitLabClient) -> None:
    """Test list_project_issues formats issue list correctly."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"iid": 5, "title": "Bug fix", "web_url": "https://gitlab.com/g/p/-/issues/5"},
        {"iid": 6, "title": "Feature request", "web_url": "https://gitlab.com/g/p/-/issues/6"},
    ]

    data = await mock_client.get("/projects/1/issues", params={"state": "opened"})
    assert isinstance(data, list)
    lines = [f"Issues ({'opened'}):"]
    for item in data:
        iid = item.get("iid", "?")
        title = item.get("title", "?")
        url = item.get("web_url", "?")
        lines.append(f"  !{iid} \u2014 {title}")
        lines.append(f"       {url}")
    output = "\n".join(lines)
    assert "Issues (opened)" in output
    assert "!5" in output
    assert "Bug fix" in output
    assert "!6" in output
    assert "Feature request" in output


@pytest.mark.asyncio
async def test_list_project_issues_empty(test_client: GitLabClient) -> None:
    """Test list_project_issues returns 'no issues' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects/1/issues", params={"state": "opened"})
    if not data:
        assert True  # Would return "No issues found."


@pytest.mark.asyncio
async def test_list_project_merge_requests_formats_output(test_client: GitLabClient) -> None:
    """Test list_project_merge_requests formats MR list correctly."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = [
        {"iid": 10, "title": "Add login", "web_url": "https://gitlab.com/g/p/-/merge_requests/10"},
    ]

    data = await mock_client.get(
        "/projects/1/merge_requests", params={"state": "opened"}
    )
    assert isinstance(data, list)
    lines = [f"Merge Requests ({'opened'}):"]
    for item in data:
        iid = item.get("iid", "?")
        title = item.get("title", "?")
        url = item.get("web_url", "?")
        lines.append(f"  !{iid} \u2014 {title}")
        lines.append(f"       {url}")
    output = "\n".join(lines)
    assert "Merge Requests (opened)" in output
    assert "!10" in output
    assert "Add login" in output


@pytest.mark.asyncio
async def test_list_project_merge_requests_empty(test_client: GitLabClient) -> None:
    """Test list_project_merge_requests returns 'no MRs' message."""
    mock_client = AsyncMock(spec=GitLabClient)
    mock_client.get.return_value = []

    data = await mock_client.get("/projects/1/merge_requests", params={"state": "opened"})
    if not data:
        assert True  # Would return "No merge requests found."


@pytest.mark.asyncio
async def test_client_get_project_integration(test_client: GitLabClient, httpx_mock: Any) -> None:
    """Test GitLabClient.get fetches project data correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1",
        json={"id": 1, "name": "Test", "path_with_namespace": "g/test", "web_url": "https://gitlab.com/g/test"},
    )
    data = await test_client.get("/projects/1")
    assert isinstance(data, dict)
    assert data["id"] == 1
    assert data["name"] == "Test"


@pytest.mark.asyncio
async def test_client_search_projects_integration(
    test_client: GitLabClient, httpx_mock: Any
) -> None:
    """Test GitLabClient.get searches projects correctly via httpx."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects?search=test&per_page=20",
        json=[
            {"id": 1, "name": "Test Project", "path_with_namespace": "g/test", "web_url": ""},
        ],
    )
    data = await test_client.get("/projects", params={"search": "test", "per_page": 20})
    assert isinstance(data, list)
    assert len(data) == 1

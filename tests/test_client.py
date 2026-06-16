"""Tests for GitLabClient."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_client_get_success(test_client, httpx_mock) -> None:
    """Test successful GET request returns parsed JSON."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1",
        json={"id": 1, "name": "test-project", "web_url": "https://gitlab.test.com/test/project"},
    )
    result = await test_client.get("/projects/1")
    assert isinstance(result, dict)
    assert result["id"] == 1
    assert result["name"] == "test-project"


@pytest.mark.asyncio
async def test_client_get_list(test_client, httpx_mock) -> None:
    """Test GET request returning a list."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects",
        json=[
            {"id": 1, "name": "Project A"},
            {"id": 2, "name": "Project B"},
        ],
    )
    result = await test_client.get("/projects")
    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_client_401_error(test_client, httpx_mock) -> None:
    """Test 401 raises GitLabApiError."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1",
        status_code=401,
    )
    from gitlab_mcp.errors import GitLabApiError

    with pytest.raises(GitLabApiError) as exc_info:
        await test_client.get("/projects/1")
    assert exc_info.value.error.code == "AUTH_FAILED"


@pytest.mark.asyncio
async def test_client_404_error(test_client, httpx_mock) -> None:
    """Test 404 raises GitLabApiError."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/99999",
        status_code=404,
    )
    from gitlab_mcp.errors import GitLabApiError

    with pytest.raises(GitLabApiError) as exc_info:
        await test_client.get("/projects/99999")
    assert exc_info.value.error.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_client_post(test_client, httpx_mock) -> None:
    """Test POST request."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues",
        method="POST",
        json={"id": 10, "iid": 1, "title": "Test Issue"},
    )
    result = await test_client.post("/projects/1/issues", json={"title": "Test Issue"})
    assert isinstance(result, dict)
    assert result["title"] == "Test Issue"


@pytest.mark.asyncio
async def test_client_put(test_client, httpx_mock) -> None:
    """Test PUT request."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues/1",
        method="PUT",
        json={"id": 10, "title": "Updated"},
    )
    result = await test_client.put("/projects/1/issues/1", json={"title": "Updated"})
    assert result["title"] == "Updated"


@pytest.mark.asyncio
async def test_client_delete(test_client, httpx_mock) -> None:
    """Test DELETE request."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues/1",
        method="DELETE",
        json={},
    )
    result = await test_client.delete("/projects/1/issues/1")
    assert result == {}


@pytest.mark.asyncio
async def test_client_pagination(test_client, httpx_mock) -> None:
    """Test that pagination follows Link headers."""
    # First page
    next_url = "https://gitlab.test.com/api/v4/projects/1/issues?page=2&per_page=20"
    first_url = "https://gitlab.test.com/api/v4/projects/1/issues?page=1&per_page=20"
    next_link = f'<{next_url}>; rel="next"'
    first_link = f'<{first_url}>; rel="first"'
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues?per_page=20",
        headers={"Link": f"{next_link}, {first_link}"},
        json=[{"id": i, "title": f"Issue {i}"} for i in range(20)],
    )
    # Second page
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues?page=2&per_page=20",
        json=[{"id": i, "title": f"Issue {i}"} for i in range(20, 30)],
    )
    result = await test_client.get("/projects/1/issues", params={"per_page": 20})
    assert isinstance(result, list)
    assert len(result) == 30  # 20 from page 1 + 10 from page 2


@pytest.mark.asyncio
async def test_client_max_results_cap(test_client, httpx_mock) -> None:
    """Test that pagination stops at max_results."""
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues",
        headers={
            "Link": '<https://gitlab.test.com/api/v4/projects/1/issues?page=2>; rel="next"',
        },
        json=[{"id": i, "title": f"Issue {i}"} for i in range(20)],
    )
    # Add many more pages, but client should stop at max_results=50
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues?page=2",
        headers={
            "Link": '<https://gitlab.test.com/api/v4/projects/1/issues?page=3>; rel="next"',
        },
        json=[{"id": i, "title": f"Issue {i}"} for i in range(20, 40)],
    )
    httpx_mock.add_response(
        url="https://gitlab.test.com/api/v4/projects/1/issues?page=3",
        json=[{"id": i, "title": f"Issue {i}"} for i in range(40, 100)],
    )
    result = await test_client.get("/projects/1/issues")
    assert isinstance(result, list)
    assert len(result) <= 50  # max_results is 50

from __future__ import annotations
from typing import Any

from pydantic import BaseModel


class Project(BaseModel):
    id: int
    name: str
    path_with_namespace: str
    description: str | None = None
    web_url: str
    visibility: str | None = None
    default_branch: str | None = None


class MergeRequest(BaseModel):
    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: str
    source_branch: str
    target_branch: str
    web_url: str
    draft: bool
    merged: bool


class Issue(BaseModel):
    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: str
    labels: list[str] = []
    web_url: str


class Pipeline(BaseModel):
    id: int
    project_id: int
    ref: str
    sha: str
    status: str
    source: str
    created_at: str
    updated_at: str
    web_url: str


class RepoFile(BaseModel):
    file_path: str
    size: int
    encoding: str
    content: str | None = None
    ref: str


class Branch(BaseModel):
    name: str
    merged: bool
    default: bool
    protected: bool


class Commit(BaseModel):
    id: str
    short_id: str
    title: str
    author_name: str
    authored_date: str
    message: str


class Note(BaseModel):
    id: int
    body: str
    author: dict[str, Any]
    created_at: str

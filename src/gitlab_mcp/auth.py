from __future__ import annotations

from abc import ABC, abstractmethod

from gitlab_mcp.config import GitLabSettings


class AuthProvider(ABC):
    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        ...


class EnvAuthProvider(AuthProvider):
    def __init__(self, settings: GitLabSettings) -> None:
        self.settings = settings

    def get_headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": self.settings.token}


class BearerAuthProvider(AuthProvider):
    def __init__(self, token: str) -> None:
        self.token = token

    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

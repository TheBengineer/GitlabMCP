from pydantic import BaseModel


class GitLabError(BaseModel):
    code: str
    message: str
    recovery: str
    status_code: int | None = None
    retry_after: int | None = None


class GitLabApiError(Exception):
    def __init__(self, error: GitLabError) -> None:
        self.error = error
        super().__init__(error.message)

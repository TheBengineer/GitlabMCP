from pydantic_settings import BaseSettings, SettingsConfigDict


class GitLabSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GITLAB_",
        env_file=".env",
        extra="ignore",
    )

    url: str = "https://gitlab.com"
    token: str = ""
    ssl_verify: bool = True
    proxy_url: str | None = None
    api_version: str = "v4"
    max_results: int = 100
    read_only: bool = False
    tool_allowlist: str = ""
    tool_denylist: str = ""

# GitLab MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that wraps the GitLab REST API, exposing GitLab operations as MCP tools for AI assistants like Claude, Cursor, Gemini, and Copilot.

## Quick Start

```bash
# Clone and install
git clone https://github.com/TheBengineer/GitlabMCP.git
cd GitlabMCP
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Set your GitLab token
export GITLAB_TOKEN="your_personal_access_token"

# Run with stdio (default — works with Claude Desktop, Cursor, etc.)
gitlab-mcp

# Or run with HTTP transport
gitlab-mcp --transport streamable-http --port 8000
```

## Configuration

All configuration is via environment variables (using pydantic-settings):

| Variable | Default | Description |
|---|---|---|
| `GITLAB_URL` | `https://gitlab.com` | GitLab instance URL (supports self-managed) |
| `GITLAB_TOKEN` | — | Personal access token (required) |
| `GITLAB_SSL_VERIFY` | `true` | Verify SSL certificates (disable for self-signed) |
| `GITLAB_PROXY_URL` | — | HTTP proxy URL for on-premise networks |
| `GITLAB_API_VERSION` | `v4` | GitLab API version |
| `GITLAB_MAX_RESULTS` | `100` | Max items to auto-fetch per paginated request |
| `GITLAB_READ_ONLY` | `false` | Block all mutation tools server-side |
| `GITLAB_TOOL_ALLOWLIST` | — | Comma-separated tool names to expose |
| `GITLAB_TOOL_DENYLIST` | — | Comma-separated tool names to hide |

Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
# Edit .env with your GitLab URL and token
```

## Tools

The server exposes **21 MCP tools** across 5 domains:

### Projects
| Tool | Description | Safe |
|---|---|---|
| `get_project` | Get project details by ID or path | ✅ Read-only |
| `list_projects` | List all accessible projects | ✅ Read-only |
| `search_projects` | Search projects by name/description | ✅ Read-only |
| `list_project_issues` | List issues for a project | ✅ Read-only |
| `list_project_merge_requests` | List MRs for a project | ✅ Read-only |

### Merge Requests
| Tool | Description | Safe |
|---|---|---|
| `get_merge_request` | Get MR details by IID | ✅ Read-only |
| `list_merge_requests` | List MRs (optionally scoped to project) | ✅ Read-only |
| `create_merge_request` | Create a new merge request | ⚠️ Mutation |
| `merge_merge_request` | Merge a merge request | ⚠️ Destructive |
| `add_merge_request_comment` | Add a comment to an MR | ⚠️ Mutation |

### Issues
| Tool | Description | Safe |
|---|---|---|
| `get_issue` | Get issue details by IID | ✅ Read-only |
| `list_issues` | List issues filtered by state | ✅ Read-only |
| `create_issue` | Create a new issue | ⚠️ Mutation |
| `update_issue` | Update issue (title, description, close/reopen) | ⚠️ Mutation |

### CI/CD Pipelines
| Tool | Description | Safe |
|---|---|---|
| `list_pipelines` | List pipelines with optional ref/status filters | ✅ Read-only |
| `get_pipeline` | Get pipeline details | ✅ Read-only |
| `retry_pipeline` | Retry a failed/canceled pipeline | ⚠️ Mutation |
| `cancel_pipeline` | Cancel a running pipeline | ⚠️ Mutation |

### Repository
| Tool | Description | Safe |
|---|---|---|
| `get_file` | Get file content (auto-decodes base64) | ✅ Read-only |
| `list_commits` | List commits on a branch | ✅ Read-only |
| `list_branches` | List repository branches | ✅ Read-only |
| `get_branch` | Get branch details (default/merged/protected) | ✅ Read-only |

All tools are annotated with MCP tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) to guide AI client behavior.

### Read-Only Mode

Set `GITLAB_READ_ONLY=true` to prevent any mutation tools from executing. This is enforced server-side — any write operation returns a structured error:

```json
{
  "code": "READ_ONLY_MODE",
  "message": "Server is in read-only mode. Mutations are disabled.",
  "recovery": "Set GITLAB_READ_ONLY=false to enable write operations.",
  "status_code": 403
}
```

## Architecture

```
┌──────────────┐     stdio / streamable-http     ┌──────────────────────┐
│  AI Client   │ ◄────────────────────────────►  │  FastMCP Server      │
│ (Claude,     │                                 │  ┌────────────────┐  │
│  Cursor,     │                                 │  │ Tools          │  │
│  Gemini)     │                                 │  │  projects      │  │
└──────────────┘                                 │  │  merge_req     │  │
                                                  │  │  issues        │  │
                                                  │  │  pipelines     │  │
                                                  │  │  repository    │  │
                                                  │  └──────┬─────────┘  │
                                                  │         │            │
                                                  │  ┌──────▼─────────┐  │
                                                  │  │ GitLabClient   │  │
                                                  │  │ (httpx async)  │  │
                                                  │  └──────┬─────────┘  │
                                                  └─────────│────────────┘
                                                            │
                                                  ┌─────────▼────────────┐
                                                  │  GitLab REST API     │
                                                  │  /api/v4             │
                                                  └──────────────────────┘
```

## Development

```bash
# Clone and install
git clone https://github.com/TheBengineer/GitlabMCP.git
cd GitlabMCP
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v

# Type check
mypy src/

# Lint
ruff check src/ tests/
```

### Project Structure

```
gitlab-mcp/
├── src/gitlab_mcp/
│   ├── __init__.py          # Package init
│   ├── __main__.py          # python -m support
│   ├── main.py              # CLI entry point (Click)
│   ├── server.py            # FastMCP server with lifespan
│   ├── client.py            # GitLab HTTP client (httpx)
│   ├── config.py            # pydantic-settings config
│   ├── auth.py              # AuthProvider interface
│   ├── models.py            # Pydantic response models
│   ├── errors.py            # Structured error types
│   └── tools/
│       ├── projects.py      # Project tools
│       ├── merge_requests.py# MR tools
│       ├── issues.py        # Issue tools
│       ├── pipelines.py     # Pipeline tools
│       └── repository.py    # Repository tools
└── tests/                   # 79 tests
```

## Error Handling

All errors return a structured response designed for LLM consumption:

```json
{
  "content": [{
    "type": "text",
    "text": "Error description"
  }],
  "isError": true,
  "error": {
    "code": "AUTH_FAILED",
    "message": "Authentication failed. Check your GITLAB_TOKEN.",
    "recovery": "Set GITLAB_TOKEN to a valid GitLab personal access token.",
    "statusCode": 401
  }
}
```

Error codes: `AUTH_FAILED`, `FORBIDDEN`, `NOT_FOUND`, `RATE_LIMITED`, `API_ERROR`, `READ_ONLY_MODE`

## Transport

- **stdio** (default) — for local MCP clients (Claude Desktop, Cursor, etc.)
- **streamable-http** (opt-in) — for remote deployment, supports ASGI mounting

## Systemd Service

Install as a systemd service (runs streamable-http on `0.0.0.0:8000`):

```bash
# Interactive (prompts for GitLab token)
sudo ./scripts/install-service.sh

# Non-interactive
sudo GITLAB_TOKEN=glpat-xxx ./scripts/install-service.sh
```

The script:
1. Creates a `gitlab-mcp` system user
2. Installs to `/opt/gitlab-mcp/` with an isolated venv
3. Writes `.env` with restricted permissions (600)
4. Installs and enables the systemd service
5. Hardens the service with `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`

After install:

```bash
systemctl status gitlab-mcp
journalctl -u gitlab-mcp -f
# MCP endpoint: http://0.0.0.0:8000/mcp
```

## Authentication

The server supports the following GitLab authentication methods:
- **Personal Access Token** (recommended) — via `GITLAB_TOKEN` env var, sent as `PRIVATE-TOKEN` header
- **Bearer Token** — extensible via `BearerAuthProvider` for OAuth2 tokens
- **Custom** — implement `AuthProvider` ABC for custom auth logic

## Self-Managed GitLab

Configure for self-managed instances:

```bash
export GITLAB_URL="https://gitlab.internal.company.com"
export GITLAB_SSL_VERIFY="false"       # For self-signed certs
export GITLAB_PROXY_URL="http://proxy:8080"  # For proxied environments
```

## License

MIT

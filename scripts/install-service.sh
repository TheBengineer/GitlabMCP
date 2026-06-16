#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────
# Install script: GitLab MCP Server systemd service
# ──────────────────────────────────────────────────
# Usage:
#   sudo ./scripts/install-service.sh              # interactive (prompts for token)
#   sudo GITLAB_TOKEN=glpat-xxx ./scripts/install-service.sh   # non-interactive
#
# Installs to /opt/gitlab-mcp, creates a gitlab-mcp system user,
# sets up the venv, configures .env, and enables the service.
# ──────────────────────────────────────────────────

SERVICE_NAME="gitlab-mcp"
INSTALL_DIR="/opt/${SERVICE_NAME}"
SERVICE_USER="${SERVICE_NAME}"
SERVICE_FILE="${SERVICE_NAME}.service"
SERVICE_TARGET="/etc/systemd/system/${SERVICE_FILE}"

# --- Preflight checks ---
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root (sudo)." >&2
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required but not found." >&2
    exit 1
fi

if ! command -v rsync &>/dev/null; then
    echo "ERROR: rsync is required but not found." >&2
    echo "  Install: apt install rsync  (or: yum install rsync)" >&2
    exit 1
fi

if ! python3 -c "import venv" &>/dev/null; then
    echo "ERROR: Python venv module is not available." >&2
    echo "  Install: apt install python3-venv  (or: yum install python3-venv)" >&2
    exit 1
fi

if ! command -v systemctl &>/dev/null; then
    echo "ERROR: systemctl is required (systemd not detected)." >&2
    exit 1
fi

# --- Gather configuration ---
GITLAB_URL="${GITLAB_URL:-https://gitlab.com}"

if [[ -z "${GITLAB_TOKEN:-}" ]]; then
    read -rsp "Enter your GitLab Personal Access Token: " GITLAB_TOKEN
    echo
    if [[ -z "$GITLAB_TOKEN" ]]; then
        echo "ERROR: GITLAB_TOKEN is required." >&2
        exit 1
    fi
fi

GITLAB_READ_ONLY="${GITLAB_READ_ONLY:-false}"
GITLAB_MAX_RESULTS="${GITLAB_MAX_RESULTS:-100}"
MCP_PORT="${MCP_PORT:-8000}"
MCP_HOST="${MCP_HOST:-0.0.0.0}"

echo ""
echo "── Installing GitLab MCP Server ──"
echo "  Install dir:  ${INSTALL_DIR}"
echo "  Service user: ${SERVICE_USER}"
echo "  GitLab URL:   ${GITLAB_URL}"
echo "  Bind:         ${MCP_HOST}:${MCP_PORT}"
echo "  Read-only:    ${GITLAB_READ_ONLY}"
echo ""

# --- Create system user ---
if ! id "${SERVICE_USER}" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
    echo "  ✓ Created system user '${SERVICE_USER}'"
fi

# --- Create install directory ---
mkdir -p "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/.venv"

# --- Copy source files (from repo root, relative to script location) ---
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
rsync -a --delete \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.omo' \
    --exclude='.opencode' \
    --exclude='.gitignore' \
    "${SCRIPT_DIR}/src/" "${INSTALL_DIR}/src/"
# Copy pyproject.toml needed for pip install (editable install looks at package root)
cp "${SCRIPT_DIR}/pyproject.toml" "${INSTALL_DIR}/pyproject.toml"
echo "  ✓ Copied source files"

# --- Set up virtual environment ---
python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/pip" install --quiet --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install --quiet "${INSTALL_DIR}"
echo "  ✓ Created virtual environment"

# --- Create .env file ---
cat > "${INSTALL_DIR}/.env" <<ENVEOF
GITLAB_URL=${GITLAB_URL}
GITLAB_TOKEN=${GITLAB_TOKEN}
GITLAB_SSL_VERIFY=true
GITLAB_API_VERSION=v4
GITLAB_MAX_RESULTS=${GITLAB_MAX_RESULTS}
GITLAB_READ_ONLY=${GITLAB_READ_ONLY}
ENVEOF

chmod 600 "${INSTALL_DIR}/.env"
echo "  ✓ Created .env (permissions 600)"

# --- Copy systemd service file ---
cp "${SCRIPT_DIR}/scripts/${SERVICE_FILE}" "${SERVICE_TARGET}"

# The service file uses %i for the user, but we use a fixed user so
# replace the specifier with the actual user name
sed -i "s/User=%i/User=${SERVICE_USER}/" "${SERVICE_TARGET}"
sed -i "s|ExecStart=.*|ExecStart=${INSTALL_DIR}/.venv/bin/python -m gitlab_mcp --transport streamable-http --host ${MCP_HOST} --port ${MCP_PORT}|" "${SERVICE_TARGET}"
echo "  ✓ Installed systemd service"

# --- Set ownership ---
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"
chmod 755 "${INSTALL_DIR}"
echo "  ✓ Set ownership to ${SERVICE_USER}"

# --- Enable and start ---
systemctl daemon-reload
systemctl enable "${SERVICE_FILE}"
systemctl restart "${SERVICE_FILE}"

# --- Verify ---
sleep 2
if systemctl is-active --quiet "${SERVICE_FILE}"; then
    echo ""
    echo "  ✓ Service '${SERVICE_NAME}' is running."
    echo ""
    echo "  Check status:  systemctl status ${SERVICE_NAME}"
    echo "  View logs:     journalctl -u ${SERVICE_NAME} -f"
    echo "  MCP endpoint:  http://${MCP_HOST}:${MCP_PORT}/mcp"
else
    echo ""
    echo "  ⚠ Service installed but NOT running. Check: systemctl status ${SERVICE_NAME}"
    exit 1
fi

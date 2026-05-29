#!/usr/bin/env bash
# whorl — idempotent installer for an Ubuntu/Debian IONOS VM.
#
# Usage (as root, on a fresh VM):
#   git clone https://github.com/pb-commits-it/whorl /opt/whorl
#   cd /opt/whorl
#   sudo bash deploy/install.sh
#
# Re-running is safe: nothing here is destructive. Edit /opt/whorl/.env after
# the first run to set OPENROUTER_API_KEY + JWT_SECRET + BASE_URL.

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/whorl}"
SERVICE_USER="${SERVICE_USER:-whorl}"
PY_BIN="${PY_BIN:-python3.12}"

log() { printf '\033[1;36m[whorl-install]\033[0m %s\n' "$*"; }

# ─── prereqs ────────────────────────────────────────────────────────────────
log "installing system packages"
apt-get update -y
apt-get install -y --no-install-recommends \
    "$PY_BIN" "${PY_BIN}-venv" python3-pip \
    git curl ca-certificates \
    nodejs npm \
    docker.io docker-compose-plugin \
    caddy \
    restic

# ─── service user ───────────────────────────────────────────────────────────
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    log "creating service user $SERVICE_USER"
    useradd -r -m -d "$REPO_DIR" -s /usr/sbin/nologin "$SERVICE_USER"
fi
usermod -aG docker "$SERVICE_USER" || true

# ─── data dirs ──────────────────────────────────────────────────────────────
log "creating data dirs"
install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_USER" \
    /var/lib/whorl /var/lib/whorl/photos /var/lib/whorl/pg /var/lib/whorl/backups

# ─── repo ownership ─────────────────────────────────────────────────────────
log "chowning repo to $SERVICE_USER"
chown -R "$SERVICE_USER:$SERVICE_USER" "$REPO_DIR"

# ─── python venv ────────────────────────────────────────────────────────────
log "creating venv + installing whorl"
sudo -u "$SERVICE_USER" -H bash -c "
    set -euo pipefail
    cd '$REPO_DIR'
    $PY_BIN -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e '.'
"

# ─── frontend build ─────────────────────────────────────────────────────────
log "building web bundle"
sudo -u "$SERVICE_USER" -H bash -c "
    set -euo pipefail
    cd '$REPO_DIR/web'
    npm ci
    npm run build
"

# ─── env file ───────────────────────────────────────────────────────────────
if [[ ! -f "$REPO_DIR/.env" ]]; then
    log "writing default $REPO_DIR/.env — edit before starting!"
    cat >"$REPO_DIR/.env" <<'ENV'
# Set OPENROUTER_API_KEY + a 32-char JWT_SECRET before starting.
OPENROUTER_API_KEY=
OPENROUTER_VISION_MODEL=qwen/qwen3-vl-30b-a3b-instruct
OPENROUTER_FALLBACK_MODEL=google/gemini-2.5-flash
JWT_SECRET=
BASE_URL=https://app.whorl.app
DATABASE_URL=postgresql+asyncpg://whorl:whorl@127.0.0.1:5433/whorl
WHORL_DEV_AUTH=0
WHORL_PHOTO_DIR=/var/lib/whorl/photos
# Backups
RESTIC_REPOSITORY=
RESTIC_PASSWORD=
B2_ACCOUNT_ID=
B2_ACCOUNT_KEY=
ENV
    chown "$SERVICE_USER:$SERVICE_USER" "$REPO_DIR/.env"
    chmod 0640 "$REPO_DIR/.env"
fi

# ─── postgres via docker-compose ────────────────────────────────────────────
log "starting Postgres (Docker)"
cd "$REPO_DIR"
sudo -u "$SERVICE_USER" docker compose -f deploy/docker-compose.yml up -d
# Give pgvector a beat to accept connections.
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if sudo -u "$SERVICE_USER" docker exec whorl-postgres pg_isready -U whorl >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# ─── KB ingest ──────────────────────────────────────────────────────────────
log "ingesting wiki KB"
sudo -u "$SERVICE_USER" -H bash -c "
    cd '$REPO_DIR' && .venv/bin/whorl kb ingest || true
"

# ─── systemd units ──────────────────────────────────────────────────────────
log "installing systemd units"
install -m 0644 deploy/systemd/whorl.service          /etc/systemd/system/
install -m 0644 deploy/systemd/whorl-weather.service  /etc/systemd/system/
install -m 0644 deploy/systemd/whorl-weather.timer    /etc/systemd/system/
install -m 0644 deploy/systemd/whorl-backup.service   /etc/systemd/system/
install -m 0644 deploy/systemd/whorl-backup.timer     /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now whorl.service whorl-weather.timer whorl-backup.timer

# ─── caddy ──────────────────────────────────────────────────────────────────
log "configuring Caddy"
install -m 0644 deploy/caddy/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy || systemctl restart caddy

log "done — visit https://app.whorl.app"
log "edit $REPO_DIR/.env (OPENROUTER_API_KEY + JWT_SECRET) then: systemctl restart whorl"

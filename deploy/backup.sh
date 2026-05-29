#!/usr/bin/env bash
# whorl — nightly backup. Dumps Postgres + bundles photos, snapshots via restic
# to a Backblaze B2 repository configured in /opt/whorl/.env.
#
# Restore manually with: restic restore latest --target /tmp/whorl-restore
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/whorl}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/whorl/backups}"
PG_USER="${PG_USER:-whorl}"
PG_DB="${PG_DB:-whorl}"

log() { printf '\033[1;36m[whorl-backup]\033[0m %s\n' "$*"; }

cd "$REPO_DIR"
# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a

mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP="$BACKUP_DIR/pg-$STAMP.sql.gz"

# ─── Postgres logical dump ──────────────────────────────────────────────────
log "dumping postgres → $DUMP"
docker exec whorl-postgres pg_dump -U "$PG_USER" -d "$PG_DB" --no-owner --no-privileges \
    | gzip -9 > "$DUMP"

# ─── Restic snapshot to B2 ──────────────────────────────────────────────────
if [[ -z "${RESTIC_REPOSITORY:-}" ]]; then
    log "RESTIC_REPOSITORY unset — skipping remote upload"
    # Local-only retention: keep 7 nightly dumps
    find "$BACKUP_DIR" -name 'pg-*.sql.gz' -type f -mtime +7 -delete || true
    exit 0
fi

log "snapshotting Postgres dump + photos to $RESTIC_REPOSITORY"
restic backup \
    "$DUMP" \
    /var/lib/whorl/photos \
    --tag whorl --tag "$(hostname -s)"

# Keep 7 nightly + 4 weekly + 12 monthly snapshots.
restic forget --tag whorl \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 12 \
    --prune

# Local pg dump retention — restic has the durable copy.
find "$BACKUP_DIR" -name 'pg-*.sql.gz' -type f -mtime +3 -delete || true
log "ok"

#!/usr/bin/env bash
#
# Back up a Rodiva deployment: the database and the uploaded files.
#
# Both halves are needed. The database holds the record of every attachment, and
# the storage volume holds the bytes; either one alone restores to an instance
# that lists documents it cannot open, or holds files nothing points at.
#
#   ./scripts/backup.sh [destination] [retention]
#
# destination  where to write (default: ./backups)
# retention    how many backups to keep (default: 14; 0 keeps every one)
#
# Run it from the directory holding docker-compose.yml, with the stack up.

set -euo pipefail

DESTINATION="${1:-./backups}"
RETENTION="${2:-14}"
COMPOSE=(docker compose)

if [ -f .env ]; then
  # Only the database coordinates are needed, and only if the operator changed them.
  POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || true)"
  POSTGRES_DB="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || true)"
fi
POSTGRES_USER="${POSTGRES_USER:-rodiva}"
POSTGRES_DB="${POSTGRES_DB:-rodiva}"

if ! "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx db; then
  echo "The db service is not running; start the stack before backing up." >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%d-%H%M%SZ)"
TARGET="${DESTINATION}/rodiva-${STAMP}"
mkdir -p "$TARGET"

echo "Backing up to ${TARGET}"

# --clean --if-exists makes the dump replayable over an existing schema, which is
# what a restore into a running deployment needs.
"${COMPOSE[@]}" exec -T db pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean --if-exists --no-owner \
  | gzip > "${TARGET}/database.sql.gz"
echo "  database.sql.gz  $(du -h "${TARGET}/database.sql.gz" | cut -f1)"

# Read the files from the api container: the volume is named, so it has no
# predictable path on the host.
"${COMPOSE[@]}" exec -T api tar czf - -C /storage . > "${TARGET}/storage.tar.gz"
echo "  storage.tar.gz   $(du -h "${TARGET}/storage.tar.gz" | cut -f1)"

{
  echo "created_at=${STAMP}"
  echo "database=${POSTGRES_DB}"
  echo "api_version=$("${COMPOSE[@]}" exec -T api python -c \
    'from app.main import app; print(app.version)' 2>/dev/null || echo unknown)"
} > "${TARGET}/manifest.txt"

# Only ever prune whole backup directories this script's own naming produced.
if [ "$RETENTION" -gt 0 ]; then
  mapfile -t stale < <(
    find "$DESTINATION" -mindepth 1 -maxdepth 1 -type d -name 'rodiva-*' \
      | sort -r | tail -n "+$((RETENTION + 1))"
  )
  for old in "${stale[@]:-}"; do
    [ -n "$old" ] || continue
    echo "  pruning $(basename "$old")"
    rm -rf -- "$old"
  done
fi

echo "Done. Verify a restore periodically: a backup nobody has restored is a guess."

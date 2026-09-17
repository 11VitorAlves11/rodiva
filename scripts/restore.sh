#!/usr/bin/env bash
#
# Restore a Rodiva deployment from a directory produced by backup.sh.
#
#   ./scripts/restore.sh backups/rodiva-20260917-103000Z
#
# This REPLACES the current database contents and the uploaded files. It asks
# before doing either, and refuses to run unattended: restoring over live data
# by accident is exactly the failure a backup is supposed to protect against.

set -euo pipefail

SOURCE="${1:-}"
COMPOSE=(docker compose)

if [ -z "$SOURCE" ]; then
  echo "Usage: ./scripts/restore.sh <backup directory>" >&2
  exit 64
fi
for required in database.sql.gz storage.tar.gz; do
  if [ ! -f "${SOURCE}/${required}" ]; then
    echo "Not a backup directory: ${SOURCE}/${required} is missing." >&2
    exit 64
  fi
done

if [ -f .env ]; then
  POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || true)"
  POSTGRES_DB="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || true)"
fi
POSTGRES_USER="${POSTGRES_USER:-rodiva}"
POSTGRES_DB="${POSTGRES_DB:-rodiva}"

if [ -f "${SOURCE}/manifest.txt" ]; then
  echo "Backup contents:"
  sed 's/^/  /' "${SOURCE}/manifest.txt"
fi

echo
echo "This replaces the database '${POSTGRES_DB}' and every uploaded file in this deployment."
read -r -p "Type the word restore to continue: " confirmation
if [ "$confirmation" != "restore" ]; then
  echo "Cancelled; nothing was changed."
  exit 1
fi

if ! "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx db; then
  echo "The db service is not running; start the stack before restoring." >&2
  exit 1
fi

# Stop the API first so nothing writes while the schema is being replaced.
echo "Stopping the api service"
"${COMPOSE[@]}" stop api >/dev/null

echo "Restoring the database"
gunzip -c "${SOURCE}/database.sql.gz" \
  | "${COMPOSE[@]}" exec -T db psql \
      --username "$POSTGRES_USER" \
      --dbname "$POSTGRES_DB" \
      --quiet --set ON_ERROR_STOP=on >/dev/null

echo "Restoring the uploaded files"
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint sh api -c \
  'rm -rf /storage/* && tar xzf - -C /storage' < "${SOURCE}/storage.tar.gz"

echo "Starting the api service"
"${COMPOSE[@]}" start api >/dev/null

echo "Restored from $(basename "$SOURCE")."

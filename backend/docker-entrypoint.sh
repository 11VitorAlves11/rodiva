#!/bin/sh
# The API must never come up against an out-of-date schema: migrate first, then
# hand over to the CMD.
set -e

alembic upgrade head

exec "$@"

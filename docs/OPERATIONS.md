# Operating Rodiva

[← Back to the README](../README.md)

## Authentication

Local accounts use hashed passwords and signed session cookies, `httponly` and `secure` in
production. Sessions are held on the server and can be revoked one at a time or all at once
from the settings screen.

Password recovery is available once SMTP is configured (see [`.env.example`](../.env.example)).
Changing or recovering a password revokes the other sessions. OIDC is available as an
authentication option alongside local sign-in; its settings live in `.env.example`, and the
integration should be validated against whichever provider you choose.

The resources are documented under `/api/v1`; the earlier `/api` paths still work.
Authentication stays on `/auth`.

## Backups

The application keeps its history in two places: the database and the storage volume with
the uploaded files. Both have to be saved — the database knows which attachments exist, the
volume holds the bytes, and either one alone restores an installation that lists documents
it cannot open, or that holds files nothing references.

```bash
./scripts/backup.sh                      # writes to ./backups, keeps the 14 most recent
./scripts/backup.sh /destination 30      # your own destination and retention
./scripts/restore.sh backups/rodiva-…    # restores; asks for written confirmation
```

Each copy is a directory holding `database.sql.gz`, `storage.tar.gz` and a `manifest.txt`
with the date and the version. Run them from the directory holding `docker-compose.yml`,
with the stack up. For a daily copy, schedule `backup.sh` in the host's cron and keep the
destination off the machine.

A restore replaces the state wholesale: it empties the schema before replaying the dump, so
that restoring an old copy onto an already-migrated instance leaves no tables orphaned by
the migrations that came later.

Restore a copy into a test environment every once in a while: a backup that has never been
restored is an assumption, not a backup.

## Security

The API answers with `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy` and `Cross-Origin-Opener-Policy` on every response, attachment downloads
included; the nginx that serves the application applies the equivalent policy to the static
files. With `ENVIRONMENT=prod`, `Strict-Transport-Security` is added.

`ALLOWED_HOSTS` restricts the host names that are accepted. It is open by default, because a
self-hosted installation cannot guess its own name; an instance reachable from the internet
should name it.

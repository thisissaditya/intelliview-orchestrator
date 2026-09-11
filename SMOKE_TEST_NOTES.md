# Issue #48 — Clean-Clone Smoke Test Findings

## What was tested
Ran `docker compose up -d --build` from a fresh clone on a clean machine,
as required by Issue #48 (F6: Clean-Clone Smoke Test).

## Gap found
`docker-compose.yml` had the `healthcheck` key defined **twice** inside the
`grafana` service block — once after `volumes:` and again after `networks:`.
This caused the compose file to fail YAML parsing with the error:

error: yaml: construct errors: mapping key "healthcheck" already defined


As a result, `docker compose up -d --build` could not even start — this
blocked the smoke test entirely, so it was fixed rather than filed as a
separate ticket (it directly affects the file under test, not an unrelated
part of the system).

## Fix applied
Removed the duplicate `healthcheck` block (the `CMD-SHELL` variant that came
after `networks:`). Kept the first `healthcheck` block (the `CMD` variant,
right after `volumes:`), which follows the same pattern used by every other
service in the file.

## Result after fix
`docker compose up -d --build` completed successfully from a fresh clone.
All 13 services came up and reported `healthy`:
redis, postgres, fastapi, worker, frontend, celery-beat, celery-exporter,
flower, grafana, prometheus, jaeger, cv-service, digest-notifications.

No manual setup steps were required beyond the fix above.

## Verified manually
- `http://localhost:3000` — frontend loads (dashboard visible, empty since DB is fresh)
- `http://localhost:3001` — Grafana login page loads
- `http://localhost:8000/docs` — FastAPI docs page loads
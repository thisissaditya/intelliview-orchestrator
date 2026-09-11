# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security bugs.**

Email **rajatkumar7861813@gmail.com** with:
- A short description of the issue
- Steps to reproduce, including any session IDs / sample payloads
- The impact you believe it has (auth bypass, info leak, RCE, …)

You should receive an acknowledgement within 72 hours and a status update
every 7 days until the fix ships.

## Production hardening checklist

Before exposing this service to the public internet:

- [ ] Set a strong, unique `API_TOKEN` (>= 32 random bytes, base64).
      Default `"dev-token-change-me"` is rejected by the lifetime
      warning logged at startup.
- [ ] Set `CORS_ALLOW_ORIGINS` to an explicit, comma-separated list of
      trusted origins. Do **not** use `*` with credentials.
- [ ] Front the API with a TLS-terminating reverse proxy (nginx, Caddy,
      Traefik). Never expose `uvicorn` directly to the internet.
- [ ] Run Postgres and Redis on private subnets; restrict by network
      policy, not just password.
- [ ] Rotate `API_TOKEN` and any DB credentials regularly.
- [ ] Enable structured JSON logs (`JSON_LOGGING=1`) and ship them to
      your log aggregator.
- [ ] Mount the Docker image as non-root (already the default in the
      provided `Dockerfile`).
- [ ] Restrict `/switch-strategy`, `/retry-session/{id}`, and
      `/detect-failures` to admin-only callers via your reverse proxy
      if your `API_TOKEN` is shared with broader automation.

## Threat model (current)

- **Trusted operators** hold the `API_TOKEN`. They can start interviews,
  register workers, switch strategies, and trigger retries.
- **Workers** hold the same `API_TOKEN` in this release; a future
  release will split worker and operator scopes.
- **Public candidates** do not authenticate directly; their interview
  media is expected to flow through an ingest service you operate.
- **Database and Redis** are assumed to be on a private network.

## Dependencies

We run Dependabot (see `.github/dependabot.yml`) and review alerts
weekly. Security-relevant advisories are patched within 7 days of
release.


## Issue #85 — Security Verification Evidence

The existing security checklist was reviewed against the current repository configuration and implementation.

### Rate limiting verification

- `RateLimiterMiddleware` is applied globally in `orchestrator/main.py`.
- Current configuration is `60 requests per 60 seconds` per client key.
- The client key is derived from the client IP and optional `X-API-Token`.
- `/health`, `/docs`, and `/openapi.json` are exempt from rate limiting.
- Existing rate-limiter tests pass: `7 passed`.
- Sensitive endpoints including `/switch-strategy`, `/retry-session/{session_id}`, and `/detect-failures` require `X-API-Token`.
- **Gap:** sensitive endpoints currently use the same global `60 requests/minute` limit. No stricter endpoint-specific rate limit is configured. This is documented as a configuration gap; no new rate-limiting algorithm is introduced by this issue.

### Production hardening checklist verification

- [ ] Strong unique `API_TOKEN` — **OPEN**. The current configuration still defines `dev-token-change-me` as the default token.
- [ ] Explicit CORS origins — **OPEN**. The current default is `*`.
- [ ] TLS-terminating reverse proxy — **OPEN / NOT VERIFIED**. No nginx, Caddy, or Traefik configuration was found in the repository.
- [ ] Private Redis and Postgres — **OPEN**. `docker-compose.yml` publishes Redis on `6379:6379` and Postgres on `5432:5432`.
- [ ] Regular credential rotation — **OPEN / NOT VERIFIED**. No credential rotation mechanism or documented rotation evidence was found.
- [x] Structured JSON logs — **VERIFIED**. `JSON_LOGGING` defaults to `1` and `JsonFormatter` is used when enabled.
- [x] Docker image runs as non-root — **VERIFIED**. The provided `Dockerfile` creates the `app` user and sets `USER app`.
- [ ] Admin-only sensitive endpoints via reverse proxy — **OPEN / NOT VERIFIED**. Sensitive endpoints require the shared `API_TOKEN`, but the repository does not provide evidence of separate reverse-proxy admin restrictions.

### Verification status

This review confirms that the global rate limiter is active and functioning, and that sensitive mutation/recovery endpoints are authenticated. The main remaining rate-limiting gap is the absence of stricter per-endpoint limits for sensitive operations.

The unchecked production hardening items remain open because the current repository configuration does not provide sufficient evidence that those production controls are enabled.

# Security Audit Follow-Up Tickets

## Purpose

This document consolidates the remaining security hardening findings and recommendations identified during the security audit and stabilization review.

The findings are prioritized according to their potential security impact and converted into actionable follow-up tickets that can be assigned to interns or development team members.

---

# Priority Definitions

* **P0 – Critical:** Must be addressed before production/public exposure.
* **P1 – High:** Important security control that should be addressed soon.
* **P2 – Medium:** Security hardening or validation improvement that should be scheduled.

---

# SEC-001 — Configure GitHub Branch Protection

**Priority:** P0 – Critical
**Suggested Owner:** Repository Maintainer / DevOps

### Finding

The stabilization review identified insufficient branch protection as a root cause of uncontrolled merges.

### Impact

Without branch protection, changes may be merged directly into `main` without proper review or successful CI validation.

### Action

Configure branch protection rules for the `main` branch.

### Recommended Remediation

* Require at least one approved pull request review.
* Require successful CI/CD checks before merging.
* Block direct pushes to `main`.
* Require conversation resolution where appropriate.
* Review repository permissions to ensure interns cannot bypass the protection rules.

### Acceptance Criteria

* Direct pushes to `main` are blocked.
* At least one approval is required.
* Required CI checks must pass before merging.
* Branch protection settings are documented.

---

# SEC-002 — Remove and Reject Default API Token in Production

**Priority:** P0 – Critical
**Suggested Owner:** Backend / DevOps

### Finding

The security policy identifies `dev-token-change-me` as the development/default API token and requires production deployments to use a strong unique token.

### Impact

Using a known default token in production could allow unauthorized users to access protected API endpoints.

### Action

Ensure production cannot operate using the default development token.

### Recommended Remediation

* Require `API_TOKEN` through secure environment configuration.
* Reject the known development token in production.
* Use a strong randomly generated token.
* Document secure token configuration.
* Rotate the token if it has been exposed.

### Acceptance Criteria

* Production rejects `dev-token-change-me`.
* A strong explicit API token is required.
* No production secret is committed to Git.
* Tests verify the default token cannot be used in production.

---

# SEC-003 — Restrict PostgreSQL and Redis Network Access

**Priority:** P0 – Critical
**Suggested Owner:** DevOps

### Finding

The security policy requires PostgreSQL and Redis to run on private networks and to be restricted using network policy.

### Impact

Direct exposure of database or Redis services increases the attack surface and could allow unauthorized access.

### Action

Ensure PostgreSQL and Redis are reachable only by services that require them.

### Recommended Remediation

* Place PostgreSQL and Redis on private/internal networks.
* Avoid unnecessary public port exposure.
* Configure firewall/security-group rules.
* Allow access only from required application services.
* Verify that external clients cannot directly access the services.

### Acceptance Criteria

* PostgreSQL is not publicly accessible.
* Redis is not publicly accessible.
* Application services continue to communicate successfully.
* Network restrictions are documented.

---

# SEC-004 — Configure Explicit CORS Origins

**Priority:** P1 – High
**Suggested Owner:** Backend Developer

### Finding

The security policy requires `CORS_ALLOW_ORIGINS` to contain an explicit list of trusted origins and prohibits using `*` with credentials.

### Impact

Overly permissive CORS configuration can allow untrusted websites to interact with browser-accessible API resources.

### Action

Replace wildcard CORS configuration with an explicit production allowlist.

### Recommended Remediation

* Define trusted frontend origins.
* Configure origins through environment variables.
* Do not use `*` when credentials are enabled.
* Add tests for allowed and rejected origins.

### Acceptance Criteria

* Production uses explicit trusted origins.
* Unknown origins are rejected.
* CORS configuration is documented.
* Automated tests cover the configuration.

---

# SEC-005 — Configure TLS-Terminating Reverse Proxy

**Priority:** P1 – High
**Suggested Owner:** DevOps

### Finding

The security policy requires the API to be placed behind a TLS-terminating reverse proxy such as nginx, Caddy, or Traefik.

### Impact

Directly exposing the application server without appropriate TLS protection can expose API traffic and authentication credentials.

### Action

Deploy the API behind a properly configured HTTPS reverse proxy.

### Recommended Remediation

* Configure nginx, Caddy, or Traefik.
* Enable HTTPS.
* Redirect or block plain HTTP traffic.
* Forward required requests to the application server.
* Configure certificate renewal.

### Acceptance Criteria

* Public API traffic uses HTTPS.
* HTTP traffic is redirected or blocked.
* Certificates are valid and renewable.
* Reverse-proxy configuration is documented.

---

# SEC-006 — Restrict Sensitive Administrative Endpoints

**Priority:** P1 – High
**Suggested Owner:** Backend / DevOps

### Finding

The security policy identifies the following sensitive endpoints:

* `/switch-strategy`
* `/retry-session/{id}`
* `/detect-failures`

These should be restricted to admin-only callers when the API token is shared with broader automation.

### Impact

If a shared API token is available to workers or automation, those credentials may provide access to sensitive administrative operations.

### Action

Implement separate authorization controls for sensitive administrative endpoints.

### Recommended Remediation

* Introduce separate operator/admin permissions or scopes.
* Restrict sensitive endpoints to authorized administrators.
* Avoid sharing administrative credentials with workers.
* Add authorization tests.

### Acceptance Criteria

* Unauthorized users cannot access admin endpoints.
* Worker credentials cannot perform admin-only operations.
* Authorization failures return appropriate HTTP responses.
* Tests cover authorized and unauthorized requests.

---

# SEC-007 — Enable E2E Smoke Tests in CI

**Priority:** P2 – Medium
**Suggested Owner:** QA / DevOps / Intern

### Finding

The stabilization review notes that `tests/test_e2e_smoke.py` is not currently included in the normal CI validation because database dependencies need to be started correctly.

### Impact

Security and integration regressions may not be detected automatically before changes are merged.

### Action

Enable the E2E smoke test suite in GitHub Actions using the required Docker Compose services.

### Recommended Remediation

* Start PostgreSQL and Redis during CI.
* Start the application stack.
* Execute `tests/test_e2e_smoke.py`.
* Fail the CI workflow when E2E tests fail.

### Acceptance Criteria

* E2E tests run automatically in CI.
* PostgreSQL and Redis start successfully.
* E2E failures cause CI failure.
* CI results are visible to pull requests.

---

# SEC-008 — Implement Credential Rotation and Secure Deployment Secrets

**Priority:** P2 – Medium
**Suggested Owner:** DevOps

### Finding

The security policy requires regular rotation of API and database credentials. The stabilization review also recommends connecting staging database secrets through GitHub Secrets.

### Impact

Long-lived or poorly managed credentials increase the impact of accidental exposure or compromise.

### Action

Create a documented secret-management and credential-rotation process.

### Recommended Remediation

* Store deployment secrets using GitHub Secrets or an appropriate secret manager.
* Remove real credentials from tracked files.
* Keep `.env.example` limited to safe placeholders.
* Define a credential rotation schedule.
* Document emergency credential rotation.
* Test token/database credential rotation.

### Acceptance Criteria

* No real credentials are committed to Git.
* Staging secrets are provided through secure secret storage.
* Credential rotation procedure is documented.
* API and database credential rotation is tested.

---

# Ticket Summary

| Ticket  | Priority | Finding                                | Suggested Owner      |
| ------- | -------- | -------------------------------------- | -------------------- |
| SEC-001 | P0       | Configure GitHub branch protection     | Maintainer / DevOps  |
| SEC-002 | P0       | Remove/reject default API token        | Backend / DevOps     |
| SEC-003 | P0       | Restrict PostgreSQL and Redis          | DevOps               |
| SEC-004 | P1       | Configure explicit CORS                | Backend              |
| SEC-005 | P1       | Configure TLS reverse proxy            | DevOps               |
| SEC-006 | P1       | Restrict admin endpoints               | Backend / DevOps     |
| SEC-007 | P2       | Enable E2E tests in CI                 | QA / DevOps / Intern |
| SEC-008 | P2       | Credential rotation and GitHub Secrets | DevOps               |

## Previously Remediated Audit Findings

The stabilization report records that several earlier repository issues were already fixed. These should not be reopened as new tickets unless a regression is discovered.

Previously remediated items include:

* README merge-conflict artifacts.
* Unrelated project directories.
* Duplicate root worker implementation.
* Committed Node installer binaries.
* Vulnerable Next.js dependency identified during stabilization.
* Duplicate/unpinned Python dependencies.
* Redundant pytest configuration.
* Missing Celery test discovery.
* Missing frontend test execution in CI.
* Unsafe Dependabot auto-merge behavior.

## Verification Process

A ticket should be marked complete only after:

1. The remediation has been implemented.
2. Appropriate automated tests have been added or updated.
3. CI passes.
4. The security control has been manually verified where required.
5. Documentation has been updated.
6. The pull request has been reviewed and approved.

## Source Documents

* `SECURITY.md`
* `STABILIZATION_REPORT.md`

# API_TOKEN Security Review

## Scope

This review covers how `API_TOKEN` is handled by the application, including authentication, logging, API responses, WebSocket connections, frontend storage, and production token rotation.

## Findings

### 1. Application logging

The application does not log the actual `API_TOKEN`.

Authentication code logs only a generic warning when the development default token is configured. Request logging records the HTTP method, URL path, status, request ID, and duration, but does not record request headers or the full query string.

### 2. API responses and errors

Authentication failures return generic messages such as:

`invalid or missing API token`

The submitted token is not included in authentication error responses.

The Digest Notifications service similarly returns a generic authentication error and does not echo the submitted token.

### 3. WebSocket token exposure risk — remediated

The dashboard WebSocket previously authenticated using:

`?token=<API_TOKEN>`

This exposed the API token in the WebSocket URL and could potentially have allowed exposure through browser history, proxy/access logs, monitoring systems, or other URL-capturing infrastructure.

This has been remediated. The WebSocket URL no longer contains the API token. The client connects without credentials in the URL and sends an authentication message over the established WebSocket connection. The server validates the token before registering the connection.

The repository audit confirms that the previous `ws/metrics?token=...` pattern is no longer present.

### 4. Digest Notifications URL token exposure — remediated

The Digest Notifications frontend previously accepted an API token from the page URL using the `token` query parameter and stored it in browser session storage.

This has been remediated. The frontend no longer reads API tokens from URL query parameters. Users must provide the token through the application UI, and authenticated API requests send it using the `X-API-Token` header.

The token is therefore no longer accepted through a URL query parameter by the Digest Notifications frontend.

### 5. Browser localStorage exposure risk

The main frontend currently stores the API token in browser `localStorage`.

Any JavaScript executing on the same origin can access values stored in `localStorage`. Therefore, an XSS vulnerability could expose the API token.

Production deployments should avoid persistent browser storage for privileged long-lived API credentials where possible.

### 6. Default token protection

The application rejects the known development default `dev-token-change-me` during production startup.

Production deployments must provide a strong, unique API token through secure environment or secret management.

## Production Token Rotation Strategy

### Normal rotation

1. Generate a new cryptographically random API token.
2. Store the new token in the production secret manager or deployment environment. Never commit it to source control.
3. During a planned rotation, temporarily support both the current and new token if zero-downtime rotation is required.
4. Deploy or restart application components using the new token.
5. Update workers, automation clients, and other trusted consumers to use the new token.
6. Verify authenticated API and worker operations using the new token.
7. Revoke or remove the old token after all consumers have migrated.
8. Review logs and deployment configuration to ensure the old token is no longer being used.

### Emergency rotation

If the token is suspected to be exposed:

1. Treat the token as compromised immediately.
2. Generate a new token.
3. Update the production secret configuration.
4. Restart or redeploy affected services and trusted clients.
5. Revoke the compromised token as soon as the new token is confirmed working.
6. Review available logs and access records for suspicious activity.
7. Document the incident and identify the exposure source.

### Rotation frequency

Token rotation should follow the organization's credential-management policy. A token should also be rotated immediately after suspected or confirmed exposure, unauthorized access, personnel or access changes, or other security events.

## Security Requirements

- Never log the API token or `Authorization` header.
- Never include the API token in API responses or error messages.
- Never commit production API tokens to source control.
- Do not place API tokens in URLs or query parameters.
- Use TLS for production API and WebSocket connections.
- Use a strong, unique randomly generated production token.
- Store production secrets using the deployment platform's secret-management facilities.
- Rotate credentials according to the organization's security policy and immediately when exposure is suspected.
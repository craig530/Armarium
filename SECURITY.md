# Security Policy

## Supported Versions

Only the latest release receives security fixes. Patch versions are released promptly for confirmed vulnerabilities.

| Version | Supported |
| ------- | --------- |
| Latest  | ✅        |
| Older   | ❌        |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately by emailing **admin@armarium.app**. Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- The Armarium version you tested against

You should receive an acknowledgement within 48 hours and a resolution timeline within 7 days. Once a fix is released, a public advisory will be added to this repository.

## Scope

Armarium is designed to be deployed on a private network or behind a reverse proxy that you control. The security model assumes:

- The host running Armarium is trusted infrastructure under your control.
- HTTPS termination (TLS) is handled by a reverse proxy you operate (e.g. nginx, Caddy, Traefik).
- Access is restricted to your household or organisation — not exposed to the public internet without authentication.

With that context, the following are **in scope** for responsible disclosure:

- Authentication bypass or privilege escalation (e.g. accessing another user's data, gaining admin without credentials)
- Server-side request forgery (SSRF) via cover art URLs or metadata fetches
- SQL injection or arbitrary code execution
- Sensitive data exposure (tokens, passwords, session data) via API responses or logs
- Significant cross-site scripting (XSS) in the web interface

The following are **out of scope**:

- Vulnerabilities that require physical access to the host machine
- Issues that only affect deployments where the attacker already has admin credentials
- Rate limiting bypass on a private, single-household deployment
- Self-XSS or issues requiring social engineering of the instance owner
- Dependency vulnerabilities with no known exploitation path against Armarium's usage

## Security Design Notes

- **Passwords** are hashed with bcrypt (cost factor 12).
- **Sessions** use short-lived signed JWTs (HS256); tokens are stored in `HttpOnly` cookies.
- **External URL fetching** (cover art, metadata) is guarded by an SSRF allowlist (`services/cover_art._is_safe_url`) that blocks private IP ranges and resolves hostnames before making requests.
- **File uploads** are validated for content type and size before processing (`services/asset_upload.py`).
- **SQL** is generated exclusively through SQLAlchemy ORM — no raw string interpolation.
- **Rate limiting** is applied to the login endpoint (10 attempts per 5 minutes per IP).

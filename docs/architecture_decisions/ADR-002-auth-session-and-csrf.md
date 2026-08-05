# ADR-002: Auth, Session, and CSRF

Date: 2026-08-05
Status: Accepted for MVP planning

## Context

Phase 1 must implement local login, role-based access control, project CRUD, archive, audit foundation, and browser UI flows. The SRS allows secure local authentication but does not fully choose between browser JWT and cookie sessions. Because Phase 1 includes state-changing browser requests, session invalidation, generic login errors, and security regression tests must be locked before implementation starts.

## Decision

Use opaque server-side session IDs carried in HTTP-only cookies.

Session token format:

- Browser receives an opaque random session ID only.
- Do not store JWT access tokens in the browser for MVP auth.
- Session IDs must be generated with cryptographically secure randomness.
- Session records are stored server-side in PostgreSQL or Redis.

Cookie behavior:

- Cookie is HTTP-only.
- Cookie uses `SameSite=Lax`.
- Cookie uses `Secure=true` in production.
- Local development may use `Secure=false` only when `APP_ENV=development`.
- Cookie path is scoped to the application.

CSRF:

- State-changing requests require a CSRF token.
- Safe methods such as `GET`, `HEAD`, and `OPTIONS` do not mutate state.
- Login, logout, project create/update/archive, and later upload/review/export actions are protected according to the state-changing rule.

Session lifecycle:

- Logout invalidates the server-side session.
- Expired sessions are rejected even if the browser still has a cookie.
- Sessions have an idle timeout.
- Sessions have an absolute timeout.
- Timeout values are environment-configured with safe defaults.

Development seed user:

- Seed users are allowed only when `APP_ENV=development`.
- The seed password is read from environment.
- No committed file may contain a real seed password.
- Missing seed-password configuration must fail clearly in development seed setup.

Login failure and rate limiting:

- Login errors are generic and must not reveal whether an account exists.
- Login is rate limited by IP and account identifier hash.
- Rate-limit storage must be server-side.
- Audit/security events should record login success, logout, and rate-limit/security-relevant failures without logging plaintext passwords.

## Consequences

Positive:

- Server-side invalidation is straightforward.
- Browser token exposure is reduced.
- Cookie behavior and CSRF tests are concrete before Phase 1 starts.
- Auth remains local and simple enough for MVP.

Tradeoffs:

- CSRF handling is required for mutating browser requests.
- API clients outside the browser need documented session/CSRF behavior.
- Session storage must be available with the API service.

## Alternatives Considered

### Browser JWT

Rejected for MVP. JWT can work, but browser storage and revocation introduce avoidable complexity for a local MVP with server-rendered/API-driven UI flows.

### Stateless sessions only

Rejected for MVP. Logout and server-side invalidation are required security behaviors.

### SameSite Strict

Not selected for MVP default because `Lax` provides practical browser behavior for local app navigation while still reducing CSRF exposure. Explicit CSRF token validation remains required for state-changing requests.

## Enforcement

Phase 1 must include tests for:

- Successful login.
- Generic login failure.
- Password hash verification.
- Cookie flags.
- CSRF rejection for state-changing requests without a valid token.
- Logout invalidates the server-side session.
- Idle or absolute timeout rejection.
- Development seed user disabled outside `APP_ENV=development`.
- Seed password read from environment.
- Login rate limit by IP plus account identifier hash.

Phase 1 cannot close as `PASS` if these controls are skipped or left as unresolved decisions.

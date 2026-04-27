# Rate Limiting Plan

This plan defines endpoint abuse protection for this app so traffic spikes, bots, and spam requests do not overwhelm the API.

## Goals

1. Protect endpoints from request floods and brute-force traffic.
2. Keep normal users responsive during load.
3. Return predictable responses (`429` + `Retry-After`) when limits are exceeded.
4. Add observability so limits can be tuned safely.

## Scope

- ASP.NET Core app-level rate limiting (`Microsoft.AspNetCore.RateLimiting`).
- Endpoint policy design for anonymous vs authenticated traffic.
- Logging/metrics and rollout strategy.

## Non-Goals

- Full L3/L4 DDoS mitigation (handled at hosting/WAF/network layer).
- Replacing auth/authorization controls.

## Layered Defense (Recommended)

1. Edge/WAF layer:
   - Use provider-level DDoS protection and bot filtering (Cloudflare/Azure/AWS).
   - Apply coarse IP reputation rules before traffic reaches app.
2. App layer:
   - Enforce endpoint-level rate limiting and concurrency caps.
3. Data layer:
   - Keep expensive endpoints cached/indexed to reduce blast radius.

## Endpoint Classes And Default Limits

## 1) Public read endpoints (anonymous GET)
- Policy: Sliding window by IP.
- Suggested start: `60 requests / minute / IP`.
- Queue: small (`5`) with oldest-first.

## 2) Auth endpoints (`/Identity/*`, login/register)
- Policy: Strict fixed window by IP + username/email key.
- Suggested start: `10 requests / 5 minutes`.
- Queue: `0` (fail fast).
- Add optional CAPTCHA trigger after repeated failures.

## 3) Mutating endpoints (POST/PUT/PATCH/DELETE)
- Policy: Token bucket by user id (fallback IP for anonymous).
- Suggested start: burst `20`, refill `1/sec`.
- Queue: `0`.

## 4) Heavy upload endpoints (TUS upload)
- Policy: Concurrency limiter + request rate cap.
- Suggested start: max concurrent uploads `2` per user/IP.
- Separate strict limits for create/finalize endpoints.

## 5) Admin-only endpoints
- Policy: Higher per-user limits than public, still bounded.

## ASP.NET Core Implementation Plan

1. Add and configure rate limiter in `Program.cs`:
   - `builder.Services.AddRateLimiter(...)`
   - Define named policies: `public-read`, `auth`, `mutating`, `uploads`, `admin`.
2. Partition keys:
   - Authenticated: `User.Identity.Name` or user id claim.
   - Anonymous: forwarded client IP.
3. Middleware order:
   - `UseForwardedHeaders()` before rate limiting if behind proxy.
   - `app.UseRateLimiter()` before endpoint mapping.
4. Endpoint mapping:
   - Apply `.RequireRateLimiting("policy-name")` per route group.
5. Rejection response:
   - Set status `429`.
   - Include `Retry-After` header.
   - Return concise problem payload.

## Proxy/Deployment Requirements

- Trust real client IP from proxy headers only from known proxies.
- Ensure `X-Forwarded-For` / `X-Forwarded-Proto` are correctly configured.
- If running multiple app instances, prefer distributed counters (Redis-backed approach) for consistent limits.

## Observability

Track and dashboard:
- Total requests by endpoint and status.
- `429` count by policy and partition key type (IP/user).
- Top blocked IPs/users.
- Latency before/after enabling limits.

Log fields:
- `RateLimitPolicy`
- `RateLimitPartition`
- `RetryAfterSeconds`
- `Endpoint`

## Testing Plan

1. Unit tests:
   - Policy registration and key partition logic.
2. Integration tests:
   - Exceed limits and verify `429` + `Retry-After`.
   - Verify normal traffic remains `200`.
3. Load tests:
   - Simulate abusive IPs and normal users together.
   - Confirm normal users still succeed under attack simulation.

## Rollout Plan

1. Add middleware and policies with conservative limits in non-prod.
2. Monitor `429` rates and false positives.
3. Adjust thresholds per endpoint class.
4. Enable in production behind feature flag/config toggle.
5. Re-tune weekly based on real traffic.

## Acceptance Criteria

- All endpoint groups have explicit rate-limiting policy.
- Exceeding limits returns `429` with `Retry-After`.
- No major false-positive blocking for normal traffic.
- Dashboards show blocked traffic and policy effectiveness.

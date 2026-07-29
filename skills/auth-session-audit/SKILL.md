---
name: auth-session-audit
description: Test session and authentication lifecycle edge cases using a real browser — session expiry mid-flow, concurrent sessions across simulated devices, whether logout in one tab propagates to another, remember-me persistence, password reset token expiry/reuse, and whether logged-out state is reachable via the back button. Use whenever the user wants to check session handling, auth edge cases, "what happens when a session expires," concurrent login behavior, or remember-me correctness — trigger on phrases like "test session expiry," "check auth edge cases," "does logout work across tabs," or "test remember me." Distinct from flow-runner's login scenario, which verifies the happy path once — this tests the lifecycle around it. Includes one narrowly-scoped, opt-in check for a documented lockout/rate-limit policy; never probes for undocumented limits by trial and error, and that's the closest this skill comes to security testing — everything else here is session-state and UX correctness.
---

# Playwright Auth/Session Audit

`flow-runner` verifies that logging in works. This checks what happens around that — session expiring mid-task, two sessions existing at once, logout not fully propagating, a "remember me" checkbox that doesn't actually do what it says.

## Relationship to the other skills

Reuse `scenario-mapper`'s `Auth` flow-type entries to know where the login/session surfaces are, rather than rediscovering them. This is a lifecycle check layered on top of what `flow-runner` already verified once — it doesn't replace that happy-path verification, it tests the edges around it.

## Core principles (and why)

**Use separate browser contexts for "different devices," multiple pages in one context for "different tabs."** These are genuinely different scenarios with different expected behavior. A real second device has its own independent cookie jar — simulate that with a separate Playwright browser context. A second tab of the same browser shares cookies and storage with the first — simulate that with two pages inside one context. Testing "does logout in one tab affect another" using two separate contexts wouldn't actually be testing what it looks like it's testing.

**Manipulate session state directly rather than waiting out a real timeout.** A 30-minute or 24-hour expiry isn't practical to sit through. Clear or overwrite the session cookie/token directly via the browser context's cookie APIs, then take the next action and observe — this gets the same test in seconds. Be explicit in the report about what was actually simulated this way versus what would need a genuinely longer-running test to confirm (the exact stated duration itself, for instance, isn't verified just because expiry-handling behavior was).

**There's no single correct answer for concurrent sessions — verify the behavior is intentional and consistent, not that it matches an assumption.** Some apps deliberately allow simultaneous sessions from multiple devices; others intentionally invalidate the older one on a new login. Neither is inherently wrong. What matters is whether the actual behavior is clear and consistent rather than undefined or confusing — flag it for the team to confirm it matches their intended policy rather than grading it against an assumed "correct" answer.

**A logged-out state should never be reachable via the back button.** After logout, pressing back shouldn't reveal cached authenticated content. No special technique needed here — log out, click back, look at what's shown.

**Scope any lockout/rate-limit check narrowly, and only if a policy is actually documented.** If the app states an account-lockout or rate-limiting policy, verify it activates as described, using only your own test account, and stop the moment the stated threshold triggers. Never probe for an undocumented limit by trial and error — that stops being verification of a stated control and starts being something else, which isn't this skill's job.

**Distinguish "handled it well" from "technically didn't crash."** Same instinct as `form-fuzzing`: a session expiring mid-checkout should redirect to login with a clear message and, ideally, not silently discard in-progress work — not just fail to crash while doing something confusing.

## Checks

1. **Session expiry mid-flow** — start a multi-step flow, invalidate the session directly (cookie/token manipulation) partway through, attempt to continue. Expect a clear redirect to login, not silent failure or data loss.
2. **Concurrent sessions** — log in from two separate browser contexts with the same account. Note the actual behavior (both work / second invalidates first / something undefined) and flag for policy confirmation rather than judging it against an assumption.
3. **Logout propagation across tabs** — two pages, same context, both authenticated. Log out in one. Check whether and how quickly the other notices on its next action.
4. **Remember-me persistence** — verify checked persists session-equivalent state across a simulated restart (new context reusing saved storage state), and unchecked does not.
5. **Password reset token behavior** — verify a used token can't be reused (single-use enforcement) and that an obviously invalid/malformed token fails clearly. Note if time-based expiry itself wasn't practically verified (see the principle above) rather than implying it was.
6. **Back button after logout** — log out, press back, observe.
7. **Lockout/rate-limit policy** (only if documented) — verify it triggers as stated, own test account only, stop at threshold.

## Report format

```markdown
## Auth/Session Audit: [site]

| # | Check | Expected/Acceptable | Actual | Result |
|---|---|---|---|---|
| 1 | Session expiry mid-checkout | Redirect to login, clear message, work not silently lost | Silently redirected to homepage, cart emptied | ❌ |
| 2 | Concurrent sessions (2 devices) | Consistent, intentional-looking behavior | Both work simultaneously, no indication either way | ⚠️ Flag for policy confirmation |
| 3 | Logout — tab B notices | Redirected to login on next action | Tab B kept working until manual refresh | ❌ |
| 4 | Remember-me checked | Persists across restart | Persisted correctly | ✅ |
| 5 | Remember-me unchecked | Does not persist | Persisted anyway | ❌ |
| 6 | Reset token reuse | Second use fails | Second use succeeded | ❌ |
| 7 | Back button after logout | Login page, no cached content | Cached authenticated page shown | ❌ |
```

## After the check

Give a short summary — real failures first, and the concurrent-sessions result framed as "needs policy confirmation" rather than pass/fail if there's no stated intended behavior to check it against. If a failure needs deeper investigation before it's clear what's actually going wrong, hand it to `bug-triage` same as any other failure.

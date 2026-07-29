---
name: network-assertion
description: Observe, assert on, and mock network/API traffic during a browser session using Playwright (route interception via @playwright/cli, the MCP server's browser_route/network tools, or raw page.route()) — simulate error responses, slow responses, and empty states without a real backend, and assert on real traffic like status codes, payload shape, duplicate calls, or calls to unexpected endpoints. Use whenever the user wants to test an API error state, loading state, or empty state; verify what network calls a page makes; simulate a backend failure, timeout, or 500; check that no unwanted or duplicate requests fire; or assert on a request/response payload — trigger even without the words "mock," "route," or "Playwright." Complements flow-runner (executes the UI-level flow) and scenario-mapper (whose "Negative" scenario_class entries — API failures, timeouts — usually need this skill's mocking to actually happen, since a live backend won't reliably fail on demand).
---

# Playwright Network Assertion

Two things this does, often together: **watch** real network traffic and assert on it (status codes, duplicate calls, payload shape, calls to endpoints that shouldn't be hit), and **mock** traffic to synthesize states a live backend won't reliably produce on demand — a 500, a timeout, an empty result set, a dropped connection.

## Relationship to the other skills

A `scenario-mapper` comprehensive-mode row like "payment API returns 500 mid-checkout" or a `flow-runner` negative-path step can't be executed against a real backend that's (hopefully) not actually broken right now — this skill is how those scenarios get run at all. If `bug-triage` traced a bug to a suspicious response ("looks like the 502 from `/api/cart` is what breaks the UI"), that's a correlation from a log until you mock that exact response deterministically and confirm the same symptom reproduces — that's the stronger form of evidence, and this skill is how you produce it.

## Before you start

Same check as the rest of the toolkit, with a specific ask this time: does your tool support **route interception** — the MCP server's `browser_route` (or similarly named network-mocking tool — check your actual tool list, this is a newer addition and naming may vary by version) or, on `@playwright/cli` / raw Playwright, `page.route()` / `context.route()`. Passive observation (just watching traffic go by) is usually available even without full interception — check for a network-log or `browser_network_requests`-style tool if that's all a given check needs.

## Core principles (and why)

**Register mocks before the request fires, not after.** A route handler set up after the app has already sent the request is too late — it'll just be real traffic. Set up interception before triggering whatever action causes the call (the button click, the page load), not as an afterthought once you notice the response looks wrong.

**Know which of the three actions you actually want.** Route interception generally gives you: **fulfill** (replace the response entirely with synthetic data), **continue** (pass through to the real server, optionally modifying the request/response), or **abort** (block it — simulating a dropped connection or network failure, not a normal HTTP error the app can parse). These are meaningfully different tests: "the API returns a 500" and "the network drops entirely" often exercise different error-handling code paths, and an app that handles one gracefully may not handle the other. Pick deliberately based on what you're actually trying to verify.

**Scope your URL patterns as narrowly as the check needs.** A broad pattern like matching everything under `/api/` is convenient but risks silently intercepting calls you didn't mean to touch — an auth-refresh request, a different endpoint that happens to share a path prefix — which can break the rest of the flow in a confusing way that looks like an unrelated failure. Match the specific endpoint you're testing.

**A mocked pass means "the UI handles this response shape," not "the API actually behaves this way."** Mocking is exactly right for reliably testing how the app handles a state you can't easily force from a real backend — but it can't tell you whether the real API would ever actually return what you mocked. Don't let a suite full of green mocked checks substitute entirely for occasionally verifying the same flow against the real backend; note this distinction in the report rather than letting mocked and real results blur together.

**If a mock doesn't seem to take effect, check for a service worker before assuming your pattern is wrong.** A service worker (or a mocking library like MSW that installs one) can intercept requests before your route handler ever sees them, making it look like the mock silently failed. If real traffic still appears to be going through untouched, this is the first thing to rule out — not just fiddling with the URL pattern.

**Watch passively for things nobody explicitly asked you to check.** While driving any flow, it's worth noting (even without being asked to mock anything): repeated/duplicate calls to the same endpoint, calls to unexpected third-party or production domains during what should be a contained test, obviously sensitive data (tokens, passwords) appearing in a URL or plaintext request body, and response times that stand out as slow. These often surface real issues nobody was specifically looking for.

## Workflow

1. **Decide what you're doing:** observing real traffic, mocking a state that's hard to trigger live, or confirming a bug-triage hypothesis by replaying an exact failing response.
2. **For observation:** set up request/response capture before navigating or acting, run the flow, then assert against the captured log afterward — status codes, absence of unexpected endpoints, no duplicates, payload shape matching what's expected.
3. **For mocking:** register the route handler (fulfill/continue/abort, chosen deliberately) before triggering the action that fires the request. Drive the app through the resulting state the same way you would in `flow-runner` — wait for the actual expected UI outcome, don't just confirm the mock fired.
4. **If something doesn't behave as expected**, check for a service worker before concluding your pattern is wrong.
5. **Record the result** using the report format below.

## Report format

```markdown
## Network check: [name, e.g. "Checkout — payment API failure handling"]
**Result:** ✅ PASS / ❌ FAILED

| # | Check | Type | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | Mock `POST /api/payment` → 500 | Mocked | UI shows "payment failed, try again," no crash | Matched | ✅ |
| 2 | No duplicate `/api/analytics` calls during checkout | Passive | Exactly 1 call | 3 calls fired | ❌ |

**Evidence:** network log / HAR path, screenshot path if a UI assertion was involved
**Notes:** [flag here if a mocked check hasn't been cross-checked against real backend behavior recently]
```

`Type` (Mocked / Passive) matters enough to always include — it's the difference between "verified the app's handling of this" and "verified the app's actual current behavior," and a reader shouldn't have to guess which.

## After the check

If this ran as part of a larger flow (a `flow-runner` scenario, or several `scenario-mapper` negative-case rows), fold this table into that report rather than presenting a disconnected second document. If it ran standalone, a short chat summary — pass/fail counts, and anything that surfaced passively that nobody asked about — is enough; don't restate every row.

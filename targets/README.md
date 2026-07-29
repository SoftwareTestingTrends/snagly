# Target profiles

A target profile is what lets the Playwright skills (`scenario-mapper`,
`flow-runner`, `crud-tester`) run against **any** website without
rediscovering the same setup facts on every run.

Without a profile, each run re-derives — by trial and error — the base URL, where credentials
live, how login works, which tenant is safe to mutate, and which console errors are pre-existing
noise. That knowledge then evaporates when the session ends.

One file per environment: `targets/<app>-<env>.yaml`. Point a skill at it by name
("run the sanity suite against targets/myapp-staging.yaml") or let the skill pick the only
profile present. Copy `example.yaml` to start a new profile — real profiles are gitignored
(they describe your internal environments; only the example template is committed).

## Fields

| Field | Required | Purpose |
|---|---|---|
| `name` | yes | Human label used in run reports |
| `base_url` | yes | Entry point |
| `credentials.source` | yes | File holding secrets (`.env`) — **never put secrets in this file** |
| `credentials.username_key` / `password_key` | yes | Env var names to read from that source |
| `login` | if gated | Prose recipe for getting authenticated, including any post-login tenant/workspace picker |
| `tenants.safe_to_mutate` | for CRUD runs | Tenant where create/edit/delete is permitted. Omit if none exists — `crud-tester` then stops and asks rather than guessing |
| `tenants.read_only_rich_data` | optional | Tenant with realistic data, for read-path testing |
| `recovery` | optional | Known ways to unstick the app (clearing storage, etc.) |
| `known_noise` | optional | Pre-existing console/network errors. Assertions must not fail on these alone |
| `app_notes` | optional | Field constraints and gotchas learned from prior runs |

## Rules

1. **No secrets in profiles.** Profiles name the env vars; the values stay in `.env` (git-ignored).
2. **`known_noise` is evidence, not an excuse.** Every entry should trace to a filed defect or a
   deliberate accepted condition — otherwise it hides regressions.
3. **Update the profile when a run teaches you something.** `app_notes` and `known_noise` are how a
   run makes the next run cheaper. A profile that never changes after a failed run wasted the run.
4. **`safe_to_mutate` is a promise.** Only name a tenant whose data nobody else depends on.

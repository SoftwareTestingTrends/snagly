---
name: crud-tester
description: Test create, edit, and delete (CRUD/mutation) operations in a web app with a real browser, verifying the full data lifecycle of each entity and cleaning up via delete-as-test. Use whenever the user wants to test CRUD operations, mutation flows, data lifecycle ("does saving/updating/deleting actually work"), form persistence, or wants a test run that verifiably cleans up after itself. Complements scenario-mapper (read-only discovery) and flow-runner (journey execution that stops before side effects) — this is the skill that is ALLOWED to mutate, under strict self-containment rules.
---

# Playwright CRUD Tester

Tests that an app's create, edit, and delete operations actually work — as full
lifecycles, not isolated clicks. Where `flow-runner` stops before real
side effects, this skill deliberately performs them, and pays for that license
with strict data hygiene rules.

## Relationship to the other Playwright skills

- `scenario-mapper` discovers what exists (read-only).
- `flow-runner` owns the browser mechanics this skill runs on:
  snapshot → act → wait for state → assert, evidence saved per step, and the
  structured run-report format. Read it before executing; do not duplicate it.
- This skill adds the mutation policy layer: what you may touch, how entities
  are named, what order operations run in, and what the report must disclose.

## Target profiles

Read the target profile (`targets/*.yaml`, see `targets/README.md`) before any mutation. Two fields
are load-bearing for this skill: `tenants.safe_to_mutate` names the only tenant you may write to,
and `known_noise` lists pre-existing errors that must not fail your assertions. If no profile exists
or it declares no safe tenant, apply rule 1 and stop to ask. Append what the run teaches you —
field constraints, irreversibility discoveries — back into the profile's `app_notes` at the end.

## Core rules

**1. Self-contained data.** Mutate ONLY entities created during the current run.
Prefer a dedicated empty tenant (sandbox org, scratch workspace, test account)
when the app has one. Pre-existing records are off limits even when they look
like test data — they may be another tester's setup. If the app offers no safe
tenant and the user hasn't named one, stop and ask before any mutation.

**2. Run marker.** Compute a run-id (`YYYYMMDD-HHMM`) at start. Every created
entity carries `QA-CRUD-<run-id>` in its most visible text field (name, title,
or body). Anything the run leaves behind must be findable by searching that
marker.

**3. Lifecycle chains.** Each entity is one chain:
create → verify → edit → verify → delete → verify-gone.
- "Verify" means the change is visible where a user would look for it (list,
  detail view), ideally after a reload — not just an optimistic UI flash.
- "Verify-gone" means absence from the default views it previously appeared in.
  Soft-deletes (archive, deactivate) verify disappearance, not destruction.
- A failed step stops that entity's remaining chain (its state is now unknown)
  but other entities' chains continue.
- If an operation doesn't exist by design (e.g. permanent records that can't be
  edited or deleted), the chain step becomes a conformance assertion: verify the
  affordance is genuinely absent, and record it as PASS with a note.

**4. Irreversibility triage — before any execution.** Classify every planned
operation as one of: *reversible* (plain edit), *soft-delete*, *permanent
record* (can never be edited/removed), or *external side effect* (sends
email/SMS, charges money, notifies third parties). Permanent and external
operations require disposable targets (e.g. `user+alias@domain` emails that land
in the tester's own inbox) or explicit user sign-off. Present the triage as part
of the plan before the first mutation.

**5. Delete-as-test ordering.** Run all creates first, then edits, then deletes.
Deletes are scenarios with assertions — teardown IS the delete coverage, not a
best-effort wipe afterward. Order deletes so dependents go before their parents
(cancel the order before archiving the customer it belongs to).

**6. Residue report.** End the run report with a "Residue" section: every entity
left behind, why it could not be removed (soft-delete only, permanent by
design, chain failed mid-way), and the marker it carries. An empty residue
section must say so explicitly.

**7. Positive control before reporting a mutation as broken.** An absent network
request proves *your client* didn't send one — never that the app can't. Automation
failure and application failure produce identical evidence: nothing happened. Before
filing any "the mutation never fires" defect, establish that your automation can
complete that flow at all. Options, cheapest first: drive the same form successfully
with different values; check whether a comparable mutation elsewhere in the app works
under automation; or ask the user to perform the action manually once. Repetition is
not a control — reproducing a failure 5/5 times with the same flawed method measures
consistency, not validity. If no positive control is available, report it as
"could not complete under automation; unverified manually" and say which it is.

**8. A dialog disappearing is not success.** Multi-step confirmations are common on
exactly the destructive and creative actions this skill targets — "are you sure",
"confirm you would like to…". The confirming popup is frequently a *different* element
from the form (a portal root, no `role="dialog"`), so a check like
`querySelector('[role=dialog]')` goes empty and reads as "submitted" when the flow is
actually sitting on step two, waiting.

Never assert success on a dialog closing. Assert on the **mutation firing** or on the
**resulting row appearing**. When a submit produces no request and no error, look for a
second step before concluding anything: dump the text of portal containers
(`#popup-root`, `[data-popup]`, `[class*=popup]`), not just `[role=dialog]`. The
cheapest way to see the whole flow is to instrument in-page — count clicks reaching the
button, wrap `fetch`/`XHR` to log operation names — and always positive-control the
instrumentation itself by confirming it records a known-good request.

## Workflow

1. Take the scenario list (CSV or prose) — or run `scenario-mapper`
   style discovery limited to mutation affordances if none exists.
2. Do the irreversibility triage (rule 4) and present it with the planned
   chains and target tenant. Get confirmation if anything is permanent or
   external and not already covered by user instructions.
3. Compute the run-id; create the evidence directory (`runs/crud-<run-id>/`).
4. Execute chains per rules 3 and 5, following `flow-runner`
   mechanics (state waits, per-step assertions, evidence on every step,
   stop-and-preserve on failure).
5. Report using the flow-runner format, with one lifecycle table per entity
   (step | action | expected | actual | result) plus the Residue section.
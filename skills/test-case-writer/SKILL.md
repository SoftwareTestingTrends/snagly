---
name: test-case-writer
description: Expand a terse scenario (from a scenario-mapper row, or a plain description) into a detailed, persistent E2E test-case document — preconditions, test data, numbered steps each with its own expected result, postconditions — as a standalone artifact that exists before anything gets executed. Use whenever the user wants a written test case, a detailed test spec, a test case someone can review or sign off on, or a document to hand to manual QA. Distinct from flow-runner's step plan, which is written immediately before execution and thrown away — this produces a reviewable document that persists on its own, independent of whether or when it gets run. Does not execute anything or touch a browser directly.
---

# Playwright Test Case Writer

Fills the gap between `scenario-mapper`'s terse one-line `quick_steps` and `flow-runner`'s detailed-but-throwaway execution plan: a full test-case document that exists as its own artifact, reviewable and sign-off-able before anyone runs it.

## Relationship to the other skills

**Upstream:** takes a `scenario-mapper` row (or a plain-language description) as its starting point — reuse its priority and scenario name rather than re-deriving them.

**Downstream — this is the important part:** once written, this document *is* the step plan `flow-runner` would otherwise write inline and discard. If a test-case document already exists for a scenario, `flow-runner` should execute directly from it rather than writing a new throwaway plan from scratch. And when `flow-runner` runs it successfully, the document's own status should be updated from "inferred" to "verified" — that update is what makes it trustworthy input for `e2e-codegen` later, which should only work from verified test cases, never inferred ones.

That gives the full pipeline a real shape: `scenario-mapper` (discover) → `test-case-writer` (detail it into a spec) → `flow-runner` (execute against the spec, flip it to verified) → `e2e-codegen` (only touches verified specs, makes them permanent code).

## Core principles (and why)

**This is a document, not an execution.** No browser or MCP tool access needed — this is specification writing. The value is entirely in being precise and reviewable *before* a session runs it, whether that session is `flow-runner`, a human QA tester, or a future automated run.

**Expected result per step, not just at the end.** This is the single biggest structural difference from a terse scenario row or a quick conversational plan. A document that only states the final expected outcome leaves every intermediate step's correctness to interpretation — if step 3 of 7 does something subtly wrong but the final assertion happens to still pass, an end-only format would never catch it. Give every step its own expected result.

**Precision over prose.** Steps should be specific enough that two different people — or two different Claude sessions — executing the same document would do the exact same thing: name the actual button label or field, not "fill out the form"; name the actual test value, not "enter valid data." Ambiguity in a test case is itself a defect in the document.

**State preconditions and test data explicitly, don't bury them in step 1.** Whoever executes this needs to know upfront what has to already be true — logged in or not, cart empty, specific account tier, specific feature flag — before they can even attempt step 1. Pull it into its own section rather than making the reader infer it from context clues buried in the steps.

**Be honest about confidence — inferred is not the same as verified.** If this is written from a `scenario-mapper` row that's never actually been executed, the specific selectors and flow details are still a best-effort guess based on a shallow discovery pass, not confirmed fact. Mark the document's status plainly as **Inferred, not yet verified**. If it's written from (or after) a `flow-runner` run that actually confirmed the flow works as described, mark it **Verified**, with the date and source. This distinction is the whole reason `e2e-codegen` can trust one and not the other — don't blur it by writing both with the same confident tone.

**Concrete but safe test data.** Give real example values (a plausible test email, a specific product name) rather than vague placeholders like `<enter data>` — but synthetic/sandbox values, same preference as everywhere else in this toolkit, not real production data.

## Workflow

1. **Get the source scenario** — a `scenario-mapper` row or a plain description. Reuse its priority and name rather than inventing new ones.
2. **Determine confidence.** Has `flow-runner` already verified this flow? Write and label accordingly (see the honesty principle above) — this isn't optional framing, it changes what the document is allowed to claim.
3. **Write preconditions and test data** as their own explicit sections.
4. **Write numbered steps**, each with a specific action *and* its own expected result — not a chain of actions with one assertion at the end.
5. **Write postconditions** — what state is left behind, and whether cleanup is needed (e.g., delete a test account created during the flow).
6. **Save** per the format below.

## Test case format

```markdown
# Test Case: [TC-001] — [Scenario name]

**Priority:** P0 / P1 / P2
**Status:** Verified (via flow-runner, [date]) — or — Inferred from exploration, not yet verified
**Source:** scenario-mapper row [id], or [other origin]

## Preconditions
- [e.g., "User has a valid, unauthenticated session"]
- [e.g., "At least one item exists in the product catalog"]

## Test data
- [e.g., "Email: test+<timestamp>@example.com"]
- [e.g., "Password: any valid 8+ character test password"]

## Steps

| # | Action | Expected Result |
|---|---|---|
| 1 | Navigate to /login | Login form displayed with email and password fields |
| 2 | Enter valid credentials, click "Log in" | Redirected away from /login; account menu visible in header |
| 3 | ... | ... |

## Postconditions
[e.g., "User session is authenticated" / "No cleanup needed" / "Delete test account via admin panel"]

## Notes
[Edge cases, environment-specific concerns, anything worth flagging for whoever executes this]
```

## Output location

`test-cases/<id>-<slug>.md`, one file per test case — same reasoning as `bug-triage`'s one-file-per-bug pattern. If writing several at once, add a short index (ID, title, priority, status) in chat rather than pasting every full document inline.

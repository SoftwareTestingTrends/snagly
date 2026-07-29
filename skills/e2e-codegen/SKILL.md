---
name: e2e-codegen
description: Convert a scenario that's already been verified by flow-runner (or network-assertion / cross-browser-matrix for their scenario types) into a permanent, runnable @playwright/test spec file — with role-based locators, real assertions per step, no fixed-time waits, dynamic test data, and shared auth fixtures. Runs the generated test immediately to confirm it actually passes before handing it over. Use whenever the user wants to turn a tested flow into an automated test, generate Playwright test code, "make this a real test," or add something to a CI test suite. Do not use this to generate code from an unverified scenario-mapper row — verify it via flow-runner first, since generating code from a scenario that's never actually been run bakes untested assumptions into something that looks more authoritative than it is.
---

# Playwright E2E Codegen

Turns "I ran this conversationally and it passed" into "this is now a committed test file CI runs on its own." This is the one skill in the toolkit whose output outlives the conversation — everything else here reports on a session; this one produces code.

## Relationship to the other skills

Input is a **verified** scenario — one `flow-runner` has already executed and confirmed passes, or a mocked negative case `network-assertion` confirmed behaves correctly, or a matrix cell `cross-browser-matrix` confirmed holds across engines/viewports. Not a raw `scenario-mapper` row — that's a hypothesis about what's worth testing, not a confirmed fact about how the site behaves. Generating code straight from an unverified hypothesis just moves an unchecked assumption into a form that reads as more trustworthy than it is. If asked to codify something that hasn't been run yet, verify it first.

Output feeds `test-plan`'s coverage ledger — once a test is generated and passing, that ledger's "Automated (e2e-codegen)?" column should reflect it. A ledger that isn't updated when this skill runs is worse than no ledger, since it actively misrepresents coverage.

## Core principles (and why)

**Every step becomes a real assertion, not just an action.** Same discipline as `flow-runner`, now expressed permanently in code: a generated test that's all clicks with no `expect()` calls is a flake detector at best, not a correctness check. Translate each step's expected outcome from the source scenario directly into an assertion — don't just replay the clicks.

**Use resilient, role-based locators.** `getByRole`, `getByLabel`, `getByText` — not CSS selectors tied to a class name or DOM position. This is the generated-code version of "read the accessibility tree, don't guess coordinates," which has been a principle since `flow-runner`; it matters more here because code that breaks on every unrelated markup tweak is exactly the kind of test a team stops trusting and starts ignoring.

**Never emit a fixed-time wait.** Use Playwright's auto-waiting assertions (`expect(locator).toBeVisible()`, `toHaveText()`, etc.), which retry until the condition holds or a timeout elapses — never `page.waitForTimeout(2000)`. Same "wait for state, not time" reasoning as everywhere else in this toolkit, except a flaky fixed wait baked into committed code causes real, recurring CI pain rather than a one-off flake.

**Reuse auth state through a shared fixture — don't repeat a login flow in every generated file.** If multiple generated tests need to start authenticated, generate (or reuse) one setup that saves `storageState` once and have each test load it. Mirrors `flow-runner`'s reasoning about not re-logging-in per scenario, now as actual shared code instead of a repeated instruction.

**Handle test data deliberately.** A flow that creates persistent state (a signup, an order) needs dynamically generated data — timestamped or UUID-based — so the test doesn't collide with itself on the next CI run. Hardcoding `"test@example.com"` into a generated signup test is a failure waiting for its second run.

**Run it before calling it done.** Generating code and assuming it's correct because the original conversational run passed skips over the exact place errors creep in — translating a step plan into code is itself a real translation, and a headless CI run can behave differently from an interactive one. Execute the generated file (`npx playwright test <file>`) immediately, and fix it if it doesn't pass. Handing over generated test code that has never itself been run as code is handing over an unverified claim, which is precisely what this whole skill exists to avoid doing to the scenario in the first place.

**A green run doesn't mean skip human review.** Flag every generated file for a human to actually read before merging — a test passing once is a good sign, not a guarantee, the same as any other generated code.

## Workflow

1. **Confirm the source scenario is actually verified** — via `flow-runner`, `network-assertion`, or `cross-browser-matrix` as appropriate. If it isn't, verify it first.
2. **Check for an existing Playwright Test project** (`playwright.config.ts`, a `tests/` directory). If none exists, set up a minimal one rather than assuming structure that isn't there.
3. **Check for existing shared fixtures** (an auth setup, common helpers) to reuse rather than duplicate.
4. **Translate the verified step plan into code:** role-based locators, a real assertion per step, auto-waiting throughout, dynamic data for anything that creates state, and `page.route()` mocks if the source was a `network-assertion` negative case.
5. **Run the generated file immediately.** Debug and fix if it doesn't pass — don't hand over untested generated code.
6. **Present the file**, flagged for human review, and note that `test-plan`'s coverage ledger should be updated to reflect it.

## Translation example

Source (a verified `flow-runner` step): *"Fill login form with valid credentials, submit → expect redirect away from /login and an account menu visible."*

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('valid credentials redirect to authenticated state', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
    await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
    await page.getByRole('button', { name: 'Log in' }).click();

    // Assert the actual expected outcome, not just that the click happened
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible();
  });
});
```

Note what's absent: no `waitForTimeout`, no CSS selector, credentials from environment rather than hardcoded, and an assertion on the specific authenticated-only element — not just "not on /login anymore," which a generic redirect could satisfy without actually being logged in.

## Output location

`tests/<flow-slug>.spec.ts`, named from the source scenario's `id`/`scenario` field if it came from a `scenario-mapper`-derived flow, so the generated file is traceable back to the scenario it codifies.

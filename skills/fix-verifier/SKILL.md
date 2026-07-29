---
name: fix-verifier
description: Re-verify previously-found defects against the current build using a real browser — take one or more defect IDs (or "all open defects"), locate each one's recorded minimal repro, re-run it faithfully at the original rigor, and deliver a per-defect verdict of FIXED, STILL BROKEN, REGRESSED, or BLOCKED, updating the bug bundle and defect ledger in place. Use whenever the user wants to know if a fix landed, whether known bugs are still present on the latest build, or to refresh the defect ledger after a deploy — trigger on phrases like "is D4 fixed," "re-check the open bugs," "did the fix for the invite bug land," "verify the fixes," or "re-run the defect checks on the new build," even without the word Playwright. Distinct from bug-triage, which investigates something newly suspected broken and produces the repro this skill consumes — if a defect has no recorded minimal repro yet, triage comes first.
---

# Playwright Fix Verifier

Takes defect IDs, digs up each one's minimal repro, re-runs it against the current build, and updates the ledger with an evidence-backed verdict. Closes the loop that otherwise dead-ends in "the fix is deployed, probably."

## Relationship to the other skills

- `bug-triage` produces the input this skill needs: a defect record with minimal repro steps and original evidence. If a defect ID has no repro on file, route through triage first — improvising a repro from a one-line symptom description verifies your guess, not the defect.
- Repros that depend on forced API failures reuse `network-assertion` techniques (mocking a 500, a distinctive GraphQL error) — a backend that has been fixed won't fail on demand, so the mock *is* the repro.
- `report-generator` consumes the updated ledger; verdicts from this skill should land where that skill will find them.
- After a verdict, optionally transition the corresponding Jira ticket via `jira-connector` (dry-run first, as ever). A REGRESSED verdict is a new ticket, not a comment on the closed one — hand it to `bug-creator`, which links it back to the original.

## Core principles (and why)

**Re-run the recorded repro, not your memory of the symptom.** The bug bundle's "Minimal repro steps" section is the contract — same preconditions, same tenant class, same data shape, same forced-state setup. A verification that reproduces something *like* the original conditions produces a verdict about a different bug.

**Pin the build before anything else.** Read the app's version identifiers first and record them next to the verdict. Staging builds can change several times a day here; a verdict without a build number expires silently and can't be compared with the last one. If the build is *identical* to the one where the defect was confirmed broken, say so — re-verifying the same build mostly measures flakiness, and the user may want to wait for the deploy instead.

**Match or exceed the original rigor.** If the defect was intermittent or the previous verification ran the repro five times (forced and natural paths), a single clean pass now is not comparable evidence. Read what the last verification actually did and do at least that. One trial is only sufficient for defects that were deterministic in both directions.

**Four verdicts, not two.**
- **FIXED** — repro conditions fully established, failure absent, positive evidence captured.
- **STILL BROKEN** — failure reproduced; note whether the signature is identical or has shifted.
- **REGRESSED** — a defect previously verified fixed is failing again. This is the loudest verdict; say it first in the summary, because it means a deploy went backwards and the team's mental model is stale.
- **BLOCKED** — the repro's preconditions can't be established anymore (data gone, feature moved, account state unavailable). Never let this collapse into FIXED: absence of the failure is meaningless if the conditions that caused it were never reached.

**"Doesn't reproduce" has two more explanations besides "fixed."** The original finding may have been an automation false positive (it has happened here — a defect was withdrawn after manual verification showed the automation misread a two-step confirmation), or environment-dependent. Before declaring FIXED, skim the original evidence: does it actually show what the summary claims? If the original evidence is ambiguous, say "not reproducible — original evidence re-examined, possible false positive" and show why, rather than crediting a fix that may never have shipped.

**Capture positive evidence for FIXED, not just absence of failure.** A screenshot of the working state, the clean console, the 200 where the 400 was — proof the check actually looked. "No error observed" without evidence is indistinguishable from "didn't look."

**Verification can mutate — the safety rules travel with the repro.** Some repros create records, send invites, corrupt tokens. Everything the mutating skills observe applies here: safe tenant only, self-containment (undo what you create), two-step confirmations completed, no MFA enablement, and forced session damage only on the shared account if the recorded repro did exactly that and recovery is part of the check.

**Update the ledger where future readers will look — and prune in both directions.** Append the verification to the bug bundle's report (date, build, trials, verdict, evidence files) and update whatever ledger tracks open/fixed status. If the fix removes an entry from the target profile's known-noise list, remove it — a stale noise entry silently suppresses the regression if it returns. Conversely, when a verdict is REGRESSED, restore the tripwire note so the next run recognizes it.

## Workflow

1. **Resolve the defect set.** Explicit IDs, or sweep: parse the ledger (consolidated/final reports, `bugs/` directory) for defects and their last-known status. Confirm the set in one sentence before starting if it's a sweep.
2. **For each defect, load the record**: `bugs/<ID>-<slug>/report.md` (primary), plus any verification notes in the target profile and run reports. Extract: minimal repro, original build, expected/actual, previous verification rigor, whether the repro mutates or mocks.
3. **Pin the current build** and note the delta from the record's build.
4. **Re-establish the preconditions** exactly (login, tenant, data, forced state, network mocks). If impossible → BLOCKED, with what's missing.
5. **Run the repro** at the recorded rigor (N trials, forced + natural paths as recorded). Capture evidence either way into the bug bundle directory.
6. **Verdict and ledger update**: append a dated verification block to the bundle report; update ledger status; prune/restore target-profile notes as the verdict requires; undo any test data.
7. **Write the run summary** to `runs/fix-verify-<date>/report.md` and give the chat summary: regressions first, then fixed, then still-broken/blocked, each with build and evidence path.

## Report structure

```markdown
# Fix Verification — <date> — build <versions>
## Verdicts
| ID | Defect (one line) | Last status (build) | Verdict (build) | Trials | Evidence |
## Regressions (if any — detail each: what changed, tripwire restored where)
## Details per defect (repro run, deviations from recorded repro if any were forced, notes)
## Ledger updates made (files touched)
```

## Judgment calls that recur

- **The repro depends on a since-fixed backend**: mock the failure (that's what the original verification did for error-surfacing defects). The check is then about the app's handling, and the verdict should say so.
- **Partial fixes**: the 400 is gone but the feature still doesn't visibly work end to end. Verdict FIXED-with-caveat, caveat stated in the ledger — silent caveats get lost.
- **Repro steps that no longer map to the UI** (button renamed, flow moved): adapt the smallest step necessary, record the adaptation in the details section, and flag if the change is large enough that this is effectively a new repro.

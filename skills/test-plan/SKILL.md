---
name: test-plan
description: Write or update a strategic test plan — scope, risk-based priorities, cadence for each of the other skills in this toolkit, release exit criteria, environment/data conventions, and a coverage ledger of what's automated versus manual-only. Use whenever the user wants a test strategy, testing roadmap, release readiness criteria, or a document describing what testing approach the team should follow — "what should our testing strategy be," "write a test plan," "when should we run each kind of check," "what are our release criteria," "set up a testing roadmap." This sits above the execution skills — scenario-mapper discovers what's testable, this decides when and how thoroughly each of the other skills should run, and what has to be true before a release ships. Does not drive a browser itself unless it needs to run scenario-mapper first to ground itself in the site's actual structure.
---

# Playwright Test Plan

The strategy document that sits above the rest of the toolkit: not what to test (that's `scenario-mapper`) or how a single run went (that's `report-generator`), but when each kind of check should run, what has to be true before something ships, and how test data/environments are handled consistently instead of improvised per-run.

## Core principles (and why)

**Ground it in the actual site — don't write a generic template.** A test plan that could apply to any website ("browser compatibility matters," "test your forms") isn't useful to anyone. Base scope and risk-based priorities on what `scenario-mapper` actually found about *this* site, and reuse its P0/P1/P2 scheme directly rather than inventing a new one — a second priority scale just adds a translation step nobody asked for.

**If nothing's been discovered yet, discover first.** Risk-based prioritization is only as good as what's actually known about the site's structure. If no `scenario-mapper` output exists, either run it before writing the plan, or write the plan but mark it explicitly as provisional until that's done — don't present confident-sounding priorities that are actually guesswork.

**Cadence should match cost, not habit.** The other skills in this toolkit already have real cost differences worth reusing here: a full cross-browser grid is expensive, a viewport-only check is cheap; comprehensive scenario discovery is a bigger lift than sanity; codifying a flow into a permanent test is worth doing once it's stable, not every run. Don't default everything to "run before every deploy" because that sounds thorough — that's the same "comprehensive isn't infinite" instinct from `scenario-mapper`, applied to scheduling instead of scenario count.

**Exit criteria have to be specific enough to actually gate a decision.** "The site should work well" isn't a criterion. "No failing P0 flow-runner scenario, no critical/serious accessibility finding, no unresolved critical bug-triage finding" is — someone can check it and get a yes/no answer. If a criterion can't be checked against something concrete, rewrite it until it can.

**This is a living document — revise it, don't regenerate it from scratch.** If a test plan already exists, update it in place: note what changed (a new risk area discovered, a cadence that turned out wrong, tightened or loosened criteria) in a changelog, rather than producing a disconnected fresh copy that loses the history of why things are set up the way they are.

**The coverage ledger should be honest, not flattering.** Which scenarios have a permanent `e2e-codegen` test versus which are still conversational/manual-only is real information the plan should track plainly. "Manual-only" isn't a failure to hide — it's just where automation hasn't been invested yet, and hiding it defeats the point of tracking coverage at all.

## Workflow

1. **Gather what exists:** `scenario-mapper` CSV(s), any `e2e-codegen` test files, a `visual-snapshot` gallery, prior `flow-runner`/`accessibility-audit`/`network-assertion`/`cross-browser-matrix` reports, and a prior version of this plan if one exists.
2. **If there's no scenario-mapper output at all**, run it (comprehensive mode, since the plan needs the fuller picture) before writing risk-based priorities, or clearly mark the plan provisional if you're proceeding without it.
3. **Define scope** — what's in and what's out (third-party embeds, marketing pages vs. core app, anything explicitly out of the team's control). Ask if genuinely unclear rather than guessing.
4. **Set risk-based priorities**, reusing `scenario-mapper`'s P0/P1/P2 scheme — list the P0 areas explicitly, since they drive most of what follows.
5. **Set cadence per skill**, matching frequency to each skill's actual cost (see the table below for a reasonable starting point).
6. **Write exit criteria** — specific and checkable, per the principle above.
7. **Write environment and data conventions** — staging vs. production rules, test accounts, sandbox payment modes, disposable-email conventions for signup flows — the policy version of what individual skills currently improvise per-run via their `notes` columns.
8. **Build or update the coverage ledger** — which scenarios have a permanent automated test versus manual-only, and when each was last verified.
9. **If updating an existing plan**, diff against it and write the changelog entry.
10. **Write using the template below.**

## Template

```markdown
# Test Plan: [site/project] — [version/date]

## Scope
**In scope:** ...
**Out of scope:** ...

## Risk-based priorities
[The P0 areas, explicitly — these drive cadence and exit criteria below. P1/P2 areas can be summarized more briefly.]

## Cadence
| Check | Frequency | Trigger |
|---|---|---|
| scenario-mapper — sanity | e.g. whenever nav structure changes | |
| scenario-mapper — comprehensive | e.g. quarterly / before major releases | |
| flow-runner — P0 scenarios | e.g. before every deploy | |
| flow-runner — full scenario set | e.g. nightly | |
| accessibility-audit | e.g. monthly / before major UI changes | |
| network-assertion | e.g. alongside relevant flow-runner scenarios | |
| cross-browser-matrix — viewport-only | e.g. every deploy (cheap) | |
| cross-browser-matrix — full grid | e.g. before major releases only (expensive) | |
| visual-snapshot | e.g. before/after significant UI work | |
| e2e-codegen | once a flow-runner scenario is verified stable, not every run | |
| bug-triage | reactive — on report, not scheduled | |
| report-generator | e.g. weekly digest / pre-release summary | |

## Exit criteria (what gates a release)
- [Specific, checkable statements — e.g. "no failing P0 flow-runner scenario"]

## Environment & data strategy
**Environments:** [staging vs. production rules — what's safe to run where]
**Test accounts / sandbox modes:** ...
**Data conventions:** [e.g. disposable email pattern for signup tests, timestamped test data to avoid collisions]

## Coverage ledger
| Scenario | Priority | Automated (e2e-codegen)? | Last verified |
|---|---|---|---|
| ... | P0 | ✅ tests/checkout.spec.ts | date |
| ... | P1 | ❌ manual only | date |

## Changelog
[If updating an existing plan: what changed since the last version, and why]
```

Leave any section thin or explicitly marked "not yet established" rather than filling it with plausible-sounding filler — a plan that honestly says "environment strategy not yet defined" is more useful than one that invents a policy nobody agreed to.

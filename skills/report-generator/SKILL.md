---
name: report-generator
description: Synthesize outputs from the other testing skills in this toolkit (scenario CSVs, run reports, bug-triage writeups, audit findings, cross-browser matrices) — potentially from several sessions across a testing cycle — into a single prioritized, human-readable report. Use whenever the user wants a summary, status update, or write-up of testing results — "summarize what we found," "give me a report I can send," "what's our testing status," "put this in a doc for the team" — especially when more than one prior run or skill's output needs pulling together. Also covers register-shaped questions about accumulated results — "which defects are still open," "what have we found across these cycles." Does not drive a browser or run tests itself — it only reads and synthesizes artifacts the other skills already produced; if nothing has been tested yet, run one of the other skills first rather than fabricating a report.
---

# Playwright Report Generator

Every other skill in this toolkit already reports its own results — flow-runner's step table, bug-triage's per-bug writeup, the CSVs from scenario-mapper and accessibility-audit. This skill isn't another version of that. It's the layer above: pulling together whatever's accumulated across a testing cycle — possibly several runs, several skills, spread over days — into one document a human can read once and understand where things stand, without re-reading every individual artifact.

## Before you start

No Playwright or MCP tool access needed for this one — it's a reading and writing task, not a browsing task. What it does need is access to the artifact files the other skills produced: CSVs, markdown reports, and the evidence directories they reference. If you don't know where those live, ask rather than guessing at a path.

## Core principles (and why)

**Synthesize, don't re-run, and never fabricate.** If accessibility wasn't audited this cycle, the report says so — it does not estimate what an audit probably would have found. Missing coverage is a gap to report, not a gap to paper over. If asked to report on something nothing has actually tested, say that plainly and point to which skill would need to run first.

**Lead with what matters, not with everything given equal weight.** A report that lists forty passing checks and one critical failure with the same visual weight buries the one thing the reader actually needs to act on. Executive summary and top issues come first; full detail is available below but isn't what a skimming reader needs to see first.

**State what wasn't covered, not just what was.** Silence about a gap reads as "checked and fine" to someone who wasn't in the room. If cross-browser testing only covered Chromium this cycle, or a comprehensive scenario pass was never run and only sanity was, the Scope section says so explicitly.

**Preserve each source skill's own severity — don't re-score.** flow-runner's pass/fail, bug-triage's severity and confidence, axe's impact level, scenario-mapper's priority: carry these through as given rather than inventing a unified scale that quietly loses the original reasoning. Some normalization for an at-a-glance table is fine (mapping different scales to a simple status icon), but the source severity should still be visible once you're in the details.

**Reconcile cross-references instead of double-counting.** `bug-triage` reports explicitly point back to the flow-runner failure they investigated; `network-assertion` checks are often already folded into whichever flow-runner report they were part of. If you present both the original and the investigation (or the folded-in check) as separate, unrelated findings, the same issue silently inflates the count. Merge them.

**Evidence stays where it lives — index it, don't inline it.** Traces and screenshots are what make a finding trustworthy on closer inspection, but pasting them into a summary defeats the point of summarizing. Reference the path; let the reader drill down if they want to.

**One defect, one row — with a stable ID.** The same underlying defect recurs across runs and must be deduplicated into a single register entry carrying an ID (`D1`, `D2`, …) that survives from report to report. Two symptoms with one root cause are one defect; one symptom with two root causes are two. Record which runs observed each. Without stable IDs, a defect that gets re-observed, fixed, and regressed becomes three unrelated-looking findings.

**Status is evidence-based — never infer `Fixed` from silence.** A defect is `Fixed` only when a later run *verified* the fix, `Open` when a later run still reproduces it, and `Unverified` when nothing has re-tested it since. A defect that simply stopped being mentioned is not fixed, and quietly promoting it is how regressions escape. Where a status changes, say which run changed it.

**Separate blocked from failed.** A scenario that never ran because a prerequisite broke is not a failure — counting it as one inflates the failure rate and, worse, hides that coverage was never obtained at all. Report pass / fail / blocked as three numbers and state what the blocker was. The distinction routinely changes the headline: a run reading "2 failed, 9 blocked" is a very different message from "11 failed."

**Distinguish app defects from suite defects — and harness defects from both.** A run can fail because the product is broken, because the scenario's expectation was wrong, or because the automation could not drive the app. All three look identical in a raw result. Say which. A suite that needed no changes after a failed run is itself a finding worth stating; so is a false positive that was withdrawn — record it as withdrawn rather than deleting it, so the count and the reasoning stay auditable.

**Only claim a pattern you can point at two or more defects for.** Connections across findings are usually the most useful thing a cross-run report adds — several defects sharing a failure mode, a subsystem, or a deploy. But a "pattern" resting on one defect is a hunch. If a pattern loses a supporting defect (withdrawn, or reclassified), say so explicitly rather than letting the claim stand on weaker evidence than when it was written.

**Environment and build belong in the report.** Results are meaningless without the build they ran against. When runs span builds, group results by build so trends are visible, and flag any comparison that is cross-build rather than like-for-like.

**No credentials, ever.** Reports name credential *sources* (`.env` keys), never values. This applies with double force to any version that gets published or shared onward.

## Workflow

1. **Gather what's available.** Check for scenario-mapper CSVs, flow-runner reports, bug-triage writeups, accessibility findings, network-assertion checks, and cross-browser matrices. If the location isn't obvious, ask rather than assuming — and confirm whether the user wants everything found, or a specific run/date range.
2. **Figure out the audience**, if not already clear: an internal technical read (developers, QA) wants full detail and evidence paths readily available; a stakeholder-facing summary wants the executive framing without jargon and with business impact in plain terms. Default to the technical read if genuinely unclear — that's the more common consumer of this toolkit's output — but say which assumption you made.
3. **Reconcile.** Cross-reference bug-triage writeups back to the flow-runner failures they investigated, and network-assertion checks that were already folded into a flow-runner report, so nothing is counted twice.
4. **If comparing against a prior report** the user points you to, call out what's new, what's resolved, and any regressions — turns a snapshot into a trend, which matters a lot more for a recurring status update than a one-off.
5. **Draft using the template below.**
6. **If the user wants a polished, formal document** (something to send externally, attach to an email, present to non-technical stakeholders) rather than an internal markdown file, hand off to document-creation for that — don't reinvent formatting here. A markdown report is the default; a formal doc is an explicit upgrade when asked for.

## Report template

```markdown
# Test Report: [site/feature] — [date or cycle range]

## Summary
[2-4 sentences: overall posture, the one or two things that matter most, a headline number if it's useful — not a restatement of every section below]

## Scope
**Tested:** [pages/flows/browsers/viewports covered, and by which skills]
**Not tested / known gaps:** [explicit — don't let silence imply coverage]
**Sources:** [which skills contributed, and when they ran]

## Results at a glance
| Category | Status | Critical/P0 issues | Notes |
|---|---|---|---|
| Functional (flow runs) | ✅ 12/14 passed | 2 | |
| Bugs investigated | ⚠️ | 1 confirmed, 1 could not reproduce | |
| Accessibility | ⚠️ | 1 critical | |
| Network/API | ✅ | 0 | |
| Cross-browser/responsive | ✅ | 0 | Chromium + Firefox only, WebKit not covered |

## Defect register
| ID | Defect | Severity | Status | Runs observed | Evidence |
|---|---|---|---|---|---|
| D4 | ... | P0 | Fixed (verified <run>) | ... | path |
| D8 | ... | P2 | Open | ... | path |
| ~~D5~~ | ... | — | Withdrawn (false positive) | ... | path |

[Stable IDs, most severe and still-open first. Include withdrawn entries struck through rather than deleted, so the count stays auditable. Omit this section only when a single run is being reported and no register exists yet.]

## Top issues
[Ranked, critical/P0 first, one line each with a pointer to the detail section — this is what a reader who only has two minutes should see]

## Details by category
[One subsection per category actually covered — omit categories nothing tested rather than writing "N/A" for each]

## Appendix: evidence index
[Paths to the raw CSVs, run reports, and trace/screenshot directories — not inlined, just indexed for anyone who wants to drill down]
```

Omit sections with nothing to report rather than padding the template out — a report that's honestly three sections long because that's what was actually tested is better than one stretched to look more thorough than the cycle actually was.

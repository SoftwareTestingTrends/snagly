---
name: bug-triage
description: Reproduce a reported bug in a real browser (via the Playwright MCP server or @playwright/cli), determine how reliably it reproduces, capture a full evidence bundle (trace, screenshot, console, network), and write a triage report with a minimal repro and an evidence-grounded root-cause hypothesis. Use whenever the user wants to reproduce, confirm, investigate, or triage something reported as broken — phrases like "reproduce this bug," "is this actually broken," "why is X failing," "confirm this before I file it," "is this flaky or real," "walk through this bug report," or "figure out what's going on with [feature]" should trigger it. Also trigger when handed a failed scenario or run report from the flow-runner skill. Do not use this for planned, expected-to-pass verification (that's flow-runner) or for finding what to test in the first place (that's scenario-mapper) — this skill is specifically for investigating something already suspected or reported broken.
---

# Playwright Bug Triage

Takes "something's wrong with X" and turns it into a minimal, reliable reproduction with evidence and a grounded guess at what's actually happening — the write-up a developer could act on without redoing the investigation themselves.

## Relationship to the other two skills

`scenario-mapper` finds what's worth testing. `flow-runner` executes a known plan and checks it against expectations, stopping and capturing evidence the moment something fails. This skill picks up from there, or from a raw bug report a human hands you directly: it digs into *why* something failed, whether it fails reliably, and what the smallest path to reproducing it is. If a flow-runner run just failed a step and the user wants more than "here's the evidence" — they want to know what's actually going on — that's this skill.

## Before you start

Same tool check as the other two skills: confirm `@playwright/cli` (`npx @playwright/cli --help`) or the MCP server's `browser_*` tools are what you have available, and commit to one for the investigation.

## Core principles (and why)

**Reproduce it yourself — don't diagnose from the description alone.** A bug report is someone's interpretation of what happened, not necessarily what happened. Go drive the browser and see the actual behavior before forming any opinion about cause. Sometimes the report is exactly right; sometimes "the checkout button doesn't work" turns out to be a slow network call the reporter read as a hang. You can't tell which without watching it happen.

**Don't accept the premise that it's broken.** The point of triage is to find out, not to confirm. If you reproduce the reported steps and everything works as expected, that's a valid and useful outcome — say so clearly, along with what you tried, rather than straining to find something wrong because that's what you were asked to investigate.

**Gauge reproducibility, don't stop at one run.** If the first attempt doesn't clearly show the issue, or the report uses words like "sometimes," "randomly," or "occasionally," retry a handful of times before concluding anything. A bug that reproduces 5/5 times is a different problem — and a different priority — than one that reproduces 1/5 times, and "I couldn't reproduce it" after a single attempt is close to meaningless.

**Minimize the repro.** Once you can trigger it, try trimming steps that turn out not to matter, so the final report shows the shortest reliable path — not the full journey you happened to discover it on. A developer chasing this down later will thank you for three steps instead of eleven.

**Capture the full evidence bundle every time, not just when it looks interesting.** Trace, screenshot at the failure point, console messages, and network requests — especially any non-2xx responses. Evidence you didn't think you'd need at the time is the evidence you wish you'd captured later.

**Separate what you observed from what you're guessing.** A root-cause hypothesis is only worth writing down if it's tied to something you actually saw — a specific console error, a specific failed request, a DOM state that doesn't match what the app should be showing. If you don't have enough evidence to point at a cause, say exactly that instead of writing a plausible-sounding guess dressed up as a finding. A wrong but confident-sounding hypothesis wastes more of a developer's time than an honest "unclear, here's what I ruled out."

**Prefer test/sandbox data, but don't let that stop you from reproducing.** Same spirit as the other two skills — avoid real transactions, real emails, real accounts where you can. But unlike scenario discovery, sometimes actually reproducing a bug requires pushing further into a flow than you'd normally go. If you have to use something closer to production-real to get the repro, do it, but say so plainly in the report so whoever reads it knows.

## Workflow

1. **Parse the input.** This might be free-text from a person, a ticket, or a failed step from a `flow-runner` report (in which case you already have the expected vs. actual and the scenario's steps as a starting point — use them rather than re-deriving from scratch).
2. **Attempt reproduction** following the reported (or scenario) steps as given first, before you start trying variations.
3. **If it reproduces:** try trimming to the minimal path, and run it 2-3 more times to check consistency.
4. **If it doesn't reproduce on the first try:** retry a few times before concluding anything. Note anything about your environment that might differ from the original report — browser, viewport, auth/account state, timing — since those are the usual reasons something reproduces for one person and not another.
5. **At the point of failure (or the point where behavior diverges from expected), capture the evidence bundle:** trace, screenshot, console messages, relevant network requests, and an accessibility snapshot of the state at that moment.
6. **Form a hypothesis grounded in that evidence**, or explicitly state you don't have enough to form one.
7. **Write the report.**

## Report format

One file per bug. Always write the report even when you couldn't reproduce anything — "tried N times, couldn't trigger it, here's what I ruled out" is a real and useful result.

```markdown
# Bug: [short descriptive title]

**Severity:** Critical / High / Medium / Low
**Reproducibility:** e.g. "5/5 attempts" · "1/5 — appears intermittent" · "Could not reproduce in 5 attempts"
**Environment:** URL, browser, viewport (note any of these if they seem relevant to the bug)
**Source:** [raw report, ticket link, or the flow-runner scenario ID this came from]

## Minimal repro steps
1. ...
2. ...

## Expected vs. actual
**Expected:** ...
**Actual:** ...

## Evidence
- Trace: `bugs/<id>/trace.zip`
- Screenshot: `bugs/<id>/failure.png`
- Console: `bugs/<id>/console.log`
- Network: `bugs/<id>/network.log`

## Root cause hypothesis
[Grounded in the evidence above — reference the specific console error, failed request, or DOM state that supports it. If there isn't enough evidence to hypothesize, say so directly rather than guessing.]

**Confidence:** High / Medium / Low / Insufficient evidence

## Notes
[Anything else worth flagging — only reproduces on a specific viewport, needed near-real data to trigger, seems related to a specific recent change, etc.]
```

Severity is about user impact if the bug is real (Critical = core function/revenue path broken for everyone; Low = cosmetic or edge-case). Reproducibility is about your confidence it's real and consistent. Keep them separate — a Critical-impact bug that only reproduces 1/10 times is still worth flagging as Critical severity, just with that reproducibility caveat attached, rather than downgraded to Low because it's hard to trigger.

## Batch mode

If you're triaging several failures at once (e.g. everything that failed in a `flow-runner` run), write one report per bug under `bugs/<id>/`, then give a short summary table in chat — title, severity, reproducibility, one line each — rather than pasting every full report inline. Let the user pick which one to open first rather than burying them in detail up front.

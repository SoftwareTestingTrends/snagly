---
name: qa-onboarding
description: Write an onboarding document for a new QA teammate joining this team's testing practice — the site's testing landscape (scope, P0 areas, cadence, environment/test data conventions, pulled from test-plan), a curated tour of which skill in this toolkit to reach for and when, known trouble spots pulled from recent bug-triage/report-generator output, and a suggested first-week path. Use whenever the user wants to onboard a new QA hire, write a "getting started" doc for the testing practice, or introduce someone to how this team tests this site. Distinct from user-guide, which documents the product for end users in plain language — this documents the testing practice for a technical teammate, and uses this team's testing vocabulary freely rather than avoiding it. Doesn't drive a browser — this is a synthesis skill, same character as test-plan and report-generator.
---

# Playwright QA Onboarding

Gets a new QA teammate from "never seen this codebase" to "productive" faster than handing them the full README and every skill's SKILL.md cold — grounded in what `test-plan` already defines, not a parallel narrative invented from scratch.

## Relationship to the other skills

**Ground it in `test-plan` — don't re-derive scope, priorities, or cadence independently.** If a test plan exists, this skill's job is making that information approachable and sequenced for a new person, not inventing a second version of it. If no test plan exists yet, say so plainly and suggest creating one first — onboarding someone into an undefined strategy just teaches them that the absence of one is normal.

**Complements the README, doesn't replace it.** The README (or equivalent skill catalog) is the exhaustive technical reference — every skill, every trigger phrase. This is the narrative, sequenced version for a specific person joining a specific team's specific practice on a specific site. Point back to the README for anything exhaustive rather than duplicating it here.

**Pull known trouble spots from `bug-triage` and `report-generator` history, not just the happy path.** If recent output shows a recurring flaky area or an unresolved finding, a new teammate benefits enormously from hearing that up front rather than rediscovering it themselves in week one.

**Distinct from `user-guide` — different audience, different vocabulary.** That skill documents the product for an end user and deliberately avoids testing jargon. This one is for a teammate who needs to *learn* this team's testing vocabulary and practice — use it freely (P0, coverage, flaky, cadence) rather than softening it.

## Core principles (and why)

**A practical first-week path beats a complete-but-unordered catalog.** A new teammate doesn't need every skill's full capability on day one. A suggested sequence — read the test plan's P0 areas, try `scenario-mapper` on something unfamiliar, run `flow-runner` against an existing test case — gets someone productive faster than a reference dump they have to self-sequence.

**Flag known trouble spots explicitly.** "Heads up, the checkout payment step has been flaky, here's the last triage" saves a new person from rediscovering a known issue the hard way. Silence about a known problem reads as "this area is fine," same honesty principle as everywhere else in this toolkit.

**Curate the toolkit tour around what this site's cadence actually uses**, not a flat list of all twenty-plus skills in equal weight. If `test-plan`'s cadence table shows accessibility audits run monthly and cross-browser matrices only before major releases, the onboarding doc should reflect that emphasis — what a new person will actually reach for most, with a pointer to the full README for the rest.

## Workflow

1. **Check for an existing `test-plan`.** Use its scope, P0 areas, cadence, and environment/data conventions as the backbone. If none exists, note that plainly.
2. **Check recent `bug-triage` writeups and `report-generator` summaries** for anything reading as a recurring or unresolved issue worth flagging up front.
3. **Write a curated toolkit tour** — which skill for which job, weighted toward what this site's actual cadence uses most, with a pointer to the full README for anything not covered here.
4. **Write a suggested first-week path.**
5. **Compile** using the template below.

## Template

```markdown
# QA Onboarding: [site/project]

## Welcome
[What this covers, who it's for]

## The site, from a testing perspective
[Pulled from test-plan: scope, P0 areas, known risk areas]

## Your toolkit
[Curated tour — what you'll reach for most given this site's cadence, with a pointer to the
full skill reference for everything else]

## Known trouble spots
[From recent bug-triage/report-generator output — recurring or unresolved issues worth knowing
about before you find them yourself]

## Environment & test data
[From test-plan: staging URLs, test accounts, sandbox modes]

## Your first week
1. [Suggested starting sequence — concrete, ordered]
2. ...

## Where to find more
[Pointer to the full README, to test-plan for complete strategy detail, to report-generator's
past summaries]
```

Leave any section thin or explicitly marked "not yet established" rather than inventing plausible-sounding content — same discipline as `test-plan` itself.

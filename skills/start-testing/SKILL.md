---
name: start-testing
description: Use whenever someone wants to test something but hasn't said (or doesn't know) which kind of check they need — "what can you test here", "what can you test on this site", "what can you do here", "what should I check", "can you test this site", "is the site okay", "help me run a test", "where do I start", "run the usual checks", "check this before we ship", "I want to test something". Also use when a request names a target but not a method ("check the signup flow", "have a look at staging"), or when someone new to the repo asks what testing is available here. Do not use when the request already clearly names a kind of check — an accessibility audit, a visual comparison, a bug reproduction — those skills should trigger directly, and routing through this one only adds a detour.
---

# Start Testing

Someone wants to check something. They may not know this repo has a whole toolkit
of testing skills, and they shouldn't have to. This skill's whole job is to get
from what they said to the right skill running, with as few questions as the
request actually requires — often zero.

Read the routing table below as the live list, and treat the skills actually
registered in this session as the authority — the toolkit grows, and a skill that
exists but isn't routed here is invisible to anyone arriving through the front
door. If you spot one missing, add its row.

It does not test anything itself. It picks and hands off.

## The one rule that matters

**Never ask what the request already told you.** A router that always runs its
menu is more annoying than no router at all. "Check if the invite form is fixed"
already names a target, a suspected defect, and an intent — that goes straight to
`bug-triage` against D8 and starts. Interrogating that person through
two menus first is worse service, not more thorough service.

Ask only when a genuinely different skill would run depending on the answer.

## Speak the user's language, not the toolkit's

The skill names, the CSV column names, and the target-profile filenames are
internal vocabulary. None of them belong in a question. Say what you're about to
do in plain terms and let the reader confirm or redirect.

| Don't ask | Ask |
|---|---|
| "Sanity or comprehensive mode?" | "A quick pass over everything, or a deep look at one area?" |
| "Which target profile?" | "Which site — staging, or somewhere else?" |
| "Shall I invoke crud-tester?" | "This one creates and deletes real records — I'll keep it to the dedicated test tenant. Go ahead?" |

Once you've picked, say which check you're running and why in one sentence, then
start. Don't present the routing table back to them.

## Routing

Match on what the person wants to learn, not on the words they used.

| They want to know | Skill |
|---|---|
| What's even worth testing on this site | `scenario-mapper` |
| Whether a specific journey works end to end | `flow-runner` |
| Whether creating, editing, and deleting actually persist | `crud-tester` |
| Whether something reported broken is really broken, and why | `bug-triage` |
| Whether previously-found defects are actually fixed on the current build | `fix-verifier` |
| Whether it works on Safari, Firefox, or a phone-sized screen | `cross-browser-matrix` |
| What every page currently looks like | `visual-snapshot` |
| Whether the look changed since last time | `visual-regression` |
| Whether it's usable with a keyboard or screen reader | `accessibility-audit` |
| Whether pages are slow, and by whose standard | `performance-audit` |
| Whether any links or images are broken across the site | `link-audit` |
| How the app behaves when the API fails, stalls, or returns nothing | `network-assertion` |
| Whether forms cope gracefully with empty, overlong, or unusual input | `form-fuzzing` |
| Whether an email a flow promises actually arrives, reads right, and its links work | `email-verification` |
| Whether sessions and logins hold up at the edges — expiry mid-flow, logout across tabs, remember-me | `auth-session-audit` |
| Whether the built screen matches its Figma design | `figma-compare` |
| Whether translations, locale switching, and RTL layouts actually work | `i18n-audit` |
| Whether basic security hygiene holds — HTTPS, cookie flags, security headers, exposed files | `security-hygiene` |
| Whether titles, metadata, structured data, and sitemaps are present and valid | `seo-audit` |
| A written test case someone can review or sign off | `test-case-writer` |
| A permanent automated test in the suite | `e2e-codegen` |
| A plain-language how-to guide for end users of a feature | `user-guide` |
| Where testing stands overall, or what's still open | `report-generator` |
| What the team's testing strategy and release criteria should be | `test-plan` |
| An onboarding doc that brings a new QA teammate up to speed on how this team tests | `qa-onboarding` |

`playwright-cli` is not on this list on purpose — it's the browser-driving
mechanism the others use, not a check anyone asks for by name.

**When two fit, prefer the narrower one.** "Does the login page work on mobile"
is a cross-browser/viewport question, not a general flow question. "Is the site
okay" with no other signal is the scenario mapper or a sanity run, not the whole
toolkit in sequence.

**When the honest answer is "several, in order,"** say so and start the first one
rather than trying to run them all at once. A person asking to check a site
before a release wants a sequence, and hearing the plan up front is part of the
service.

## When you do need to ask

How you ask depends on how much signal the request carried. Getting this wrong
is the easiest way to make the router worse than nothing.

**No signal at all** — a bare invocation, "what can you do here", "I want to test
something". This is a *discovery* request, and a short-list answer fails it: a
picker caps at four options, so choosing four means silently hiding eleven. List
**every** routable check as plain text, grouped, one line each, phrased as
outcomes rather than skill names. Then ask what they want in open text. Never
narrow a discovery request down to your own guess at what matters — the whole
point is that they don't yet know what's on offer.

**Partial signal** — they've named an area, a symptom, or a goal, and two or
three genuinely different skills could serve it. Now a picker is right: offer
only the real candidates, say what each would actually do, and let the differences
between them be the thing the person decides on.

**Enough signal** — route and start. See the rule at the top.

The second question, when it's still open, is **which site** — read
`targets/*.yaml` and offer what's there by its friendly name, not its filename.
If exactly one profile exists, don't ask; name it in your handoff sentence so
they can correct you.

If **no profile exists at all**, don't block on it: most read-only checks just need
a URL. Take the URL, hand off, and let `scenario-mapper` write the profile as a
by-product of its run (it carries the template). If the request needs credentials or
mutation, that's when a profile becomes required — the shape is: `name`, `base_url`,
`credentials` (`source` plus env-var *names*, never values), a prose `login` block,
`tenants`, and optional `recovery` / `known_noise` / `app_notes`. On production, omit
`safe_to_mutate` entirely rather than naming it "none".

Never more than two questions. If a third feels necessary, the receiving skill
should ask it — it has the context to ask well. Don't front-load the whole
interview here.

**Surfacing what's outstanding is a bonus, not a substitute.** Knowing that the
sanity suite hasn't been re-run since the fixes landed is genuinely useful, and
worth saying. Say it *alongside* the full list, not instead of it.

## Before handing off, check the prerequisites

Some skills need something to already exist. Discovering that after a person has
committed to a run is a bad experience; catch it here and offer the missing step
instead of failing into it.

| Skill | Needs first | If missing |
|---|---|---|
| `visual-regression` | A baseline capture in `snapshots/` | Offer to run `visual-snapshot` and say plainly that this run establishes the baseline rather than comparing anything |
| `e2e-codegen` | A scenario already verified by a run | Offer `flow-runner` first — generating a test from an unverified scenario bakes in whatever's wrong |
| `report-generator` | Artifacts under `runs/`, `bugs/`, or `snapshots/` | If nothing has been tested, say so and route to an actual check rather than producing an empty report |
| `cross-browser-matrix` | An existing scenario and its expected outcomes | Offer to run it once in one browser first, then widen |
| `figma-compare` | A Figma design URL, and Figma MCP access with that file reachable | Ask for the Figma link — without a design to compare against there's nothing to check |
| `fix-verifier` | A defect record with minimal repro steps (a `bugs/<ID>-*/` bundle) | Offer `bug-triage` first — verifying an improvised repro checks your guess, not the defect |
| `user-guide` | The flow verified by `flow-runner` (or a test case marked Verified) | Offer to verify the flow first — never write end-user instructions for a flow nobody's confirmed works |
| `qa-onboarding` | A test plan and/or accumulated run artifacts to synthesize from | Say the doc will be thin without them and offer `test-plan` or a first mapping run instead |
| `email-verification` | A readable test inbox (connected mail tool + plus-alias, or a disposable inbox the target delivers to) | Say what's missing — never verify email delivery by assumption from the app's "sent" toast |
| Anything that mutates data | A target profile naming a safe tenant | Stop and ask — see below |

## Safety carries through the handoff

Two constraints in this repo are not the receiving skill's problem alone, because
the person clicking through a router may never have read that skill:

**Mutations are tenant-scoped.** `crud-tester` may only write to the
tenant named in the profile's `tenants.safe_to_mutate`. If the chosen
profile names no safe tenant, don't route there — say
what's missing and ask. Never let a routing decision be the reason something
mutated production-shaped data.

**Say when a run has real side effects.** Creating records, sending invitations,
archiving accounts — name it in one sentence before starting, even when the
person clearly asked for it. Someone who typed "test the member flow" may not
have pictured a real invitation email.

## Adding to the toolkit later

The routing table is keyed on what someone wants to learn, not on what drives the
check — so a future skill built on Figma, Jira, or Chrome DevTools gets a row here
the same way the browser ones do. Add the row when the skill lands; that's the
only maintenance this skill needs.

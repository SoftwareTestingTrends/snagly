---
name: scenario-mapper
description: Explore a live website with a real browser (via the Playwright MCP server or @playwright/cli) to discover what's worth testing, and output a CSV of candidate sanity-test scenarios. Use this whenever the user wants to explore, audit, or map out a site before testing it — phrases like "explore this site and figure out what to test," "give me a test plan," "what are the critical flows here," "identify sanity testing scenarios," "map out what could break," or "what should we cover before we ship" should all trigger it, even without the word "Playwright." This is a discovery/reconnaissance step, not execution — it does not verify or assert anything, it produces a prioritized list. Pairs with the flow-runner skill, which executes and verifies the scenarios this one discovers.
---

# Playwright Scenario Mapper

Explores a site the way a new QA hire would on day one: click around, see what's there, and come back with a short list of "here's what would actually catch a broken deploy" — not an exhaustive spec of every possible interaction.

## Relationship to flow-runner

This skill discovers *what* to test; it doesn't test it. Each row you output becomes the input to a `flow-runner` run later — the `scenario` and `quick_steps` columns are deliberately terse because the flow runner is where the detailed step-by-step plan with assertions gets written. Don't do the flow runner's job here by writing a full numbered step plan per scenario; that's wasted work if the scenario turns out to be low priority or the site's actual structure changes the approach.

## Before you start

Check what you have available, same as for any Playwright-driven skill: `@playwright/cli` (preferred on Claude Code — writes snapshots to disk instead of streaming them into context) or the MCP server's `browser_*` tools. See `flow-runner`'s reference file if you have it installed; the CLI/MCP correspondence is the same here.

You need a starting URL. If the user didn't give one, ask for it — this is the one thing that's genuinely blocking, unlike most ambiguity in this skill, which you should resolve by exploring rather than asking.

## Target profiles

Check for a target profile (`targets/*.yaml`) before exploring. It supplies
the base URL, credential env-var names, the login recipe including any tenant picker, and
`app_notes` from prior runs — all of which save you rediscovering the same setup by trial and error.
If none exists for this site, explore as normal, then **write one** as a by-product of the run:
what you learned about login, tenants, and gotchas is exactly what the next run needs and would
otherwise lose.

**Create `targets/` if it doesn't exist, then copy
[assets/target-profile-template.yaml](assets/target-profile-template.yaml) there as
`targets/<app>-<env>.yaml` and fill it in — don't improvise the schema.** Most users install
this toolkit as a plugin rather than cloning the repo, so a fresh working directory has no
`targets/` folder and no template of its own; the copy in this skill is the one that travels. Those fields are all any skill reads; extra invented keys
(site maps, flow lists, discovered scenarios) belong in the scenario CSV, not the profile, and
go stale there. Two rules the template states and that matter most: credentials are env var
*names*, never values, and on a production target you **omit `safe_to_mutate` entirely** rather
than setting it to "none" — its absence is what makes `crud-tester` stop and ask.

## Core principle: look, don't finalize

This is reconnaissance, not testing. You're allowed to click into a flow far enough to see its shape — add something to a cart to see what checkout looks like, start a signup form to see what fields it asks for — but never complete a real transaction, real account creation, or real submission during this phase. If a "submit" or "confirm" button would send real data, real money, or a real email, stop before clicking it and note in the scenario that this is where actual execution (in `flow-runner`, ideally against a test/staging environment) would need to take over.

Why this matters beyond politeness: discovery runs are exploratory and a little sloppy by nature — you're clicking around to see what's there, which is exactly the wrong mode to also be committing real-world side effects in.

## Workflow

1. **Load the homepage, snapshot it.** Note the primary navigation, obvious calls-to-action (sign up, buy, book, apply, search), and footer links (these often hide account/legal/support surfaces the main nav doesn't).

2. **Walk primary nav one level deep.** Visit each top-level nav destination and its immediate children. Don't crawl the whole site — a sanity scenario list should come from the structure a typical user actually encounters, not from finding every page that exists. If the site is large, prioritize breadth (cover every major section shallowly) over depth (don't fully map one section while ignoring others).

3. **Classify what you find** using the same flow-type taxonomy as flow-runner:
   - **Auth** — login, signup, password reset, any gate between anonymous and authenticated state.
   - **Multi-step commit** — checkout, booking, application, onboarding wizard, anything that accumulates state across steps and finalizes it.
   - **Search** — any query/filter/browse interface.
   - **Content/Navigation** — pages that just need to render correctly and link correctly, no submission involved.

4. **Filter for sanity, not completeness.** For each thing you found, ask: "if this broke, would it be obvious the site was broken, or would only someone testing that exact edge case notice?" Keep the former, drop or deprioritize the latter. A good sanity set is usually 8-20 scenarios for a small-to-medium site, not 100 — if you're listing more than that, you're probably including edge cases that belong in a deeper regression suite, not a sanity check. Concretely: "can a user log in" is sanity; "does the login form show the right error for a password with exactly 7 characters" is not.

5. **Assign priority:**
   - **P0** — if this is broken, the site is effectively unusable or losing revenue (core auth, primary purchase/signup path, homepage rendering).
   - **P1** — a major feature is broken but the site is still usable (search, secondary nav sections, account settings).
   - **P2** — worth having in the sanity set but lower stakes (a specific content page, a minor CTA).

6. **Write the CSV using Python's `csv` module**, not manual string concatenation — scenario descriptions will contain commas and quotes, and hand-joined CSV silently corrupts on those. A short inline script is enough:

   ```python
   import csv, os
   rows = [...]  # list of dicts matching the columns below
   os.makedirs('scenarios', exist_ok=True)   # scenario CSVs live in scenarios/, not the repo root
   with open('scenarios/sanity-scenarios.csv', 'w', newline='') as f:
       writer = csv.DictWriter(f, fieldnames=[
           'id', 'area', 'scenario', 'flow_type', 'priority',
           'quick_steps', 'expected_outcome', 'notes'
       ])
       writer.writeheader()
       writer.writerows(rows)
   ```

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `S001` |
| `area` | Where on the site, e.g. "Homepage," "Product page," "Account settings" |
| `scenario` | Short name, e.g. "Guest checkout with valid item" |
| `flow_type` | `Auth` / `Multi-step Commit` / `Search` / `Content-Navigation` |
| `priority` | `P0` / `P1` / `P2` |
| `quick_steps` | One or two sentences — enough for a human or the flow runner to know where to start, not a full numbered plan |
| `expected_outcome` | What "this works" looks like, in one sentence |
| `notes` | Anything a later test run needs to know: requires a test account, no sandbox payment mode found, this flow sends a real email so needs a disposable address, etc. |

## After writing the CSV

Give a short summary in chat, not a restatement of every row: total scenario count, the P0/P1/P2 breakdown, and anything you noticed that blocks safe automated testing later (no sandbox/test mode for payments, no way to create disposable test accounts, destructive actions with no dry-run option). That last part matters — it tells the user, before they hand this list to `flow-runner`, which scenarios can be run freely and which need a staging environment or manual review first.

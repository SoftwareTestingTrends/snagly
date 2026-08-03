---
name: accessibility-audit
description: Run an accessibility audit against a live site using a real browser (via Playwright MCP or @playwright/cli), combining automated axe-core scans with a defined set of manual checks axe can't do, and output a CSV of findings by impact and WCAG criterion. Use whenever the user asks for an accessibility audit, a11y check, WCAG compliance check, whether the site works with a screen reader or keyboard only, or ADA/EAA compliance review — trigger even if they just say "check this site for accessibility issues" without naming WCAG or axe explicitly. Distinct from the incidental a11y notes scenario-mapper and flow-runner make in passing — this is the dedicated, thorough version.
---

# Playwright Accessibility Audit

Two layers, run together: an automated axe-core scan (fast, reliable, covers the WCAG criteria that are actually mechanically checkable) plus a short manual-check pass for the things automated tools structurally can't judge — keyboard operability, focus order, whether alt text is actually meaningful rather than merely present. Roughly 30% of WCAG success criteria are testable by software; the other 70% is why the manual layer exists, not an afterthought bolted onto axe's output.

## Relationship to the other skills

`scenario-mapper` and `flow-runner` both read the accessibility tree as part of normal operation and may note something obviously wrong in passing — that's a side effect, not an audit. If the user has already run the mapper, its CSV's `area` column is a good source of pages/flows to audit here rather than rediscovering the site's structure from scratch. If a flow-runner scenario passes through a modal, dropdown, or validation-error state, those are exactly the states worth auditing here too — dynamic states are where automated single-page-load scans miss the most.

## Before you start

Same tool check as the rest of the toolkit (`@playwright/cli` vs MCP `browser_*` tools) — but this skill specifically needs whichever one lets you evaluate/execute JavaScript in the page context, since that's how axe-core gets run.

**Get axe-core's source before you touch the browser:**
1. Check for a local install first: `node_modules/axe-core/axe.min.js` in the current project.
2. If it's not there, install it: `npm install axe-core --no-save` (throwaway, doesn't need to touch the project's real dependencies).
3. Read the file's contents into a string — don't reference it by URL.

Injecting the source as a string through your evaluate tool, rather than pointing the browser at a CDN URL via a script tag, matters for a reason beyond convenience: a site with a strict Content-Security-Policy can block a `<script src="...">` from loading, but code your automation tool injects directly into the page context isn't a resource the page fetched, so CSP's script-src restrictions don't apply to it. This works regardless of how locked-down the target site is.

```
axeSource = read contents of axe-core/axe.min.js
evaluate(axeSource)          # defines `axe` as a global in the page
results = evaluate("axe.run()")   # returns { violations, passes, incomplete, inapplicable }
```

The exact call shape depends on whether you're on the CLI or MCP tools — check what your evaluate tool actually expects (raw JS string vs. a function to run in-page) rather than assuming.

## Core principles

**Scan real states, not just page-load.** A single axe.run() on initial load misses everything that only exists after interaction — an opened modal, an expanded mobile nav, a validation error, a populated search-results list. Interact first (open it, trigger it), then scan that state, the same way you'd approach steps in `flow-runner`.

**Use axe's own severity and citations — don't invent a new scale.** Every violation already comes with an impact level (`critical` / `serious` / `moderate` / `minor`), the specific WCAG success criterion it maps to, and a help URL with remediation guidance. Preserve all of it in the report. Re-scoring findings on your own scale just adds a translation step and loses traceability back to the standard.

**Aggregate across pages by rule, don't list every instance.** If a shared header component is missing an accessible name on every page, that's one finding with a note that it affects N pages — not N separate rows for the same root cause. Report instance count, not instance-by-instance duplication.

**Report what's actually there.** A page or flow with zero or few violations is a valid, good outcome — don't pad the report with marginal stylistic nitpicks to make the audit look more thorough than the site warranted. Same principle as the rest of this toolkit: the job is to find out, not to manufacture findings because an audit was requested.

## Manual checks (the ~70% axe can't do)

Run these on every page/state you scan, alongside the automated pass:

1. **Keyboard operability.** Tab through the page. Every interactive element — links, buttons, form fields, custom controls — should be reachable and operable without a mouse, and you should never get stuck unable to tab out of something (except an intentional modal focus trap, which should release and return focus to the trigger on close).
2. **Focus visibility.** Every focused element should show a visible focus indicator. `outline: none` with nothing replacing it is a common, easy-to-miss failure.

   **Never report a focus-visibility failure from computed styles alone — confirm it in a
   screenshot.** This check produces false positives more readily than any other in this list,
   for two reasons. Programmatic `element.focus()` does not reliably match `:focus-visible`, so
   frameworks that build their ring from CSS variables (Tailwind's `--tw-ring-*`, for example)
   read as fully transparent when they are in fact about to render a perfectly good ring. And
   modern rings arrive as one layer inside a multi-layer `box-shadow` written in `oklab()` or
   `color-mix()`, which is easy to parse wrongly and conclude nothing is there.

   The reliable procedure: press **Tab** (real key, not `.focus()`), screenshot the element,
   and compare it against the same element unfocused. If you cannot see a difference in the two
   images, it is a finding. If you can, it is not — regardless of what `outline` computes to,
   because the indicator may be a border change, a ring, or a background shift. `outline: none`
   on its own is not evidence of anything.
3. **Reading/tab order vs. visual order.** The order elements receive focus should roughly track their visual layout. A mismatch is disorienting for keyboard and screen-reader users even when each individual element is otherwise fine.
4. **Alt text quality, not just presence.** Axe flags a missing `alt` attribute but can't judge whether the text there is meaningful — `"IMG_4021.jpg"` or `"image"` passes axe's check and fails the actual point. Decorative images should have empty `alt=""`, not a description that adds noise for screen reader users.
5. **Dynamic content announcements.** When content updates without a page reload — search results appearing, a validation error, a toast — check whether it's exposed via `aria-live` or similar so screen reader users actually hear about it. A static scan won't catch a live region that's never triggered.
6. **Modal/dialog focus behavior.** Focus should move into a modal on open, stay trapped within it while open, and return to the triggering element on close.

## Workflow

1. Determine scope: a single URL, or a set of pages/flows (pull from a `scenario-mapper` CSV if one exists, otherwise ask which pages matter most if the site is large).
2. Get axe-core's source loaded per the setup above.
3. For each page/state: navigate or interact into that state, run the automated scan, then run through the manual checklist.
4. Aggregate findings across all scanned pages/states by rule, with affected-page counts.
5. Write the CSV, then a short chat summary — not a restatement of every row.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `A001` |
| `page_or_state` | Where it was found, e.g. "Checkout — step 2" or "Homepage — mobile nav expanded" |
| `rule_id` | Axe's rule id (e.g. `image-alt`, `color-contrast`) or a short label for manual findings (e.g. `manual-focus-order`) |
| `wcag_criterion` | e.g. "1.1.1 Non-text Content" |
| `impact` | `critical` / `serious` / `moderate` / `minor` |
| `source` | `Automated (axe)` / `Manual` |
| `description` | What's wrong, in plain terms |
| `selector` | The element or component affected |
| `affected_instances` | How many elements/pages this shows up on |
| `suggested_fix` | Paraphrased from axe's own help text for automated findings; your own for manual ones |
| `help_url` | Axe's helpUrl if available, otherwise the relevant WCAG technique page |

Write it with Python's `csv` module, same reasoning as the other skills in this toolkit — descriptions will contain commas and quotes.

## After writing the CSV

Give a short summary: pages/states scanned, total findings by impact level, and a call-out of anything `critical` or `serious` specifically (don't make the user dig through the CSV to find the things that matter most). Note explicitly if axe-core had to be installed fresh, and if any page's CSP or other restriction affected how thoroughly it could be scanned.

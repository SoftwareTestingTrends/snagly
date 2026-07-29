---
name: cross-browser-matrix
description: Run an existing test scenario across a matrix of browser engines (Chromium, Firefox, WebKit) and viewport sizes (mobile/tablet/desktop), and normalize the results into a single pass/fail comparison table. Use whenever the user wants to check something across browsers, check responsive/mobile behavior, verify something "works on Safari/Firefox," or build a compatibility matrix — trigger on phrases like "test this across browsers," "does this work on mobile," "check responsive behavior," "cross-browser check," or "compatibility matrix," even without the word Playwright. This skill runs a scenario that already exists (from flow-runner or a scenario-mapper row) across the matrix — it doesn't invent new scenarios, and it doesn't do pixel-level visual diffing (that's a separate concern from functional cross-browser correctness).
---

# Playwright Cross-Browser / Responsive Matrix

Takes a scenario you already have a plan for and runs it repeatedly across engines and viewport sizes, then collapses the results into one table instead of N separate reports you'd have to compare by hand.

## Before you start — read this one carefully, it changes the approach

**Browser engine and viewport are not the same kind of dimension.** Viewport size is freely adjustable within a single session — resize the context, no restart needed. Browser *engine*, if you're going through the official Playwright MCP server, is set at server launch (`--browser` flag or config), not per tool call — one running MCP server instance drives one engine for its whole session. This means the straightforward "just call a tool with a different browser argument" approach that works for viewport does not work for engine on the standard MCP setup.

Given that, and that you're on Claude Code with bash access: **for the engine dimension specifically, prefer writing and running a small standalone script** (Node with the `playwright` package, or Python with `playwright.sync_api`) that loops `chromium.launch()` / `firefox.launch()` / `webkit.launch()` directly, rather than trying to reconfigure or juggle multiple MCP server instances mid-conversation. This isn't the token-efficiency preference from the other skills in this toolkit — it's a hard functional constraint, not a nice-to-have. If you're on a community MCP server variant that does expose per-call browser selection, or you've deliberately got multiple MCP server instances running (one per engine), that works too — check what's actually in front of you before assuming either way.

**Know what "Chrome," "Edge," "Chromium," "Firefox," and "WebKit" actually mean here.** Chrome and Edge are both *channels* of the Chromium engine, not separate rendering engines — testing both catches almost nothing that testing Chromium alone wouldn't, since the underlying engine is the same. Chromium, Firefox (Gecko), and WebKit are three genuinely different engines. If you're prioritizing a limited matrix, that triad is where the real coverage is; Chrome/Edge beyond plain Chromium is a low-value addition unless you have a specific reason to think a browser-specific feature (not the rendering engine) is involved.

**Desktop WebKit is an approximation of Safari, not Safari itself — say so in the report.** Playwright's WebKit build tracks desktop Safari's engine reasonably well but isn't identical to real Safari, and is a bigger gap from real iOS Safari specifically (viewport units, on-screen-keyboard behavior, and PWA quirks all diverge on real iOS hardware). Report results as "WebKit engine," not "verified on Safari" or "verified on iPhone" — the difference matters to whoever reads the report and decides whether to trust it for a mobile-Safari-specific concern.

## Relationship to the other skills

This doesn't discover scenarios (`scenario-mapper`'s job) or invent new assertions (`flow-runner`'s job) — it takes a scenario's existing step plan and expected outcomes and runs them, unmodified, once per matrix cell, using the same wait-for-state-and-assert discipline as `flow-runner`. If a cell fails, capture evidence the same way flow-runner does; if the failure needs deeper investigation, hand it to `bug-triage` same as any other failure would go.

## Define the matrix deliberately

**First, figure out which axis (or both) the request actually needs — don't default to the full grid.** The two axes have very different costs: viewport is free (resize within the current session, same engine, seconds), engine is expensive on the standard MCP setup (the launch-time constraint above, potentially a whole separate script and browser install). If the request is really just "does this look right on mobile" with no stated interest in other engines, running it as a viewport-only pass in whatever single engine you already have — no script, no engine juggling — is the right scope, not a shortcut. Reserve the full engine × viewport grid for when cross-browser correctness is actually in question, not as the default for every request that touches either word.

- **Viewport-only** ("check this on mobile," "responsive check," "does this fit on a tablet"): resize within your current session, one engine, done.
- **Engine-only** ("does this work in Firefox/Safari," "cross-browser check" with no size concern stated): use whatever single default viewport is already in play, loop engines only.
- **Both** ("full compatibility matrix," "test across browsers and screen sizes," or the request is ambiguous enough that you'd rather over-cover than under-cover): the full grid below.

When you do run the full grid, don't run every scenario through every cell — that's combinatorial and mostly wasted effort. A reasonable default: run the **full matrix (3 engines × 3 viewports)** against the scenario's happy path (usually the P0 case), and spot-check lower-priority or negative-case scenarios on one or two cells at most, not the whole grid. This is the same instinct as the "comprehensive but not infinite" principle from `scenario-mapper` — more cells isn't more signal once you're past covering what's actually likely to diverge.

Default viewport set if none is specified: mobile (375×667), tablet (768×1024), desktop (1440×900). Adjust to match the site's actual breakpoints if you know them — testing exactly at a CSS breakpoint boundary is more informative than an arbitrary round number.

## Core principle: different isn't automatically broken

Browsers legitimately render some things differently — default form control styling, font rendering, scrollbar appearance — and that's normal, not a defect. What you're checking is whether the scenario's *defined expected outcome* still holds in each cell, not whether every cell looks pixel-identical to every other. If cell WebKit/Mobile shows a checkout button that's a slightly different shade or a native `<select>` that looks different from Chromium's, and the flow still completes and the confirmation still appears — that's a pass. Flag divergence only when it actually breaks the functional/semantic outcome the scenario defined. Pixel-level visual comparison is a different kind of check (visual regression testing) and isn't this skill's job.

## Workflow

1. Get the scenario's step plan and expected outcomes — from a `flow-runner` plan or a `scenario-mapper` row. Don't write a new plan from scratch here.
2. Decide scope (viewport-only / engine-only / both) per the guidance above, then the matrix within that scope, and decide execution method (standalone script vs. MCP, per the constraint above — only relevant at all if engine is in scope).
3. Run the scenario once per cell, same assertion discipline as `flow-runner`: wait for the actual expected state, don't just confirm the page loaded.
4. On any cell's failure, capture the evidence bundle for that cell (trace, screenshot, console/network log) before moving to the next.
5. Normalize into the matrix table below.

## Report format

The table's shape follows scope — a viewport-only check is a single column (one engine, several viewports), engine-only is a single row, and only a "both" run produces the full grid. Don't pad a narrower check out to a full grid just for the table to look more thorough than the check actually was.

```markdown
## Cross-browser/responsive matrix: [scenario name]
**Scope:** Chromium, Firefox, WebKit × Mobile (375×667), Tablet (768×1024), Desktop (1440×900)

| Viewport | Chromium | Firefox | WebKit |
|---|---|---|---|
| Mobile | ✅ | ✅ | ❌ |
| Tablet | ✅ | ✅ | ✅ |
| Desktop | ✅ | ✅ | ✅ |

### WebKit — Mobile
**Diverges at:** step 3, "submit shipping form"
**Expected:** redirect to /payment
**Actual:** no redirect after 10s, form appears to hang
**Evidence:** `matrix/webkit-mobile/trace.zip`, `matrix/webkit-mobile/screenshot.png`

**Notes:** Edge/Chrome omitted — same engine as Chromium, tested above. WebKit results reflect the desktop WebKit engine, not verified against real iOS Safari.
```

Give the grid first so the shape of the problem (one cell, one row, one engine entirely) is visible at a glance, then detail only the failing cells — don't write a full step-by-step for cells that passed.

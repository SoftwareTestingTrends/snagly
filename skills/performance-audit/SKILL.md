---
name: performance-audit
description: Measure Core Web Vitals (LCP, INP, CLS) and related performance signals on a site's key pages using a real browser (via Playwright MCP or @playwright/cli), by injecting the web-vitals library the same way axe-core gets injected for accessibility, and rate results against Google's published thresholds. Use whenever the user wants a performance audit, Core Web Vitals check, page speed review, or wants to know if a page is "slow" or would fail Google's page experience signals — trigger on phrases like "check Core Web Vitals," "is this page slow," "performance audit," "check LCP/CLS/INP," or "will this pass Google's speed requirements." Always distinguishes lab measurement (what this skill produces) from the field data (CrUX, real users) Google actually grades against — these are related but not the same number.
---

# Playwright Performance Audit

Measures the same three metrics Google actually grades pages on — Largest Contentful Paint, Interaction to Next Paint, Cumulative Layout Shift — using a real browser session, and rates them against Google's own published thresholds rather than inventing a new scale.

## Relationship to the other skills

Reuse `scenario-mapper`'s page list the same way `visual-snapshot` does, rather than rediscovering site structure. For INP specifically (see below), reuse an existing `flow-runner` scenario's interactions where one exists — a passive page load alone can't produce a meaningful INP reading. Findings here are a natural category for `report-generator` to fold in, and cadence (how often to run this) is exactly the kind of thing `test-plan` should schedule rather than running on every deploy — a full audit is more than a quick sanity check needs.

## Before you start

Same tool check as the rest of the toolkit, needing whichever tool lets you evaluate JavaScript in the page — same requirement as `accessibility-audit`. Get the `web-vitals` library's source available locally the same way and for the same reason as that skill gets axe-core: check `node_modules/web-vitals`, install it if missing (`npm install web-vitals --no-save`), and inject its source as a string rather than pointing the browser at a CDN script tag — it works regardless of the target's Content-Security-Policy, for the identical reason described in `accessibility-audit`.

## Core principles (and why)

**This measures lab performance, not the Core Web Vitals score Google actually grades.** Google's real page-experience grading uses CrUX — field data aggregated from real users' real devices and networks, at the 75th percentile over a rolling 28-day window. A single Playwright-driven run is one synthetic sample under one set of conditions on one machine. It's a genuinely useful early-warning signal and a real regression check, but it is not the number Search Console or actual visitors will produce. State this plainly every time — never present a lab reading with the same confidence as an official field score.

**INP needs real interaction — a page load alone won't produce a meaningful reading.** LCP fires once, early, from a passive load. INP measures responsiveness to actual clicks, taps, and keypresses, so if you only navigate and wait, there's nothing for it to measure. This is the same reason standard Lighthouse runs fall back to Total Blocking Time as an INP proxy — TBT correlates with responsiveness but isn't the same metric. Drive the page through its real interactions while measuring: reuse a `flow-runner` scenario for that page if one exists, or at minimum interact with the primary CTA and any obvious form fields, rather than measuring a page that never got touched.

**Use the specialized library — don't reconstruct these metrics from raw Performance API entries.** Same "delegate to the right tool" reasoning as `accessibility-audit`'s use of axe-core: `web-vitals` is the standard, browser-vendor-aligned implementation of exactly these metric definitions. Reinventing LCP/CLS/INP calculation from scratch risks subtly wrong numbers that don't match what Google or anyone else's tooling would report for the same page.

**A number alone isn't a finding — pair it with a likely cause where you can.** "LCP is 4.2 seconds" says there's a problem, not what to fix. Where you can identify one — an oversized hero image, a render-blocking script, a slow initial server response — say so. A Lighthouse run against the same page (if available) is the most reliable way to get this; short of that, note anything obvious from what you can observe directly (an unusually large image request, a long gap before the main content resolves).

**Prioritize poor-band metrics first, and leave what's already good alone.** Fix whatever's actually in the "poor" band before anything else, then INP (generally the hardest to improve), then LCP (usually the highest business impact), then CLS (usually the easiest). Don't propose changes to a metric that's already comfortably in the "good" range just to have more to report.

**Rate against Google's own published thresholds — don't invent a new scale.** Same "preserve the source's own severity" reasoning as `accessibility-audit`'s axe impact levels: LCP good ≤2.5s / poor >4s; INP good ≤200ms / poor >500ms; CLS good ≤0.1 / poor >0.25. Anything between good and poor is "needs improvement."

## Workflow

1. **Get the page list** — reuse `scenario-mapper`'s CSV if available, otherwise a shallow nav walk.
2. **Get `web-vitals`'s source loaded locally** per the setup above.
3. **For each page:** navigate, inject the library, drive real interactions (reusing a `flow-runner` scenario if one exists for that page), and capture LCP/CLS/INP as reported.
4. **Rate each metric** against Google's thresholds.
5. **For anything not "good,"** identify a likely contributor if you can (Lighthouse run, or direct observation).
6. **Write the CSV**, then a short chat summary — poor-band items first, and an explicit reminder that these are lab numbers, not field data.

## Measurement example

```javascript
const webVitalsSource = fs.readFileSync(require.resolve('web-vitals/dist/web-vitals.iife.js'), 'utf-8');
await evaluate(webVitalsSource); // defines `webVitals` global in the page

await evaluate(`
  window.__vitals = {};
  webVitals.onLCP(m => window.__vitals.lcp = m.value);
  webVitals.onCLS(m => window.__vitals.cls = m.value);
  webVitals.onINP(m => window.__vitals.inp = m.value);
`);

// ... drive real interactions here (click the primary CTA, fill a field) ...
// INP and CLS only have values worth reading after some interaction/time has passed

const results = await evaluate('window.__vitals');
```

Exact call shape depends on your evaluate tool, same caveat as the other injection-based skills in this toolkit — check what it actually expects.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `P001` |
| `page` | Page name/URL |
| `lcp_seconds` / `lcp_rating` | Measured value and Good/Needs Improvement/Poor |
| `cls` / `cls_rating` | Measured value and rating |
| `inp_ms` / `inp_rating` | Measured value and rating |
| `likely_contributor` | Best available explanation if not "good" — otherwise blank |
| `notes` | e.g. "measured without interaction, INP not meaningful" if that limitation applied |

## After writing the CSV

Give a short summary: pages measured, anything in the poor band (named explicitly, not buried in the CSV), and a clear restatement that these are lab measurements — a real assessment of what Google and users will see requires field data over time, not a single audit.

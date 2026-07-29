---
name: visual-regression
description: Compare two runs of visual-snapshot's screenshot capture — a baseline and a current run — using pixel-level diffing (pixelmatch, or @playwright/test's native toHaveScreenshot if a real Playwright Test project exists) to flag unintended visual changes, while masking known-dynamic regions and tolerating ordinary anti-aliasing noise. Use whenever the user wants to check for visual regressions, compare before/after a change, verify a redesign or refactor didn't break the look of pages, or catch unintended CSS/layout drift — trigger on phrases like "check for visual regressions," "compare screenshots before and after," "did this change break how anything looks," or "diff the site against the last version." Requires two visual-snapshot captures to compare — if there's no baseline yet, this skill's job is to establish one (using visual-snapshot), not to invent a comparison from nothing.
---

# Playwright Visual Regression

Takes two runs of `visual-snapshot`'s capture — a baseline and a current one — and finds the pages that actually changed, filtering out the noise that's normal (anti-aliasing, a carousel that rotated) from the noise that isn't (a layout that shifted, a section that disappeared).

## Relationship to visual-snapshot

This skill doesn't capture anything new on its own — it consumes two capture runs `visual-snapshot` already produced (same viewport, same settle discipline, same `snapshots/<date>/<page-slug>.png` naming). Consistency between the two captures is what makes a diff meaningful at all: if the baseline was taken at a different viewport or without letting the page settle, the diff will be dominated by capture-condition noise that has nothing to do with real changes. If there's no baseline yet, run `visual-snapshot` and treat its output as the baseline — that's a legitimate starting state, not a missing prerequisite to work around.

## Core principles (and why)

**Two thresholds, not one.** A per-pixel color-difference threshold (commonly ~0.1) tolerates ordinary anti-aliasing and font-rendering noise at the level of individual pixels. A separate page-level tolerance — a maximum acceptable percentage of changed pixels (commonly ~1%) — tolerates the fact that a handful of genuinely different pixels scattered around shouldn't fail a whole page, while a large contiguous change should. Relying on just one of these either misses real regressions or drowns in false positives from harmless rendering noise.

**Mask known-dynamic regions before diffing — don't just note them and move on.** `visual-snapshot` already flags carousels, timestamps, and similar widgets as "captured in an arbitrary state, this is normal." In a regression check, that same region will register as "changed" on essentially every single run unless it's explicitly excluded from the pixel comparison. Masking it out entirely is the difference between a report someone trusts and one they start ignoring because it cries wolf every time.

**A flagged diff never gets silently promoted to the new baseline.** Baseline management, not the diffing itself, is the part of visual regression testing that actually causes real-world setups to fail — because applications legitimately change, baselines have to update, but only deliberately. Every flagged page needs an explicit human decision: accept as an intentional change and update the baseline, or treat it as a real regression and fix the underlying issue. Never auto-accept the current run as the new baseline just because it's newer — that's exactly how a real regression gets permanently baked in as "correct."

**Prefer `@playwright/test`'s native `toHaveScreenshot()` if a real Playwright Test project already exists — it gets you more than pixelmatch alone.** It automatically disables CSS animations and waits for fonts to load before capturing, which removes a whole category of false positives from animation frames or font-swap timing that a bare pixelmatch comparison would still be exposed to. For an ad hoc comparison of two independent `visual-snapshot` capture runs — the more common case in this toolkit, since not every project has a full Playwright Test setup — use `pixelmatch` directly against the two PNG sets instead.

**Some pages cannot be pixel-diffed at all — exclude them deliberately rather than tuning thresholds until they pass.** Canvas/SVG charts, waveform renderers and anything drawing from resampled data can re-render with sub-pixel variation on every load even when the underlying data is byte-identical. Masking the chart region helps but often leaves the page over tolerance anyway. When you hit one, establish it by evidence — try the font wait, try a mask, try a longer settle — and if it still fails, exclude the page and say what you tried. Then cover it *functionally* instead: asserting a waveform renders a plausible heart rate and a non-trivial path count is a stronger check than asserting its pixels match yesterday's. Quietly raising a page's tolerance until a genuinely unstable page goes green is how a suite stops detecting anything.

A worked example from a real run: an ECG viewer measured 3.394% noise between two identical captures. Font-ready wait took it to 3.394% (no help), masking the chart to 1.148%, a 3-second settle made it *worse* at 4.803%. It was excluded, and the functional sanity scenario covering heart rate and SVG path count was cited as the substitute.

**Pages that appear in one run but not the other are a finding, not something to silently skip.** A page added, removed, or renamed since the baseline is itself worth surfacing explicitly in the report, not quietly dropped from the comparison because it doesn't have a clean pair.

## Workflow

1. **Confirm both captures exist** and were taken under matching conditions (same viewport, same page set). If there's no baseline, run `visual-snapshot` and establish one — say plainly that this run is a baseline, not a comparison.
2. **Match screenshots by page-slug** between the two runs. Flag any page present in only one side.
3. **For each matched pair**, diff using pixelmatch (or `toHaveScreenshot()` inside a real Playwright Test project), with masks applied over any region already flagged as dynamic, and both thresholds from above.
4. **Classify each page:** unchanged, changed-within-tolerance (no action needed), or flagged for review (exceeds tolerance).
5. **Compile the report** per the format below — flagged pages get full detail (baseline / current / diff image, percentage changed); unchanged and within-tolerance pages get a single summary line each, not the full triptych, so the report stays focused on what actually needs a decision.
6. **End with an explicit call to action** for every flagged page: accept as intentional (update baseline) or treat as a regression (goes to `bug-triage` if the cause isn't obvious).

## Diffing example

```javascript
const pixelmatch = require('pixelmatch');
const { PNG } = require('pngjs');

function diffScreenshots(baselinePath, currentPath, mask = []) {
  const img1 = PNG.sync.read(fs.readFileSync(baselinePath));
  const img2 = PNG.sync.read(fs.readFileSync(currentPath));
  const diff = new PNG({ width: img1.width, height: img1.height });

  // Blank out masked (known-dynamic) regions in both images before comparing,
  // so they can never register as a difference.
  for (const region of mask) blankRegion(img1, region);
  for (const region of mask) blankRegion(img2, region);

  const changedPixels = pixelmatch(
    img1.data, img2.data, diff.data, img1.width, img1.height,
    { threshold: 0.1 } // per-pixel color tolerance
  );
  const changedRatio = changedPixels / (img1.width * img1.height);
  return { changedRatio, diffImage: diff, flagged: changedRatio > 0.01 }; // page-level tolerance
}
```

Adjust both threshold values based on what the site actually needs — a marketing page tolerant of minor rendering differences can run looser than a pixel-sensitive design system component library.

## Report format

Reuse `visual-snapshot`'s HTML gallery approach, ordered flagged-pages-first:

```markdown
## Visual Regression: [site] — baseline [date] vs current [date]

**Flagged for review:** 2 of 14 pages
**Unchanged / within tolerance:** 12 of 14

### 🔴 Checkout — 3.2% changed
[baseline image] [current image] [diff image]
Likely area: shipping form section — appears to have shifted down ~40px
**Decision needed:** intentional change (update baseline) or regression (investigate)?

### 🔴 Pricing page — 1.8% changed
[baseline image] [current image] [diff image]
Likely area: pricing card border color
**Decision needed:** intentional change (update baseline) or regression (investigate)?

### Unchanged / within tolerance
Homepage · Product · About · Contact · ... (12 pages, no action needed)

### Pages missing a pair
"New /referral page" — present in current run, no baseline to compare against yet
```

Never end the report without the explicit decision-needed framing on every flagged page — a diff that's just reported and left hanging is easy to forget about; a diff that asks for a decision gets one.

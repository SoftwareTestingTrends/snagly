---
name: visual-snapshot
description: Navigate a site's main pages using a real browser (via Playwright MCP or @playwright/cli), capture full-page screenshots under consistent conditions, and compile them into a single reviewable gallery (HTML by default) so a human can see what every page currently looks like without clicking through the site themselves. Use whenever the user wants a visual overview, screenshot gallery, visual review doc, or to "see what all the pages look like" — trigger on phrases like "screenshot every page," "visual snapshot of the site," "compile a gallery of pages," or "show me what the site looks like right now," even without the word Playwright. This captures current state for review — it does not compare against anything or flag regressions (that's a future visual-regression skill's job, which would diff two runs of this same capture).
---

# Playwright Visual Snapshot

Sweeps the site's main pages, takes a full-page screenshot of each under consistent conditions, and compiles the set into one gallery a human can scroll through in a couple of minutes instead of clicking through the site themselves.

## Relationship to the other skills

Reuse `scenario-mapper`'s page list (the `area` column of its CSV) if one already exists, rather than rediscovering the site's structure from scratch. If none exists, do a lightweight nav walk yourself — primary nav plus immediate children, the same shallow default depth as the mapper's sanity mode. This isn't meant to be an exhaustive crawl; it's a broad, representative sweep.

This skill is also, incidentally, the capture half of what a future visual-regression skill would need — that skill would diff two runs of this same capture against each other to flag unintended changes over time. This skill doesn't do that diffing itself, but it's worth using a consistent naming/storage convention now (see below) so that extension is straightforward later rather than requiring a rebuild.

## Core principles (and why)

**Full-page, not viewport-only.** A screenshot call defaults to whatever fits in the viewport unless you explicitly request full-page capture. For a review gallery, viewport-only screenshots would cut off most real pages below the fold — always request the full-page variant.

**Wait for webfonts before capturing — not just for the network.** If a page's font lands after the
screenshot, every glyph renders in a fallback face and the capture is unrepresentative. Worse, in a
regression comparison it makes the entire page register as changed, which is indistinguishable from a real
layout break. Await `document.fonts.ready` (plus a short settle) before every shot, and be especially
careful when fonts come from a third-party CDN, where load timing is outside the app's control:

```js
await page.waitForLoadState('networkidle').catch(() => {});
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(500);
await page.screenshot({ path, fullPage: true });
```

Observed in practice: on a site loading Mulish from a third-party CDN, two captures of the same page on the
same build differed by 1.26% of pixels — over the usual 1% regression tolerance — purely from font-swap
timing. Awaiting fonts dropped it to 0.195%. Tall pages are the most exposed, because full-page stitching
takes longer and widens the window for the swap to land mid-capture.

**Let the page settle before capturing.** Same instinct as `flow-runner`'s "wait for state, not time" — wait for network activity to quiet down and any obvious loading indicators or in-progress animations to resolve before capturing. A screenshot taken mid-transition or while a skeleton loader is still showing misrepresents the page and undermines the whole point of the gallery, which is to show what the page actually looks like.

**Hold the viewport constant across the sweep.** Pick one viewport (default: desktop, ~1440×900) for a given gallery unless asked for more than one. A gallery only reads coherently if every page in it was captured under the same conditions — if both desktop and mobile review are wanted, treat those as two separate sweeps producing two galleries, not one gallery with mixed viewports that look inconsistent for reasons that have nothing to do with the pages themselves.

**Flag inherently dynamic content rather than pretending it isn't there.** Carousels, rotating banners, "related items" widgets, timestamps, and chat widgets can all be captured in an arbitrary transient state — that's normal, not a bug, but a reviewer who doesn't know a region is dynamic might mistake ordinary variability for something wrong. Note in the gallery which pages have a spot like this.

**Don't silently omit a page that fails.** If a page errors out or won't load, say so in the gallery in that page's place — a missing entry with no explanation looks like an oversight, not a finding.

**Label clearly, order sensibly.** Every image needs a label (page name, URL, viewport, timestamp) and the gallery should be ordered to match primary nav — the reviewer's mental model of the site — not alphabetical or whatever order you happened to visit pages in.

## Workflow

1. **Get the page list.** Reuse a `scenario-mapper` CSV's `area` column if one exists; otherwise do a shallow nav walk yourself (primary nav + immediate children).
2. **Decide viewport(s).** Default to one desktop viewport. If more than one is wanted, plan for separate galleries per viewport rather than mixing them.
3. **For each page:** navigate, wait for the page to settle, capture a full-page screenshot, save it with a clear filename (`snapshots/<date>/<page-slug>.png`), and note anything obviously dynamic you spotted.
4. **On failure to load:** capture whatever state you can (even a blank/error screen) and flag it clearly rather than skipping the page.
5. **Compile the gallery** per the format below.
6. **Give a short chat summary:** pages captured, any failures, viewport used, and where the gallery file lives — not a restatement of every page.

## Compiling the gallery

Default output is a single self-contained HTML file — embed each screenshot as a base64 data URI rather than linking to separate image files, so the whole gallery is genuinely one portable document with nothing to keep alongside it. This works well for a small-to-moderate page count. If the site has a large number of pages and base64-embedding would make the file unreasonably large, reference external image files from the HTML instead (still one gallery, just not literally one file) — use your judgement based on page count, and say which approach you used. **Over ~10 MB total, switch to referencing files** — the PNGs sit beside the HTML anyway, and a browser handles ten separate images far better than one enormous document.

**Screenshots are wider than you think — don't crush them.** A retina/full-page capture is commonly 2–3× the CSS viewport width (a 1440px viewport can yield a ~2700px image). Rendering that inside a narrow `max-width` container downscales it 2–3×, which blurs exactly the fine detail a reviewer is checking: nav text, borders, icon edges. So:

- Give the gallery a **wide container** (`max-width: min(1600px, 96vw)`), not a text-column width like 1000px.
- Style images `width: 100%; height: auto;` — never set both dimensions, which distorts aspect ratio.
- **Link each image to its full-size file** (`<a href="home.png"><img …></a>`) so a reviewer can open the original at 1:1 instead of squinting at a downscale. Say in the gallery that images are clickable.
- Full-page captures of long pages get very tall (10,000px+ is normal). That's fine — but note the capture's real pixel dimensions under each image so the reviewer knows what they're looking at.

```python
import base64

def to_data_uri(png_path):
    with open(png_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('ascii')
    return f'data:image/png;base64,{encoded}'
```

A minimal gallery structure — one section per page, in nav order, each with a label and its image:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Visual Snapshot — [site name] — [date]</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }
  section { margin-bottom: 3rem; border-top: 1px solid #ddd; padding-top: 1rem; }
  h2 { font-size: 1.1rem; }
  .meta { color: #666; font-size: 0.85rem; margin-bottom: 0.75rem; }
  img { width: 100%; border: 1px solid #ddd; }
  .flag { color: #a15c00; font-size: 0.85rem; }
  .failed { color: #b00020; }
</style>
</head>
<body>
  <h1>Visual Snapshot — [site name]</h1>
  <p class="meta">Captured [date] · Viewport [e.g. 1440×900] · [N] pages</p>

  <nav><!-- optional: anchor links per page for quick jump-around --></nav>

  <section id="homepage">
    <h2>Homepage</h2>
    <div class="meta">https://example.com/ · captured 14:02</div>
    <div class="flag">Note: hero carousel — captured mid-rotation, this is normal</div>
    <img src="[data URI or relative path]" alt="Homepage screenshot">
  </section>

  <!-- one <section> per page, repeated -->

  <section id="checkout" class="failed">
    <h2>Checkout</h2>
    <div class="meta">https://example.com/checkout · failed to load</div>
    <p>Could not capture — [error encountered]</p>
  </section>
</body>
</html>
```

Keep the styling plain and functional — this is a working review document, not a design showcase.

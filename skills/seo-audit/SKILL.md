---
name: seo-audit
description: Check technical/structural SEO elements across a site using a real browser — title tags, meta descriptions, canonical tags, meta robots (catching accidental noindex), Open Graph tags, structured data (JSON-LD) validity, and robots.txt/sitemap.xml sanity, including whether sitemap URLs actually resolve. Use whenever the user wants an SEO audit, metadata check, or wants to verify titles/descriptions/canonicals/structured data are present and valid — trigger on phrases like "check our SEO," "audit page metadata," "check structured data," or "verify robots.txt and sitemap." This is technical/structural validation — presence, validity, correctness — not SEO strategy, keyword advice, content quality judgment, or any claim about actual search ranking impact, none of which is something this skill (or anything without live access to a search engine's actual behavior) can verify.
---

# Playwright SEO Audit

Checks the mechanical, verifiable layer of SEO — does a title tag exist and is it a sane length, does a page meant to be indexed accidentally say otherwise, does structured data actually parse — not the strategic layer, which isn't something a browser session can verify.

## Scope boundary

This stays in checkable territory: presence, validity, structural correctness, uniqueness. It does not predict ranking impact, judge keyword choices, or give content strategy advice — those require actual search engine behavior or editorial judgment this skill has no way to verify, the same reason a general "improve the visual design" request was ruled out of this toolkit earlier. If asked to rank pages by SEO quality or predict search performance, redirect back to what's actually checkable instead.

## Relationship to the other skills

Reuse `scenario-mapper`'s page list. Don't duplicate `accessibility-audit`'s territory — image alt text is already that skill's job (a literal axe-core rule), even though it has SEO value too; cross-reference rather than re-checking it here. Reuse `link-audit`'s lightweight-HTTP-check technique for verifying sitemap URLs actually resolve, rather than re-deriving it. For a multi-locale site, hreflang tag correctness (whether locale variants correctly reference each other) is `i18n-audit`'s job, not this one's — this skill validates a single page's metadata in isolation.

## Core principles (and why)

**An accidental `noindex` or a `Disallow: /` in robots.txt is the single highest-value thing this check can catch.** Both are extremely common — usually leftover from a staging config that never got cleaned up — and extremely damaging, since either can make an entire site or section invisible to search engines while everything otherwise looks fine. Prioritize catching these over subtler issues like description length.

**Structured data validation here is a first-pass check, not full schema compliance.** Confirm each JSON-LD block is syntactically valid JSON, note its declared `@type`, and flag if commonly-required fields for that type are obviously missing — but say plainly that full schema.org conformance needs a dedicated validator (Google's Rich Results Test is the authoritative one) if the site actually depends on rich results. Don't imply deeper validation than what was actually done.

**Duplicate titles/descriptions across pages are one finding, not N findings.** If the same title appears on twelve pages, that's "not unique, affects 12 pages" — one row, same aggregation instinct as `accessibility-audit`'s "group by rule, note affected-page count."

**Length guidelines are guidelines, not hard failures.** Title/description length recommendations (roughly 50-60 characters for titles, 150-160 for descriptions) are about avoiding truncation in search results, not a pass/fail spec — flag outliers as worth a look, not as broken.

## Checks

**Per page:**
- Title tag: present, non-empty, reasonable length, unique across the site
- Meta description: present, non-empty, reasonable length, unique across the site
- Canonical tag: present, points to a sensible URL (not a 404, not an unrelated page, no canonical chain)
- Meta robots: no unexpected `noindex`/`nofollow` on a page that should be indexable
- Open Graph / Twitter Card tags: present for social sharing preview (`og:title`, `og:description`, `og:image` at minimum)
- H1 count: exactly one is the common recommendation — flag zero or multiple as worth a look, not an automatic failure
- Structured data: each JSON-LD block parses as valid JSON; declared `@type` noted; obviously-missing required fields flagged

**Site-level:**
- `robots.txt`: exists, parses without errors, doesn't accidentally block everything
- `sitemap.xml`: exists, valid XML, and its listed URLs actually resolve (reusing `link-audit`'s check technique)

## Workflow

1. Get the page list from `scenario-mapper` (or a shallow nav walk if none exists).
2. For each page, extract and check the per-page items above.
3. Fetch and check `robots.txt` and `sitemap.xml` at the site level.
4. Verify sitemap URLs resolve.
5. Aggregate duplicates across pages rather than reporting them per-page.
6. Write the CSV, then a short chat summary — noindex/robots.txt blocking issues first, since those are the highest-severity findings by far.

**Write the CSV with Python's `csv` module, never by joining strings.** Findings routinely
contain commas and quotes (title tags, meta descriptions, URLs with query strings), and
hand-built rows silently break column alignment on exactly those rows — the interesting ones.

```python
import csv, os
os.makedirs('scenarios', exist_ok=True)
with open('scenarios/seo-audit-findings.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=[...])
    w.writeheader(); w.writerows(rows)
```

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `S001` |
| `page` | Page or "Site-level" for robots.txt/sitemap findings |
| `check` | e.g. "Title tag," "Canonical," "Structured data," "robots.txt" |
| `finding` | What's wrong or worth noting |
| `severity` | e.g. `Critical` (noindex/blocking issue), `Moderate` (missing/invalid element), `Low` (length/style guideline) |
| `notes` | e.g. "affects 12 pages" for a duplicate finding |

## After writing the CSV

Give a short summary: pages checked, and anything Critical named explicitly — an accidental noindex or a robots.txt blocking issue should never be buried in a CSV row when it's found; it's worth surfacing in the chat summary itself.

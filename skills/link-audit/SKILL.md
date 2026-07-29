---
name: link-audit
description: Crawl a site exhaustively (deeper and wider than scenario-mapper's shallow, curated pass) using a real browser to discover every internal link and image, then verify each one's status via lightweight HTTP requests — flagging 404s, 5xx errors, redirect loops, long redirect chains, and broken images. Use whenever the user wants a broken-link check, dead-link audit, crawl for 404s, or link validation across the site — trigger on phrases like "check for broken links," "crawl the site for dead links," "find 404s," or "audit our links." This is mechanical and exhaustive by design, unlike scenario-mapper's curated "worth testing" list — a link is either broken or it isn't, so completeness matters more than prioritization here.
---

# Playwright Link Audit

Crawls outward from a starting point, finds every internal link and image the rendered page actually exposes, and checks whether each one resolves. Unlike everything else discovery-oriented in this toolkit, this isn't curated — it's meant to be exhaustive, because a broken link three levels deep in the site is just as broken as one on the homepage.

## Relationship to the other skills

Doesn't need `scenario-mapper`'s output the way `visual-snapshot` and `performance-audit` do — this crawls far beyond what that skill's shallow, curated pass would ever cover, by design. It's fine to start from the same seed (homepage, primary nav) if convenient, but the crawl should go wherever the site's own links lead, not stop at one level deep.

Findings here don't need `bug-triage`'s involvement. An HTTP status code is a deterministic, immediately confirmed fact the moment you observe it — there's no reproducibility question or root-cause investigation the way there is for a UI behavior bug. Report it directly.

## Core principles (and why)

**Discover via the browser, verify via lightweight HTTP requests — not a full page load for every link.** Finding the links in the first place needs a real browser: a JS-heavy site can render links into the DOM that would never show up in raw HTML, so a plain HTTP crawler would miss them. But once a URL is known, loading a full page — images, scripts, full render — just to check whether it 404s is needlessly expensive across what could be hundreds of links. Use Playwright's request API (a lightweight HTTP call within the same browser context) for the actual status check, and reserve full navigation for pages you're deliberately crawling deeper into.

**Stay within the site's own domain for recursive crawling; verify external links without crawling into them.** Following external destinations recursively turns a link check into an uncontrolled crawl of the internet. Confirm an external link actually resolves, then stop — don't follow it further.

**Guard against crawl traps.** Pagination, calendar widgets, faceted search filters, and similar patterns can generate effectively unbounded URLs. Cap the total pages crawled, deduplicate by normalized URL, and watch for a URL pattern that's clearly generating new pages indefinitely rather than following it forever hoping it terminates.

**Redirect chains and loops are findings too, not just hard failures.** A redirect loop (A → B → A) will hang a real user's browser and deserves the same urgency as a 404. A long redirect chain (roughly four or more hops) technically works but is slow and fragile — worth flagging even though it isn't broken yet.

**Severity should reflect where the link lives, not just its status code.** A broken link in primary navigation or a core flow is a different problem than one in an old post's footnote — both are worth fixing, but not at the same priority. Note whether it's internal or external and where it was found, and let that inform severity rather than treating every 404 identically.

**Prefer staging over production, and pace the crawl reasonably.** Same environment preference as the rest of this toolkit — a fast, wide crawl hitting a production site repeatedly isn't a great way to check it. Use staging if one exists, and don't hammer whichever environment you do use.

## Workflow

1. **Determine the seed** — homepage, or a provided starting list — and the domain boundary for recursive crawling.
2. **Crawl:** for each page, navigate, extract every `<a href>` and `<img src>` from the rendered DOM, queue newly discovered same-domain URLs (respecting caps and dedup), and record external URLs to verify without crawling into them.
3. **Verify every discovered URL** via a lightweight HTTP request: status code, redirect chain if any, loop detection.
4. **Classify:** hard 404/5xx, redirect loop, long redirect chain, broken image.
5. **Assign severity** based on internal/external and where it was found.
6. **Write the CSV**, then a short chat summary — internal, high-severity issues first.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `L001` |
| `source_page` | Where the link/image was found |
| `link_url` | The URL that was checked |
| `link_type` | `Link` / `Image` |
| `scope` | `Internal` / `External` |
| `status_or_issue` | e.g. `404`, `500`, `Redirect loop`, `Redirect chain — 5 hops` |
| `severity` | e.g. `Critical` (internal, primary nav/core flow), `Moderate` (internal, elsewhere), `Low` (external) |
| `notes` | Anything relevant — e.g. "behind auth wall, expected" if a link correctly requires login rather than being broken |

## After writing the CSV

Give a short summary: pages crawled, total links/images checked, and a breakdown by severity — leading with internal Critical findings, since those are the ones that actually need fixing soonest. Note the crawl boundary you used (page cap, domain scope) so the reader knows what was and wasn't covered, same as every other skill in this toolkit being explicit about scope rather than implying completeness it didn't actually achieve.

---
name: i18n-audit
description: Check internationalization correctness across a site's supported locales using a real browser — text actually changes per locale, no leaked raw translation keys, right-to-left layouts don't visually break, translated text doesn't overflow its container, locale selection persists across navigation, hreflang tags correctly pair locale variants, and date/currency/number formatting matches the locale. Use whenever the user wants to check translations, locale switching, RTL layout, or multi-language correctness — trigger on phrases like "check our translations," "test locale switching," "does RTL work," or "audit our i18n." This checks mechanical correctness, not translation quality — it can flag obviously broken or untranslated text but doesn't grade whether a translation is idiomatic or culturally appropriate, the same kind of judgment call this toolkit stays out of for visual design.
---

# Playwright i18n Audit

Checks that switching locale actually does something, that switch actually sticks, that right-to-left layouts don't visually fall apart, and that nothing's silently still showing a raw translation key or the wrong language.

## Scope boundary

This is mechanical correctness — did the text change, did the layout survive, does a hreflang tag point where it should — not translation quality review. It can flag something that looks obviously broken (a raw key like `HOMEPAGE_HERO_TITLE` instead of a sentence, a garbled machine-translation artifact, an English sentence sitting untranslated in an otherwise-translated page) but doesn't grade whether a translation is natural, idiomatic, or culturally appropriate beyond that. Same reasoning as this toolkit staying out of visual design opinions — that's a different kind of judgment than what the rest of this toolkit does.

## Relationship to the other skills

Reuse `scenario-mapper`'s page list, applied per-locale. Reuse `visual-snapshot`'s capture mechanism for RTL layout checks — whether a right-to-left layout actually mirrors correctly is fundamentally a visual question, not something worth re-deriving a separate capture step for. hreflang correctness is this skill's job, not `seo-audit`'s — that skill validates a single page's metadata exists and is structurally sound; this one validates that locale variants of the same content correctly reference each other.

## Core principles (and why)

**Leaked translation keys are pattern-matched, not confirmed — flag for review, don't assert as fact.** Text that looks like a code identifier (`HOMEPAGE_HERO_TITLE`, `{{missing_key}}`, dotted paths like `home.hero.title`) instead of a sentence is a strong signal something's untranslated, but pattern-matching on "looks like an identifier rather than prose" has real false-positive risk — a legitimate SKU or product code can look similar. Flag it as a candidate for review, not a confirmed bug.

**Text overflow from translation expansion is mechanically checkable, not just visual.** Translated text is often meaningfully longer than the source (German and Finnish especially) — compare an element's `scrollWidth`/`scrollHeight` against its visible `clientWidth`/`clientHeight` to catch silent clipping or overflow programmatically, rather than relying entirely on spotting it by eye in a screenshot.

**Locale persistence matters as much as the switch itself.** A switcher that works on the page it's clicked from but silently resets to default on the next navigation is a common, easy-to-miss bug — check the selected locale survives at least one subsequent navigation, not just that switching itself works.

**RTL correctness is a visual question — look at it, don't just assert it from the DOM.** Whether a right-to-left layout actually mirrors correctly (alignment, element order, icon direction, no overlapping or garbled mixed-direction text) is best caught by capturing and looking at it, the same way `visual-snapshot` already does for anything visual in this toolkit.

## Checks

- **Translation coverage:** capture text content in the default locale and in each target locale; confirm it actually differs, not silently falling back to default for some or all of the page.
- **Leaked keys:** scan for text that looks like an untranslated key rather than prose; flag for review.
- **RTL layout:** for right-to-left locales, capture full-page screenshots (reusing `visual-snapshot`) and note anything that looks broken — misaligned text, elements that didn't flip, overlapping content.
- **Text overflow:** compare `scrollWidth`/`scrollHeight` against `clientWidth`/`clientHeight` on key elements per locale, flagging silent clipping.
- **Locale persistence:** switch locale, navigate to a second page, confirm the locale held.
- **hreflang correctness:** each locale variant's hreflang tags should reference all other variants and itself; flag missing or asymmetric pairs.
- **Date/currency/number formatting:** spot-check that a locale known to use different conventions (date order, currency symbol/placement, decimal/thousands separators) actually shows them, not a hardcoded default.

## Workflow

1. Identify supported locales — from a language switcher, URL structure (`/en/`, `/fr/`), or a provided list.
2. Get the page list from `scenario-mapper`.
3. For each key page, run the checks above across locales, using the default/reference locale as the comparison baseline.
4. For RTL locales, capture screenshots per the RTL check above.
5. Write the CSV, then a short chat summary — leaked keys and untranslated pages first, since those are the most visible to real users.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `I001` |
| `page` | Page checked |
| `locale` | The locale this finding applies to |
| `check` | Translation coverage / Leaked key / RTL layout / Overflow / Locale persistence / hreflang / Formatting |
| `finding` | What's wrong or worth review |
| `severity` | e.g. `Critical` (untranslated core page, leaked key on a P0 flow), `Moderate` (overflow, minor formatting), `Low` |
| `notes` | Anything relevant — e.g. "flagged as possible leaked key, verify against translation source" |

## After writing the CSV

Give a short summary: locales and pages checked, and anything Critical named explicitly — an entire page still in the default language, or a leaked key on a primary flow, shouldn't be buried in a CSV row.

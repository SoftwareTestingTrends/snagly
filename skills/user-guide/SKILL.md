---
name: user-guide
description: Generate an end-user-facing how-to guide for a site feature by walking through a verified flow with a real browser, capturing a screenshot with the relevant element visually highlighted at each step, and writing a plain-language instruction using the interface's own button/field labels. Use whenever the user wants a user guide, help doc, how-to article, or step-by-step walkthrough for end users — trigger on phrases like "write a user guide for checkout," "create a how-to doc for signup," or "document how to use this feature." Only documents flows already verified by flow-runner (or a test-case-writer document marked Verified) — never writes user-facing instructions for a flow nobody's confirmed actually works. Written for end users, not for QA — no testing jargon, no assertions, no priorities.
---

# Playwright User Guide

Turns a verified flow into the kind of help article a real user would actually want: a screenshot per step with the thing to click visibly marked, and an instruction in plain language using the interface's own wording — not a testing report wearing a friendlier font.

## Relationship to the other skills

**Input must be verified — same reasoning as `e2e-codegen`.** Source from a `flow-runner` run that's already confirmed passing, or a `test-case-writer` document marked Verified. Never write user-facing instructions from a raw, unexecuted `scenario-mapper` row — a guide telling someone to click a button that doesn't do what the guide claims is worse than no guide at all, since it actively damages trust rather than just being unhelpful. If nothing's verified yet, verify first, or say plainly that the guide is provisional.

**Reuses `visual-snapshot`'s capture discipline** — full-page, settled, consistent viewport — with one addition: highlighting the target element before capturing, so each screenshot visually shows what the instruction is talking about.

**Skip anything from `network-assertion` or `bug-triage`.** Backend behavior, API calls, error-handling internals — none of that belongs in a document describing what a user sees and does. A user guide covers the visible interaction only.

## Core principles (and why)

**Use the interface's own words, not a paraphrase.** If a button reads "Add to Bag," the instruction says "Add to Bag" — not "add the item to your cart." Read the actual rendered label rather than describing it generically. Same "read what's actually there, don't guess" discipline as `flow-runner`, now applied to writing prose instead of clicking things — and it matters more here, because a user hunting for a button that matches the guide's wording exactly will miss one described approximately.

**Highlight the element in the screenshot itself.** Inject a visible outline around the target element (the same evaluate-based technique used for axe-core and web-vitals injection elsewhere in this toolkit) before capturing, rather than relying on a caption like "click the button in the top right" to do the work. A marked screenshot is unambiguous in a way a text description alone never quite is.

**Write for the end user, not for QA.** Every other skill in this toolkit writes for a technical reader — assertions, priorities, evidence paths. This is the one exception. No "expected outcome," no "P0," no "assert," no testing vocabulary of any kind. Describe what the person will see and what to do, the way an actual product help article reads.

**This is a snapshot of current UI, not a permanent fact.** Interfaces change. Date the guide. If `visual-regression` later flags a meaningful change on a page this guide documents, that's a signal to regenerate the affected section — the guide doesn't self-correct, and an undated guide reads as more current than it might be.

**Don't document more than the user needs.** Skip internal implementation details and anything from a bug investigation or network check — if it isn't something the user sees or does, it doesn't belong in the guide.

## Workflow

1. **Get the verified flow** — a `flow-runner` run that passed, or a Verified `test-case-writer` document. Verify first if neither exists.
2. **For each step:** identify the target element, read its actual visible label, inject a highlight around it, capture a screenshot, and write a plain-language instruction using that exact wording.
3. **Compile** into a single HTML document, in the order the flow actually happens, with a brief intro (what this covers, any prerequisites like needing an account).
4. **Date the document.**
5. **If a formal, printable, or externally-distributed version is wanted**, hand off to the `docx` or `pdf` skill for that — don't reinvent document formatting here; this skill's default output is a self-contained HTML file, same as `visual-snapshot`.

## Highlighting example

```javascript
await evaluate(`
  const el = document.querySelector('[data-testid="add-to-bag"]'); // or the located element from the verified run
  el.style.outline = '3px solid #e63946';
  el.style.outlineOffset = '2px';
`);
// then capture the full-page screenshot, same technique as visual-snapshot
```

## Output format

Single self-contained HTML file (base64-embedded screenshots, same reasoning as `visual-snapshot`), structured as:

```html
<h1>How to [complete the flow] — [site name]</h1>
<p class="meta">Last verified: [date]</p>
<p>[Brief intro — what this covers, any prerequisites]</p>

<div class="step">
  <h2>Step 1: [Plain-language description]</h2>
  <img src="[highlighted screenshot]" alt="Step 1 screenshot">
  <p>Click <strong>[exact button label]</strong>.</p>
</div>

<!-- one .step block per step, in order -->
```

Keep the tone the way a real help article reads — short sentences, no jargon, second person ("Click Add to Bag" not "The user clicks the Add to Bag button").

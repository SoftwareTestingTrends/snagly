---
name: figma-compare
description: Compare a Figma design against its live web implementation using the Figma MCP server (design side) and a real browser via Playwright MCP or @playwright/cli (implementation side), producing an evidence-backed diff report — field-by-field structure, labels, required markers, dropdown option lists, conditional states, and visual styling. Use whenever the user provides a Figma URL and a site URL and wants to know if the implementation matches the design — trigger on phrases like "compare the Figma design against...", "does the site match the design," "design QA," "verify this screen against the mock," or "check the implementation against Figma," even if they never say Playwright or MCP. Distinct from visual-regression (which pixel-diffs two captures of the same site over time — no Figma involved) and visual-snapshot (capture only, no comparison). This skill compares design intent to built reality, which is judgment work, not pixel math.
---

# Playwright Figma Compare

Takes a Figma design URL and a live site, walks both, and reports where the implementation matches the design and where it deviates — with severity, evidence screenshots, and a clear separation between "defect," "implementation is right and the mock is stale," and "can't be verified from a mock."

## Relationship to the other skills

- `visual-regression` pixel-diffs two runs of the same site. This skill never pixel-diffs against Figma exports — a mock and a DOM render will never match at the pixel level, and pretending they should produces noise. The comparison here is structural and semantic, checked by eye and by accessibility snapshot.
- Confirmed functional defects found along the way (not just design deviations) deserve their own writeup — hand them to `bug-triage` for reproduction rigor or draft a ticket directly (severity, steps, expected/actual, evidence), optionally filing via `jira-connector`.
- The final report can feed `report-generator` alongside other testing artifacts.

## Prerequisites

- **Figma MCP server** (`get_screenshot`, `get_metadata`, `use_figma`) — the remote server (browser OAuth sign-in to your Figma account; no desktop app needed) or the local server inside the Figma desktop app with the file open. Load the `figma-use` skill before any `use_figma` call.
- **Browser automation** — Playwright MCP server or `@playwright/cli`.
- **Site access** — if the project has a target config (e.g. `targets/*.yaml` with login steps, credentials source, safe-to-mutate tenants, known noise), read it first and follow it. If none exists and the site needs login, ask the user for the path to credentials rather than guessing.

## Core principles (and why)

**The linked node is often not the screen.** Figma "copy link" URLs frequently point at whatever leaf node the designer had selected — a dropdown item, a single input — not the screen or section under discussion. Resolve the real scope before capturing anything: walk up the parent chain to the enclosing frame/section, then enumerate its children. Sections typically hold *several* screen frames (state variants: different country, toggle on/off, error state) plus small detail frames that spec dropdown contents. Compare against all of them, not just the first screen you find.

**Extract option lists as text, not pixels.** A closed dropdown in a mock shows one value; the design's real spec for its options usually lives in a separate detail frame. Screenshots of those frames work, but extracting the text nodes directly (via `use_figma`, `findAll(t => t.type === 'TEXT')`) gives you the exact strings *and their order* — which lets you catch "same options, different order" and "labels missing the ISO codes" class differences that eyeballing misses.

**Mock data is not spec.** Filled example values in a mock (names, dates, IDs) are illustration, not requirements — and mocks contain copy-paste errors (a date pasted into a "Group Number" field, a stray required-asterisk on one frame but not its sibling). Placeholder *text* visible in empty mock fields IS comparable; example *values* in filled fields are not. When the mock contradicts itself between frames, note it as a mock inconsistency instead of flagging the implementation.

**Exercise every conditional state the design shows.** If the design section has N screen variants, the implementation must be driven into each one: select the relevant dropdown value, toggle the radio, switch the country. A form that matches the default state can still be missing an entire conditional block. Enumerate the states from the Figma frames first, then reproduce each in the browser and capture it.

**Compare structure from the accessibility snapshot, pixels from screenshots.** The a11y snapshot gives exact labels, required markers, placeholder text, option lists, disabled states, and field order — far more reliable than reading a screenshot. Use screenshots for what snapshots can't show: colors, spacing, icons (flag glyphs), band backgrounds, truncated placeholder text. You need both.

**Leave the site exactly as you found it.** Design comparison is read work. Open forms, switch dropdowns, toggle radios — then Cancel/Discard, never Save on records you didn't create. Watch for two-step confirmations (a second "are you sure" dialog, sometimes outside `[role=dialog]`) and complete them so you don't leave a half-open modal blocking the page. If a design state is only reachable with persisted data (e.g. the read-only view of a variant that doesn't exist yet), create a clearly-marked throwaway record, capture, then archive/delete it — and say so in the report. After any discard, verify the original values actually came back; that check is free and occasionally finds a real bug.

**Not every gap is a defect.** Three other explanations recur, and the report must distinguish them:
1. **The mock is stale** — the implementation deviates in a way that's obviously more correct (e.g. a US form showing "State" where the mock still says "Province"). Flag as "implementation likely right — confirm with design."
2. **Per-tenant / per-environment configuration** — a feature visible in the mock may be intentionally disabled where you're testing (feature flags, org/tenant-level settings, license tiers). Before rating a missing element as a defect, check project notes for known config differences, and phrase the finding as a question when unsure. Ask the user if it's cheap to do so.
3. **Out of the mock's scope** — real apps have elements (buttons, footers, metadata rows) the design frames simply don't include. Absence from the mock is not a spec to remove them.

**Number the findings and rate severity.** Each difference gets an ID (D1, D2… or E1, E2… per section), a severity (functional data-loss > missing content > behavior deviation > label/order > cosmetic), the Figma expectation, and the implementation reality. Numbered findings survive into tickets, follow-up runs, and conversations; "a few label issues" doesn't.

**Record the build.** Read and note the app's version identifiers at the start (footer, sidebar metadata, response headers). Fast-moving staging environments can change builds mid-day; a comparison is only meaningful pinned to a build.

## Workflow

### 1. Resolve the design scope
1. Parse `fileKey` and `nodeId` from the Figma URL (`figma.com/design/:fileKey/...?node-id=X-Y` → node `X:Y`).
2. Load the `figma-use` skill, then via `use_figma`: get the node, walk `parent` up to the enclosing SECTION/top frame, list its children (names, sizes, positions). Screen-sized frames (~360–1600px wide) are state variants; small frames (~200–600px) are usually dropdown/detail specs; ignore connector lines.
3. Note the quirk: `get_metadata` without a nodeId may list only a cover page even when the file has more; navigate with `use_figma` (`getNodeByIdAsync` + `setCurrentPageAsync`) instead. Set the current page before `findAll` — an unloaded page returns empty results, not an error.

### 2. Capture the design
1. `get_screenshot` each screen frame and the section overview; download the returned URLs (curl) into `runs/figma-compare-<date>/figma/` with descriptive names.
2. Extract text from each detail/dropdown frame via `use_figma` — these are the option-list specs.
3. Read the screens and write down, per state: field inventory in order, labels, required markers, placeholder text where visible, conditional blocks and what triggers them.

### 3. Drive the implementation
1. Follow the target config for login/tenant selection if one exists.
2. Navigate to the screen under comparison. If a wizard/consent step precedes it, go through it.
3. For each design state: put the form into that state, take the a11y snapshot (structure) and an element screenshot (visuals) into `runs/figma-compare-<date>/site/`. Resize the viewport tall enough that dialogs don't scroll-clip before element screenshots.
4. Capture full dropdown option lists from the snapshot — they're free there.
5. Undo everything (Cancel/Discard + confirmations); verify restoration. Archive/delete any throwaway records you created.

### 4. Compare and report
Write `runs/figma-compare-<date>/report.md`:

```markdown
# Figma vs Implementation — [screen name] ([variant])
**Date / Build / Environment / Figma file+node / Evidence paths**

## Verdict
One paragraph: overall match quality, count of differences by severity.

## What matches ✅
| Design element | Status |

## Differences ⚠️
| # | Severity | Area | Figma | Implementation |
(one row per finding; mark "impl likely right — confirm with design" and
"possibly per-tenant config — confirm" where applicable)

## Not verifiable from the mock
(validation messages, dynamic behavior, anything the mock doesn't specify)
```

5. Summarize in chat: verdict first, then the differences worth acting on, then where the evidence lives. Offer bug tickets for the findings that are genuine defects.

## Judgment calls that recur

- **Defaults**: an implementation that silently pre-selects a real value (first insurer in the list, first physician) where the mock shows an example value is ambiguous — the mock rarely specs the default. Flag it as a product question, especially where a wrong silent default could persist bad data.
- **Data loss on state switch**: if switching a variant control (country, type) clears sibling field values, that's a functional finding — capture before/after evidence and verify whether discard restores. Rate it above any cosmetic finding.
- **Label casing/wording**: report but rate low. Batch them into one row/ticket rather than one each.
- **Empty-state conventions** (blank vs "--" vs "N/A" in read-only views): cosmetic, but easy to verify and worth one row.

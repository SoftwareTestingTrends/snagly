---
name: form-fuzzing
description: Test form fields with unusual-but-realistic inputs (empty, boundary-length, unicode, malformed formats, real-but-uncommon characters like apostrophes in names) using a real browser, to verify the app degrades gracefully — clear validation messages, no crashes, no data corruption, no broken layout. Use whenever the user wants to test form robustness, input validation, edge-case inputs, or how a form handles unusual data — trigger on phrases like "test form validation," "fuzz this form," "check edge-case inputs," or "does this form handle unusual input gracefully." This is explicitly a UX/robustness check, not a security or penetration test — it never uses injection payloads, never attempts to bypass authentication or access data that isn't its own, and never tries to confirm or exploit a vulnerability. If something observed looks security-relevant, the job is to flag it for proper review, not investigate further.
---

# Playwright Form Fuzzing

Tests forms the way real, messy human input actually happens — empty submissions, names with apostrophes, absurdly long strings, unicode, malformed dates — and checks whether the app handles each one with a clear message or falls over.

## Scope boundary — read this first

**This is robustness and UX testing, not security testing.** The goal is confirming graceful degradation, not finding exploitable vulnerabilities. Concretely:

- Never use SQL syntax, script/injection payloads, or anything crafted to execute code or manipulate a query.
- Never attempt to bypass authentication, access another user's data, or escalate privileges.
- Never attempt to confirm, reproduce, or exploit something that looks like a security vulnerability once observed — flag it and stop.
- If a finding looks security-relevant (unescaped output, a leaked stack trace or internal error message, anything suggesting the app isn't sanitizing input the way it should), the record should say "possible security-relevant issue — recommend proper security review" and go no further. That's a different discipline with different tooling and different people who should own it; this skill's job ends at noticing something worth their attention, not investigating it.

## Core principles (and why)

**A good validation failure is specific and actionable — not just "the app didn't crash."** "Please enter a valid email address" is a pass. A raw stack trace, a blank page, or a generic "something went wrong" for a simple format mistake is a fail, even though the server technically stayed up. Judge the quality of the failure mode, not just survival.

**Real-but-unusual input matters more than purely synthetic edge cases.** A name field that rejects "O'Brien" or "Müller" is a real bug affecting real people, arguably more worth catching than an extreme boundary case almost nobody will ever hit. Weight the input set toward what's actually likely to occur, not toward maximum weirdness for its own sake.

**Check what happens after submission, not just at the point of entry.** Client-side validation might correctly reject bad input while the same input, reaching the backend directly, gets handled less carefully — because the backend assumed the client already filtered it. Where it matters, pair with `network-assertion` to submit unusual data via a direct request rather than only through the UI, checking the server doesn't rely entirely on client-side filtering.

**Check round-tripping, not just acceptance.** If a field accepts unicode or special characters, confirm the value displays correctly wherever it's shown again — a profile name, a reflected comment. Silent mangling on the way back out is as real a bug as wrongly rejecting it on the way in.

**Don't fuzz every field with equal effort.** A field in a `scenario-mapper` P0 flow (signup, checkout, a primary contact form) is worth the full input set; a rarely-touched internal admin field isn't. Match effort to how much the field actually matters.

## Input categories (all non-malicious)

- **Empty / whitespace-only** — nothing, or only spaces/tabs, in a required field.
- **Boundary length** — empty, single character, at the stated max length if known, one over, and an extreme length (e.g., 10,000 characters) to check for graceful truncation/rejection rather than a crash or broken layout.
- **Numeric boundaries** — zero, negative where positive is expected, decimals where an integer is expected, very large numbers, non-numeric characters in a numeric field.
- **Format validity** — malformed email, malformed phone number, invalid dates (Feb 30th, an obviously wrong year).
- **Unicode / internationalization** — accented characters, non-Latin scripts, emoji, right-to-left text — check display, storage, and round-trip, not just acceptance.
- **Real-but-uncommon characters** — apostrophes, hyphens, ampersands in names — a very common, very real bug class.
- **Whitespace formatting** — leading/trailing spaces, multiple internal spaces, a pasted newline into a single-line field.
- **Single stray display-sensitive characters** — a lone `&`, `<`, `>`, or `"` in a text field, purely to confirm it displays back literally rather than breaking the page's own rendering. This is a rendering-robustness check, not an injection attempt — never combine these into any kind of payload or script-like sequence.
- **File upload edge cases**, if applicable — wrong file type, zero-byte file, oversized file (using genuinely harmless test files, not anything crafted to be malicious).

## Workflow

1. **Identify target forms** — reuse `scenario-mapper`'s discovered `Auth` and `Multi-step Commit` entries, prioritizing P0 flows.
2. **For each field**, infer its expected type/constraints from its label and input type, and select the relevant subset of categories above — unicode matters for a name field, numeric boundaries matter for a quantity field, not the reverse.
3. **Submit one edge case at a time** — isolating which input caused which behavior matters; submitting several at once muddies the finding.
4. **Observe:** clear validation message, silent incorrect acceptance, crash/error, or broken layout.
5. **Where it matters, check server-side handling too**, pairing with `network-assertion` to submit directly rather than only through the UI.
6. **For accepted special/unicode input, verify it round-trips correctly** wherever it's displayed again.
7. **If anything looks security-relevant, flag it and stop there** — don't investigate further, per the scope boundary above.
8. **Record findings**, then a short chat summary — real bugs and anything security-flagged first.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `F001` |
| `form_field` | e.g. "Signup — Email field" |
| `input_category` | e.g. "Boundary length," "Unicode," "Real-but-uncommon characters" |
| `input_description` | What was entered — describe rather than paste if it's long (e.g. "10,000-character string," not the string itself) |
| `observed_behavior` | What actually happened |
| `assessment` | Pass / Fail / Security-relevant — recommend review |
| `notes` | Anything else — e.g. "client rejected it but a direct request to the API accepted it" |

## After recording

Give a short summary: fields tested, pass/fail counts, and anything marked security-relevant called out explicitly and separately — that category should never blend into the general findings, since it needs a different kind of attention than a UX validation-message fix does.

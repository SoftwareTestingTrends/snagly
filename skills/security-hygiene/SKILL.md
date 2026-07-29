---
name: security-hygiene
description: Check basic web security hygiene using a real browser — HTTPS enforcement and mixed content, cookie security flags (Secure/HttpOnly/SameSite), common security response headers (CSP, X-Content-Type-Options, X-Frame-Options, HSTS), a narrow check for commonly-exposed accidental files (.env, .git/config, source maps), and known-vulnerable JS library versions via Retire.js. Use whenever the user wants a security hygiene check, wants to verify cookie flags or security headers, or check for accidentally exposed files. This is explicitly hygiene, not a security audit or penetration test — every check here is passive observation (reading a header, a cookie attribute, a file the server already serves to anyone) — it never attempts SQL injection, XSS, auth bypass, or any exploit, and never tries to confirm a finding is actually exploitable. Passing every check here is not evidence the site is secure.
---

# Playwright Security Hygiene

Checks the mechanical, easy-to-get-wrong hygiene basics — a cookie missing a security flag, a source map left publicly accessible, an outdated library with a known CVE — not an assessment of the site's actual security posture.

## Scope boundary — read this first

**This is hygiene, not a security audit.** Every check here is passive observation: reading an HTTP response header, reading a cookie's declared attributes, requesting a file the server would serve to anyone who asked, matching a script's signature against a public vulnerability database. None of it involves crafting a payload, attempting to bypass a control, or confirming a finding is actually exploitable.

Concretely, this skill never:
- Attempts SQL injection, XSS, CSRF, or any other injection/exploit payload
- Attempts to bypass authentication or access data that isn't its own
- Systematically enumerates arbitrary paths looking for what exists (that's reconnaissance, a different activity from checking a short, well-known list of common accidental-exposure paths)
- Tries to confirm or escalate a finding once observed — a missing header or an exposed file gets reported and the check stops there

**Passing every check here is not evidence the site is secure.** If genuine security assurance is needed, that requires a qualified security professional or a dedicated engagement — this skill catches common, easy-to-fix misconfigurations, nothing more.

## Relationship to the other skills

Reuse `scenario-mapper`'s page list. Reuse `link-audit`'s lightweight-HTTP-check technique for the exposed-file checks, rather than re-deriving it.

## Core principles (and why)

**Delegate known-vulnerable-library detection to Retire.js — don't guess from memory.** Whether a specific library version has a known CVE is exactly the kind of fact that goes stale fast and that a specialized, regularly-updated tool (Retire.js, checked against current advisory sources) tracks far more reliably than guessing from training data. Same "use the right tool" reasoning as `accessibility-audit`'s use of axe-core.

**Check a short, well-known list of exposed-file patterns — this is not enumeration.** Whether `.env`, `.git/config`, or a common backup-file pattern is accidentally publicly served is a standard, narrow hygiene check most teams genuinely want. Systematically guessing at arbitrary paths to map out what exists on a server is a different activity and isn't this skill's job.

**Report and stop — never confirm exploitability.** If a cookie is missing `Secure`, or a source map is exposed, or a library has a known CVE, that's the finding. Confirming whether it's actually exploitable in this specific application is a different discipline with different tooling and different people who should own it — the same line `form-fuzzing` and `auth-session-audit` already draw, held just as firmly here.

**Severity here means "worth fixing," not "confirmed exploit impact."** Nothing in this skill confirms actual exploitability, so don't phrase findings as if a working exploit was demonstrated — "missing Secure flag on the session cookie" is accurate; "session hijacking vulnerability" overclaims what was actually checked.

## Checks

**Transport & headers (per page):**
- HTTP → HTTPS redirect enforced
- Mixed content: any HTTP resources loaded on an HTTPS page
- Security headers present: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` (or a `frame-ancestors` CSP directive), `Strict-Transport-Security`

**Cookies (per page):**
- `Secure` flag on authentication/session cookies
- `HttpOnly` flag
- `SameSite` attribute set

**Exposed files (site-level, narrow list only):**
- `.env`
- `.git/config` or `.git/HEAD`
- Common backup-file patterns (`.bak`, `.sql`, a trailing `~`)
- Publicly accessible JS/CSS source maps (`.js.map`, `.css.map`)

**Known-vulnerable libraries:**
- Run Retire.js against scripts discovered while crawling, flagging any with a known CVE at their detected version

## Workflow

1. Get the page list from `scenario-mapper`.
2. For each page: check protocol/redirect behavior, mixed content, response headers, and cookie flags.
3. At the site level: check the narrow exposed-file list via lightweight HTTP requests.
4. Run Retire.js against discovered scripts.
5. Write the CSV, then a short chat summary — restating the hygiene-not-audit boundary, not just stating it once at the start.

## CSV columns

| Column | Contents |
|---|---|
| `id` | Sequential, e.g. `H001` |
| `page_or_scope` | Page checked, or "Site-level" for file/header checks that aren't per-page |
| `check` | e.g. "Cookie flags," "Security headers," "Exposed file," "Vulnerable library" |
| `finding` | What's missing or present that shouldn't be |
| `severity` | Worth-fixing priority — not a claim about confirmed exploit impact |
| `notes` | e.g. CVE reference for a flagged library, or "recommend security review" for anything ambiguous |

## After writing the CSV

Give a short summary: pages/scope checked, findings by category, and close by restating plainly that this is a hygiene pass — not a security audit, and not something that should be read as clearing the site for security purposes.

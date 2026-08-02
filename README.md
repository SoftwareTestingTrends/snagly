# Snagly — Web QA testing skills for AI coding agents

**Snagly** is a set of 30 skills that turn **GitHub Copilot, Claude Code, or any of 70+ other agents** into a QA engineer for web applications — browser flows, accessibility, visual regression, performance, SEO, i18n, bug triage — driven by Playwright (via the Playwright MCP server or `@playwright/cli`), plus a small Jira family for turning findings into tracked tickets. Each skill has a single, well-defined job; they're designed to hand off to each other rather than duplicate work.

A [Software Testing Trends](https://softwaretestingtrends.com) project — *learn smarter, test better*.

## Getting started

### Prerequisites

**Core — needed by every browser-driving skill:**

- An AI coding agent that supports skills — [GitHub Copilot](https://github.com/features/copilot), [Claude Code](https://claude.com/claude-code), Cursor, Codex, OpenCode, and others
- Node.js (a current LTS release)
- Browser automation, either of:
  - **`@playwright/cli`**: `npm install -g @playwright/cli@latest`, then `playwright-cli install --skills` to add its own skill (Snagly does not bundle a copy, so you always get the current upstream version)
  - or the **Playwright MCP server**, configured however your agent takes MCP servers (on Claude Code: `claude mcp add playwright -- npx @playwright/mcp@latest`)
- Browser binaries: `playwright-cli install-browser chromium` — add `firefox` and `webkit` if you'll use `cross-browser-matrix`

**Fetched on demand** — nothing to pre-install, but runs need network access to npm the first time: axe-core (`accessibility-audit`), web-vitals (`performance-audit`), pixelmatch (`visual-regression`), Retire.js (`security-hygiene`), `@playwright/test` (`e2e-codegen`, `visual-regression`).

**Optional, only for specific skills:**

| You want to use | You also need |
|---|---|
| `figma-compare` | The **Figma MCP server**. Easiest: the remote server — `claude mcp add --transport http figma https://mcp.figma.com/mcp`, then sign in to your Figma account in the browser when prompted. (Alternative: the local server inside the Figma desktop app, with the design file open.) |
| `jira-connector`, `bug-analyzer`, `bug-creator` | Python 3.10+ (standard library only — no pip installs) and a Jira Cloud API token (see Credentials below) |
| `email-verification` | A test-readable inbox: either a mail tool/MCP connected to a tester-owned inbox (using plus-aliases like `you+test1@…`), or a disposable-inbox service the target app actually delivers to |

Everything else runs with just the core setup.

### Install the skills

**Any agent — via [skills.sh](https://www.skills.sh)** (GitHub Copilot, Cursor, Codex, OpenCode, Claude Code, and 70+ more):

```
npx skills add softwaretestingtrends/snagly --all
```

It detects your agent and installs into the directory it reads. Note this **copies** the files, so re-run the command to pick up new releases.

**Claude Code — as a plugin** (skills namespaced as `snagly:<skill>`, and updates handled for you):

```
/plugin marketplace add softwaretestingtrends/snagly
/plugin install snagly@snagly
```

**Or from a clone** — clone this repo, then add it as a local marketplace (`/plugin marketplace add /path/to/snagly`) and install as above. (The skills live in `skills/`, which the plugin system reads; if you prefer plain project skills, symlink or copy `skills/` into your agent's skills directory.)

Either way, run the toolkit from the project directory where you want its working files — target profiles are read from `targets/`, and run artifacts land in `runs/`, `bugs/`, `snapshots/`, `scenarios/`, `test-cases/` relative to where you work.

### Updating

New releases are published as version bumps to this repo.

**If you installed via skills.sh**, re-run the install to pick them up — it copies files, so nothing updates on its own:

```
npx skills add softwaretestingtrends/snagly --all
```

**If you installed the Claude Code plugin**, no reinstall is needed:

```
/plugin marketplace update snagly    # fetch the latest release
/reload-plugins                      # apply it in the current session
```

(Or just start a new session after the marketplace update.) Updates are **not automatic by default** for community marketplaces like this one — to opt in, open `/plugin` → Marketplaces → `snagly` → enable auto-update, and Claude Code will fetch new versions in the background and prompt you to reload. Each release is also tagged on GitHub (`v1.x.x`) if you need to see what changed or point at an older version.

**Credentials** — never committed; `.gitignore` already excludes `.env`. Create a `.env` at the repo root:

```bash
# Target app login (referenced by targets/<profile>.yaml)
USER='you@example.com'
PASSWORD='...'

# Jira Cloud (only needed for jira-connector / bug-analyzer / bug-creator)
JIRA_URL=https://your-org.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=...        # from id.atlassian.com/manage-profile/security/api-tokens
JIRA_PROJECT_KEY=PROJ     # default project for created issues (optional)
```

The Jira vars can also live in `~/.jira-connector.env` (chmod 600) to be shared across repos — see `jira-connector`'s SKILL.md for the full resolution order.

**Getting app credentials into a run** — nothing auto-loads `.env`, and many agents refuse to read `.env` files at all as a secret-exfiltration guard. The reliable (and safer) pattern is to export the variables in the shell you launch the agent from:

```bash
export USER='you@example.com' PASSWORD='...'      # or: source .env
```

Commands then reference `"$PASSWORD"`, so the value never enters the agent's context or your terminal transcript. The Jira connector is the exception — its Python client reads `.env` directly.

**Target profiles** — `targets/*.yaml` describes each app under test: base URL, where credentials come from, the login flow, which tenant is safe to mutate, known console noise to not re-flag, and hard-won app-specific notes. Skills read the profile before touching a site, and each run makes the next one cheaper by updating it.

Set one up in whichever way suits you — **you don't have to write it by hand**:

- **Easiest — let the toolkit write it.** In your project folder, ask: *"Explore https://yoursite.com and write a target profile for it."* `scenario-mapper` explores, then writes `targets/<name>.yaml` from its bundled template along with a scenario list.
- **From the template.** If you cloned this repo, copy `targets/example.yaml`. If you installed the plugin or used skills.sh, grab it directly:
  ```bash
  mkdir -p targets
  curl -o targets/example.yaml https://raw.githubusercontent.com/softwaretestingtrends/snagly/main/targets/example.yaml
  ```

Two rules the template explains: credentials are env-var **names**, never values, and on a production target you **omit `safe_to_mutate` entirely** — its absence is what makes `crud-tester` stop and ask instead of mutating live data. Keep your real profiles gitignored; they describe your internal environments.

**Conventions**

- All Jira writes are **dry-run by default** — nothing is created/commented/transitioned without `--apply` after you've seen the payload.
- Skills that mutate app data only touch the tenant named in the profile's `tenants.safe_to_mutate`, mark every created record with a `QA-CRUD-<run-id>` style marker, and clean up after themselves.
- Run artifacts land in `runs/`, bug evidence bundles in `bugs/`, screenshot baselines in `snapshots/`, scenario CSVs in `scenarios/`, test-case documents in `test-cases/` — all gitignored local history.

**First run** — just ask: *"What can you test here?"* — the `start-testing` skill routes from there.

## How they fit together

```
ROUTE               start-testing is the front door: routes a vague "test this" to the right
                    skill below, and checks prerequisites before handing off
      ↓
DISCOVER            scenario-mapper explores a site, outputs a CSV of candidate scenarios
      ↓
DETAIL              test-case-writer expands a scenario into a full spec (preconditions,
                    test data, per-step expected results) — status: Inferred
      ↓
EXECUTE             flow-runner runs the spec against a real browser, asserts outcomes,
                    flips the spec's status to Verified on a passing run
                    (crud-tester is the variant that's allowed to mutate: full
                    create → edit → delete lifecycles, self-contained and cleaned up)
      ↓
CODIFY              e2e-codegen turns a Verified spec into a permanent @playwright/test file

DEFECT LOOP         bug-triage investigates any failure (minimal repro, reproducibility, root
                    cause) → bug-creator files it in Jira (deduped, evidence attached) →
                    fix-verifier re-runs the repro on later builds and updates the ledger
                    (bug-analyzer works the other direction: existing ticket → ranked causes)

Around that core loop:
  - network-assertion / cross-browser-matrix / auth-session-audit / form-fuzzing /
    email-verification each execute a specific kind of check, usually against a
    flow-runner or scenario-mapper scenario
  - accessibility-audit / performance-audit / seo-audit / i18n-audit / link-audit /
    security-hygiene run as independent, site-wide sweeps
  - visual-snapshot captures full-page screenshots; visual-regression diffs two of those
    runs; figma-compare checks the built UI against its Figma design
  - user-guide turns a verified flow into an end-user how-to; qa-onboarding writes the
    QA-teammate version
  - test-plan sets strategy and cadence for all of the above; report-generator synthesizes
    whatever's accumulated into one readable summary
```

---

## Front Door

### `start-testing`
Routes a vague testing request to the right skill with as few questions as the request actually requires — often zero. Knows every skill's prerequisites (baselines, verified flows, safe tenants) and catches missing ones before handing off.
> "Can you test this site?"
> "What can you check here?"

---

## Discovery & Strategy

### `scenario-mapper`
Explores a site with a real browser and outputs a CSV of candidate test scenarios — either a small **sanity** set (8–20 scenarios, "would this obviously break") or a **comprehensive** suite (happy path + negative/edge cases per flow).
> "Explore mysite.com and find sanity testing scenarios"
> "Build a full test suite for our checkout flow"

### `test-case-writer`
Expands a terse scenario into a detailed, persistent test-case document — preconditions, test data, numbered steps each with its own expected result. Sits between the terse CSV and a live execution run.
> "Write a detailed test case for the login scenario"
> "Turn scenario S003 into a full test case doc"

### `test-plan`
The strategy document above everything else: scope, risk-based priorities, cadence for each of the other skills, release exit criteria, environment/data conventions, and a coverage ledger of what's automated vs. manual.
> "Write a test plan for our site"
> "What should our testing strategy be before the next release?"

### `qa-onboarding`
Synthesizes an onboarding document for a new QA teammate — the site's testing landscape (from `test-plan`), a curated tour of which skill to reach for and when, known trouble spots from recent bug-triage/report history, and a suggested first-week path. Uses this team's testing vocabulary freely — a different audience from `user-guide`, which is for end users.
> "Write an onboarding guide for a new QA hire"
> "Help me get a new teammate up to speed on our testing setup"

---

## Core Execution

### `flow-runner`
Drives a browser through a defined scenario step by step, asserting the actual expected outcome at each step (not just that a click happened), and captures a full evidence bundle the moment anything fails. Deliberately stops before real side effects.
> "Test the checkout flow end to end"
> "Run test case TC-004"

### `crud-tester`
The skill that's **allowed to mutate** — tests full data lifecycles (create → verify → edit → verify → delete → verify-gone) under strict self-containment rules: safe tenant only, run-marked records, mutates nothing it didn't create, delete-as-test cleanup.
> "Test that creating and editing records actually persists"
> "Run the CRUD suite"

### `e2e-codegen`
Converts a scenario `flow-runner` has already verified into a permanent, runnable `@playwright/test` spec file — role-based locators, real assertions, no fixed-time waits, dynamic test data. Runs the generated file before handing it over.
> "Turn the verified login scenario into a real Playwright test"
> "Generate test code for TC-004"

### `bug-triage`
Reproduces a reported or suspected bug, determines how reliably it reproduces, captures a full evidence bundle, and forms a root-cause hypothesis grounded only in what was actually observed.
> "Reproduce this bug: the checkout button doesn't work"
> "Is this actually broken, or is it flaky?"

### `fix-verifier`
Re-verifies previously-found defects against the current build: locates each defect's recorded minimal repro, re-runs it at the original rigor, and delivers a per-defect verdict — FIXED, STILL BROKEN, REGRESSED, or BLOCKED — updating the bug bundle and defect ledger in place.
> "Is D4 fixed on the new build?"
> "Re-check all the open bugs after the deploy"

---

## Behavioral & Interaction Checks

### `network-assertion`
Mocks network responses to test error/loading/empty states a live backend won't reliably produce on demand, and asserts on real traffic (status codes, duplicate calls, payload shape).
> "Test what happens if the payment API returns a 500"
> "Check that no duplicate analytics calls fire during checkout"

### `cross-browser-matrix`
Runs an existing scenario across browser engines (Chromium/Firefox/WebKit) and/or viewport sizes, scoped to whichever axis is actually needed, normalized into one comparison table.
> "Does checkout work on Firefox and Safari?"
> "Check this page on mobile"

### `auth-session-audit`
Tests session/auth lifecycle edge cases: expiry mid-flow, concurrent sessions across simulated devices, logout propagation across tabs, remember-me persistence, password reset token reuse, back-button caching.
> "Test what happens when a session expires mid-checkout"
> "Check our auth edge cases — does logout work across tabs?"

### `form-fuzzing`
Tests form fields with realistic edge-case inputs — empty, boundary-length, unicode, malformed formats, real-but-uncommon characters like apostrophes in names — to verify graceful handling. Explicitly a UX/robustness check, not security testing.
> "Test our signup form with edge-case inputs"
> "Fuzz the checkout form fields"

### `email-verification`
Verifies the email half of a flow end to end: triggers it in the browser, confirms the email arrives in a test-controlled inbox (plus-alias via a connected mail tool, or a disposable inbox), checks sender/subject/content against what the flow promised, inspects link hosts (catching staging→prod link bugs), and clicks through to complete the loop.
> "Verify the password reset email arrives with a working link"
> "Does the invite email actually get sent?"

---

## Site-Wide Audits

### `accessibility-audit`
Runs an automated axe-core scan plus a defined set of manual checks (keyboard operability, focus order, alt-text quality, dynamic-content announcements) and reports findings by WCAG criterion and impact level.
> "Run an accessibility audit on our site"
> "Is this page WCAG compliant?"

### `performance-audit`
Measures Core Web Vitals (LCP, INP, CLS) via the `web-vitals` library during real page interactions, rated against Google's published thresholds. Explicitly lab data, not the field data Google actually grades against.
> "Check our Core Web Vitals"
> "Is this page slow?"

### `seo-audit`
Checks technical/structural SEO: titles, meta descriptions, canonical tags, meta robots (catching accidental noindex), structured data validity, robots.txt/sitemap sanity. Not keyword strategy or ranking prediction.
> "Audit our page metadata"
> "Check our robots.txt and sitemap for issues"

### `i18n-audit`
Checks translation coverage per locale, leaked untranslated template keys, RTL layout correctness, text-overflow from translation expansion, locale persistence, and hreflang tag correctness.
> "Check our translations and RTL layout"
> "Test locale switching on the site"

### `link-audit`
Exhaustively crawls the site (deeper than `scenario-mapper`'s curated pass) to find broken links, broken images, redirect loops, and long redirect chains.
> "Crawl our site for broken links"
> "Find any 404s on the site"

### `security-hygiene`
Checks basic security hygiene — HTTPS enforcement, mixed content, cookie security flags, common security headers, a narrow check for commonly-exposed accidental files (`.env`, `.git/config`, source maps), and known-vulnerable JS libraries via Retire.js. Explicitly hygiene, not a security audit or penetration test — no injection payloads, no exploit attempts, no confirming exploitability.
> "Check our basic security hygiene"
> "Are our cookies missing any security flags?"

---

## Visual & Design

### `visual-snapshot`
Navigates main pages, captures full-page screenshots under consistent conditions, and compiles them into a single HTML gallery for quick human review.
> "Take screenshots of all our main pages"
> "Show me what every page looks like right now"

### `visual-regression`
Diffs two `visual-snapshot` runs (a baseline and a current one) using pixel comparison, masking known-dynamic regions, to flag unintended visual changes for human review.
> "Check for visual regressions since the last deploy"
> "Did this change break how anything looks?"

### `figma-compare`
Compares a Figma design against the live implementation — field-by-field structure, labels, required markers, dropdown option lists (extracted as text from the design, not eyeballed), conditional states, and visual styling. Judgment work with evidence, not pixel math; distinguishes "defect" from "stale mock" from "per-tenant config."
> "Compare the Figma design against the signup form"
> "Does this screen match the mock?"

---

## Documentation

### `user-guide`
Generates an end-user-facing how-to guide from a verified flow — a screenshot per step with the target element visually highlighted, and a plain-language instruction using the interface's own button/field labels. Written for end users, not QA; no testing jargon.
> "Write a user guide for checkout"
> "Create a how-to doc for signing up"

---

## Reporting

### `report-generator`
Synthesizes outputs from any of the other skills — potentially from several sessions across a testing cycle — into one prioritized, human-readable report. Doesn't drive a browser itself; reads what the others already produced.
> "Summarize everything we found this week"
> "Give me a report I can send to the team"

---

## Jira & Defect Tracking

All Jira writes are dry-run until `--apply`.

### `jira-connector`
The shared building block: read/write Jira Cloud via REST v3 (issue fetch, JQL search, create, comment, attach, link, transition) through a stdlib-only Python client. The higher-level skills shell out to this rather than re-implementing auth and ADF handling.
> "Get PROJ-123"
> "Find open bugs assigned to me"

### `bug-analyzer`
Turns an existing bug report/ticket into ranked root-cause hypotheses, each tied to the code, commit, or log line that supports it — investigative leads with confidence levels, not verdicts. Best run inside the affected code repo.
> "Analyze PROJ-123"
> "Why is this stack trace happening?"

### `bug-creator`
Turns a confirmed finding (bug-triage bundle, drafted ticket, fix-verifier regression) into a filed Jira Bug: dedupes against existing tickets first, composes an actionable description, attaches evidence, links related issues, and writes the new key back into the local ledger.
> "File this bug in Jira"
> "Create a ticket for D4"

---

## Shared rules (not a check)

`browser-safety` carries the credential, snapshot, untrusted-content, and headed-mode rules that every browser-driving skill above applies — it's a shared rule set, not something to invoke by name for testing. Each rule exists because something went wrong in a real run: filling a password leaks it into the transcript (the CLI echoes the resolved value), accessibility snapshots render credential fields as text, and page content is written by people outside your trust boundary.

The browser itself is driven by `@playwright/cli` or the Playwright MCP server. Snagly deliberately does **not** bundle a copy of the CLI's own skill — run `playwright-cli install --skills` to get it from upstream, so it stays current and you keep its improvements.

---

## Design notes

A few things threaded through the whole toolkit, worth knowing before relying on it:

- **Every skill is explicit about what it didn't cover**, rather than implying completeness — scope, gaps, and confidence level are always stated, not assumed.
- **Mocked/lab/inferred results are never presented with the same confidence as verified/real ones** — a mocked network response, a lab performance measurement, and an unverified test-case document are all labeled as such.
- **Automated tools are used where they exist** (axe-core for accessibility, `web-vitals` for performance, `pixelmatch` for visual diffing) rather than reasoning about the same thing from scratch.
- **Findings close their loop** — a defect gets an ID and evidence bundle (bug-triage), becomes a tracked ticket (bug-creator), and is re-verified against later builds (fix-verifier), so nothing lives only in a chat transcript.
- **Two topics were deliberately kept out of scope**: general visual-design opinion (aesthetic judgment isn't checkable the way everything else here is) and anything resembling security penetration testing (form-fuzzing, auth-session-audit, and security-hygiene all draw a hard line against injection payloads, exploit attempts, or probing undocumented limits).

## Security model

Automated scanners rate some of these skills medium/high risk. That's a capability rating, not a finding — here is exactly what those capabilities are, so you can review before installing:

- **What executes things**: the browser skills shell out to `@playwright/cli` (installed by you, not bundled here) or call Playwright MCP tools; the audit skills fetch standard npm tools at run time (axe-core, web-vitals, pixelmatch, Retire.js); the Jira family runs the bundled `jira_client.py` (Python standard library only — read the script, it's one file). Everything runs under your agent's normal tool-permission prompts; nothing executes outside them.
- **Credentials** are read only from environment variables / gitignored `.env` files, are never written into skill files or tickets, and the skills are instructed never to echo them.
- **Writes are gated**: every Jira write is dry-run until `--apply`; data mutations are restricted to a tenant you explicitly name as safe, with run-marked records and cleanup-as-test.
- **Hard lines**: no skill uses injection payloads, exploit attempts, or authentication bypass — `form-fuzzing`, `auth-session-audit`, and `security-hygiene` draw this line explicitly in their instructions.

Skills are plain markdown — audit them yourself before use, as you should for any skill from any source.

## License

[MIT](LICENSE)

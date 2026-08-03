---
name: bug-creator
description: Use when a defect needs to become a Jira ticket — takes a finding from any source (a bug-triage bundle, a drafted ticket markdown, a figma-compare/fix-verifier finding, or a defect described in conversation), checks Jira for duplicates first, then files a well-structured Bug with evidence attached and links back, via jira-connector (dry-run first, always). Trigger on "file this bug", "create a ticket for this", "raise this in Jira", "log a defect for D4", or when a testing skill ends with a confirmed defect the user wants tracked. Distinct from bug-analyzer (which investigates causes of an existing ticket) and bug-triage (which establishes that something IS a bug — unverified findings route there first, because a filed bug that doesn't reproduce burns the team's trust in every future report).
compatibility: Needs jira-connector (same auth setup — env vars, ~/.jira-connector.env, or repo .env). Reads local evidence bundles (bugs/, runs/) when present. All Jira writes dry-run by default; --apply only after the user nods.
allowed-tools: Read Grep Glob Write Bash(python3:*)
metadata:
  version: "1.0"
---

# Bug Creator

Turn a confirmed defect into a Jira Bug that a developer can act on without coming back
to ask questions — deduplicated against what's already filed, evidence attached, linked to
its story, and written in the project's own vocabulary.

Two failure modes this skill exists to avoid: **duplicate tickets** (which fragment the
discussion and waste a triager's time) and **unactionable tickets** (no build, no steps,
no evidence — which bounce back to the reporter). Everything below serves one or the other.

## Inputs

Accept a defect from any of:
- A **local bug bundle** (`bugs/<ID>-<slug>/report.md` + evidence files) from `bug-triage`
  or `fix-verifier` — the richest source; most fields map directly.
- A **drafted ticket markdown** (e.g. from a design-comparison run) — already structured; verify it
  names a build and has evidence paths.
- A **finding in conversation or a run report** — gather what's missing before filing (see checklist).
- A **REGRESSED verdict** from `fix-verifier` — file as a new bug linked to the original
  ticket if one exists, not a comment on a closed one (closed-ticket comments go unread).

**Verify before filing.** If the defect hasn't been reproduced — it came from a single automation
run, a visual impression, or secondhand report — route through `bug-triage` first.
One withdrawn false positive costs more credibility than ten good tickets earn.

## Method

### 1. Dedupe against Jira — always, before composing anything

Search for the defect's distinctive signals (exact error strings, endpoint/operation names,
component + symptom words) scoped to the project, recent-first:

```bash
JIRA=$(ls "${CLAUDE_PROJECT_DIR:-.}"/skills/jira-connector/scripts/jira_client.py \
          "${CLAUDE_PROJECT_DIR:-.}"/.agents/skills/jira-connector/scripts/jira_client.py \
          "${CLAUDE_PROJECT_DIR:-.}"/.github/skills/jira-connector/scripts/jira_client.py \
          "${CLAUDE_PROJECT_DIR:-.}"/.claude/skills/jira-connector/scripts/jira_client.py \
          "$HOME"/.agents/skills/jira-connector/scripts/jira_client.py \
          "$HOME"/.claude/skills/jira-connector/scripts/jira_client.py \
          "$HOME"/.claude/plugins/cache/*/snagly/*/skills/jira-connector/scripts/jira_client.py \
          2>/dev/null | head -1)
python3 "$JIRA" whoami                          # fresh session? verify auth first
python3 "$JIRA" search --jql 'project = PROJ AND issuetype = Bug AND text ~ "policy holder" ORDER BY created DESC' --max 15
```

Run two or three searches with different signals — one JQL phrasing misses siblings. Present
any plausible matches to the user with keys and one-line summaries. Outcomes:
- **Same defect, open** → don't file; offer to `comment` fresh evidence onto it instead.
- **Same defect, closed as fixed** → this is a regression; file new, `--link "Relates:<old>"`
  (and say "regression of <old>" in the summary).
- **Adjacent but different** → file new with a `Relates` link.
- **Nothing** → file new.

### 2. Compose the ticket

**Summary line**: `[component] symptom under condition` — specific enough to be findable by
the same dedupe search you just ran, e.g. `[Portal] User Profile: switching Country clears
Phone and address without warning`. Not "Form issue".

**Description** — an **ADF JSON document** filed via `--adf-file`. Not `--body-file`: plain
text becomes flat paragraphs, and wiki markup like `h3.` renders as literal text — that shape
has been rejected by reviewers. The document is six `heading` (level 3) nodes, each followed
by its content nodes:

| Heading | Content nodes |
|---|---|
| Summary | paragraph(s): what breaks, who hits it, why it matters |
| Environment | bulletList: URL, build/version, browser, tenant/config |
| Steps to reproduce | orderedList from login, incl. preconditions (test data, flags) |
| Expected / Actual | two paragraphs, each opening with a bold `Expected:` / `Actual:` label |
| Evidence | bulletList: attachment filenames + what each shows (by filename only — inline media embeds can 400 on Jira Cloud; see jira-connector's gotchas) |
| Notes | bulletList: reproducibility (n/n trials), severity rationale, suspected scope, source run |

Node shapes (compose the six sections from these):

```json
{"type":"heading","attrs":{"level":3},"content":[{"type":"text","text":"Summary"}]}
{"type":"paragraph","content":[{"type":"text","text":"Expected: ","marks":[{"type":"strong"}]},{"type":"text","text":"…"}]}
{"type":"orderedList","content":[{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"…"}]}]}]}
{"type":"bulletList","content":[{"type":"listItem","content":[…]}]}
```

Mark ids/values (`Study 2fc9…`, URLs, field values) with `"marks":[{"type":"code"}]`. Wrap it
all as `{"type":"doc","version":1,"content":[…]}`, write to a file, and check it parses
(`python3 -m json.tool`) before the dry-run.

**Required custom fields** — many projects reject bare Bugs (`400 … is required`) because
they require org-specific custom fields (a release, a team area, reproducibility, severity).
Discover yours once and record them in jira-connector's
[field-reference.md](../jira-connector/references/field-reference.md); pass them via
`--fields-json`. Before picking values, `get` one or two comparable recent Bugs and mirror
theirs — precedent beats guessing (allowed values drift;
`GET /rest/api/3/issue/createmeta/<PROJECT>/issuetypes/<typeId>` is the source of truth).
An illustrative example of what such a payload looks like:

```json
{
  "customfield_1xxxx": [{"value": "Release 2.6"}],
  "customfield_1xxxx": [{"value": "SW - Web"}],
  "customfield_1xxxx": {"value": "Always"},
  "customfield_1xxxx": {"value": "3 - Medium"}
}
```

**Severity/priority — set it on the create, every time.** Map the finding's severity to the
project's priority scheme and pass `--priority` on the `create` itself. Omitting it doesn't
leave the field blank; Jira silently defaults it (usually to Medium), so a Critical defect
lands looking routine and the triage queue misleads everyone who reads it. Priority schemes
are project-local, so if you're genuinely torn between two levels, ask — but never skip the
flag to avoid deciding.

If a ticket does get filed with the wrong value, fix it rather than leaving a note for a
human: `edit <KEY> --priority <name>` (dry-run first, like every other write).

**Privacy pass before anything leaves the machine**: staging screenshots and logs carry
real-looking emails, names, tokens. Mask or crop them, and never paste credential
values from `.env`/localStorage into a ticket.

### 3. File it — dry-run, nod, apply

```bash
python3 "$JIRA" create --type Bug --summary "..." --adf-file bug-adf.json \
  --fields-json bug-fields.json \
  --labels qa,figma-compare --link "Relates:PROJ-100"           # dry-run: shows payload
# user reviews → re-run with --apply
python3 "$JIRA" attach PROJ-NEW --file evidence1.png --file console.log --apply
```

Show the user the draft **as readable markdown in chat** (not raw ADF JSON or the dry-run
payload dump) and get an explicit nod before `--apply` — repo-wide convention, never bypass
it. Attach the evidence files after create; reference them by filename in the description
(already written that way in step 2). Give evidence files descriptive names before attaching
(`profile-country-clears-phone.png`, not `1.png`).

### 4. Close the loop locally

Write the new Jira key back into the source artifact — the bug bundle's `report.md`
header, the run report's finding row, the defect ledger — so local IDs (D-numbers,
E-numbers) map to Jira keys. This is what lets `fix-verifier` transition the
ticket when it later verifies the fix, and stops the same finding being re-filed by the
next run that trips over it.

## Presenting results

- Dry-run stage: show summary line, description, labels, links, and attachment list —
  compactly, not as raw JSON.
- After apply: report the new key + URL, the attachments uploaded, and which local files
  were updated with the key.
- If dedupe found matches and the user chose not to file: record that decision in the
  source artifact too ("not filed — duplicate of PROJ-xxxx"), for the same reason.

## See also

- [`jira-connector`](../jira-connector/SKILL.md) — owns the API; extend it there if a field
  or JQL capability is missing, don't inline REST calls here.
- [`bug-analyzer`](../bug-analyzer/SKILL.md) — the inverse direction: existing ticket → root-cause leads.
- `bug-triage` / `fix-verifier` (project skills) — produce the confirmed,
  evidence-backed findings this skill files.

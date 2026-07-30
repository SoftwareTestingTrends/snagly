---
name: jira-connector
description: Use when the user wants to read from or write to Jira Cloud — fetch an issue, run a JQL search, list projects/fields/transitions, or create issues, comments, and status transitions. The reusable Jira building block that higher-level QE skills (bug-analyzer, bug-creator) call. e.g. "get PROJ-123", "find open bugs assigned to me", "create a bug in PROJ".
compatibility: Requires Python 3.10+ and network access to your Jira Cloud site. Auth (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY) from the environment, ~/.jira-connector.env, $JIRA_ENV_FILE, --env-file, or a repo .env — so it runs from any repo, not just this one. Standard library only — no pip install. All write commands default to dry-run; pass --apply to execute.
allowed-tools: Bash(python3:*) Read Write
metadata:
  version: "1.0"
---

# Jira Connector

Read and write Jira Cloud issues through the REST API v3, cleanly and reproducibly. This is
a **connector building block** — a thin, shared layer other QE skills reuse instead of each
re-implementing auth, JQL search, and Atlassian Document Format (ADF).

**Reads are safe and run immediately. Writes (`create`, `comment`, `transition`) default to
dry-run — nothing changes without `--apply`.**

## Gotchas (read first — these defy reasonable assumptions)

- **Bodies are ADF, not text.** Jira Cloud v3 descriptions/comments are Atlassian Document
  Format (JSON), not plain strings. Sending a raw string is a 400. The script wraps plain
  text into ADF for you (`--description` / `--body`) — pass text, not JSON. For **rich**
  descriptions (headings, checklists/`taskList`, panels) that plain-text wrapping can't
  express, author the ADF yourself and pass it with `create --adf-file <doc.json>`.
- **Transitions are project/workflow-specific, by ID.** You can't set `status` directly and
  the transition name (e.g. "In Progress") is not universal. Always list what's actually
  available on the issue first (`transitions <KEY>`), then transition. The script does this
  lookup for you and matches on transition name *or* destination status.
- **Custom fields are `customfield_NNNNN`, and required ones vary per project.** A create can
  400 with "field is required" for something not obvious (e.g. a custom "Team" or "Sprint").
  Discover IDs with `fields --grep <name>`; see [references/field-reference.md](references/field-reference.md).
- **JQL search uses the token-paginated `/search/jql` endpoint** (the old `/search` is
  deprecated). Pages carry `nextPageToken` / `isLast`, not `startAt` — the script follows it.
- **Auth is email + API *token*, not your password**, base64'd as HTTP Basic. A 401 almost
  always means a stale/typo'd token or wrong email — not a permissions problem (that's 403).
- **Issues may carry personal data.** Mask emails and personal identifiers when presenting; never
  echo the API token. `.env` is gitignored — keep it that way.
- **Attachments are multipart, not JSON, and need `X-Atlassian-Token: no-check`.** The `attach`
  command handles both. Uploaded images render as thumbnails in the issue's Attachments panel.
- **Inline `media` embedding in comments can 400 on Jira Cloud.** Referencing an attachment
  `id` from a `media` node in a `comment --adf-file` doc (`{"type":"media","attrs":{"type":"file",
  "id":"<attachmentId>"}}`) is rejected with **HTTP 400 `ATTACHMENT_VALIDATION_ERROR`** — the
  endpoint wants a media-services id, not the issue attachment id (verified on one Jira Cloud
  site). So `attach` the files and **reference them by filename** in the comment text; don't
  try to embed.

## Setup — one time

**Locate the script** (works whether this skill runs from a clone of this repo, as a
**personal skill** under `~/.claude/skills/`, or as part of the installed **snagly
plugin**). Run this once per shell; every example below uses `$JIRA`:

```bash
JIRA=$(ls "${CLAUDE_PROJECT_DIR:-.}"/skills/jira-connector/scripts/jira_client.py \
          "${CLAUDE_PROJECT_DIR:-.}"/.claude/skills/jira-connector/scripts/jira_client.py \
          "$HOME"/.claude/skills/jira-connector/scripts/jira_client.py \
          "$HOME"/.claude/plugins/cache/*/snagly/*/skills/jira-connector/scripts/jira_client.py \
          2>/dev/null | head -1)
```

**Provide credentials.** The four vars below are needed (`JIRA_PROJECT_KEY` optional). The
script never overrides variables already set in the environment; it resolves them in this
order (first hit wins): `--env-file` → `$JIRA_ENV_FILE` → `~/.jira-connector.env` → the
nearest `.env` walking up from the current directory. So:

- **Working inside this repo** — a gitignored `.env` at the repo root is found
  automatically. Nothing else to do.
- **Using the skill from any other repo** — put the creds where they're always found,
  independent of CWD. Either export them in your shell profile, or create a home file:
  ```bash
  cp .env ~/.jira-connector.env          # from this repo's checkout, one time
  chmod 600 ~/.jira-connector.env        # it holds a token — keep it private
  ```

```
JIRA_URL=https://your-org.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=<token from id.atlassian.com/manage-profile/security/api-tokens>
JIRA_PROJECT_KEY=PROJ          # default project for `create` (optional)
```

Verify everything works before anything else — a successful `whoami` prints your account and
confirms the base URL. Always run it first on a fresh session:

```bash
python3 "$JIRA" whoami
```

## Read commands (safe)

```bash
# (define $JIRA once per shell — see Setup)

# Fetch one issue (curated fields; description flattened from ADF to text)
python3 "$JIRA" get PROJ-123
python3 "$JIRA" get PROJ-123 --raw            # full raw JSON when you need every field
python3 "$JIRA" comments PROJ-123             # comments (NOT in `get` — often hold the real detail)

# JQL search (paginated; --max caps results)
python3 "$JIRA" search --jql 'project = PROJ AND status = "In Progress"' --max 50
python3 "$JIRA" search --jql 'assignee = currentUser() AND resolution = Unresolved'
# --fields adds columns: the standard set is projected under named keys; any EXTRA field
# (e.g. a customfield_NNNNN) is passed through under its own id, rendered generically.
python3 "$JIRA" search --jql 'filter = 14716' \
  --fields 'summary,status,issuetype,priority,assignee,updated,customfield_10316'

# Discovery
python3 "$JIRA" projects                       # accessible projects + keys
python3 "$JIRA" fields --grep "acceptance"     # find a custom field's customfield_ id
python3 "$JIRA" transitions PROJ-123           # valid status moves for THIS issue
```

For a JQL pattern library (recent bugs, unestimated stories, my open items, changed-since),
read [references/jql-cookbook.md](references/jql-cookbook.md).

## Write commands (dry-run by default — add `--apply` to execute)

Every write prints exactly what it would send, then stops. Review it, then re-run with
`--apply`. This is the repo-wide convention — do not bypass it.

```bash
# Create an issue (uses JIRA_PROJECT_KEY unless --project given)
python3 "$JIRA" create --type Bug --summary "Login 500 on empty password" \
  --description "Steps:\n1. ...\nExpected: ...\nActual: ..." --labels qa,regression
python3 "$JIRA" create --type Bug --summary "..." --body-file bug.txt --apply

# Create with a rich ADF description + custom fields + an issue link
python3 "$JIRA" create --type "Test Case - SQA" --summary "Verify X" \
  --adf-file desc.json \                 # raw ADF doc (headings, taskList, ...) used verbatim
  --fields-json fields.json \            # JSON object merged into fields (custom fields, parent, ...)
  --field customfield_10790="Release Testing" \  # simple string field (repeatable)
  --link "Relates:PROJ-42" --apply       # link the new issue outward (applied only with --apply)

# Create a sub-task (set the parent via --fields-json)
#   child.json = {"parent": {"key": "PROJ-100"}, "customfield_10493": <AC as ADF>, ...}
python3 "$JIRA" create --type "Subtask - Test Case - SQA" --summary "Area scenario" \
  --fields-json child.json

# Comment (plain text, or a rich ADF doc for embedded screenshots / tables / headings)
python3 "$JIRA" comment PROJ-123 --body "Verified fixed in build 42."
python3 "$JIRA" comment PROJ-123 --body-file review.md --apply
python3 "$JIRA" comment PROJ-123 --adf-file results.json --apply   # ADF verbatim (embed media, etc.)

# Attach file(s) — screenshots, logs, reports (multipart upload; dry-run by default)
python3 "$JIRA" attach PROJ-123 --file step5.png --file result.png          # dry-run: lists files
python3 "$JIRA" attach PROJ-123 --file step5.png --apply                     # returns attachment id(s)

# Link two existing issues
python3 "$JIRA" link --from PROJ-124 --to PROJ-100 --type Relates
python3 "$JIRA" link --from PROJ-124 --to PROJ-100 --type Blocks --apply

# Transition status (matches on transition name OR destination status)
python3 "$JIRA" transition PROJ-123 --to "In Review"
python3 "$JIRA" transition PROJ-123 --to Done --apply
```

Long or formatted bodies (a story review, a full bug report): write to a file and use
`--body-file` / `--description`-via-file rather than fighting shell escaping. For structured
content (checklists, headings), author an ADF doc and pass `--adf-file`. Arbitrary custom
fields and sub-task parents go through `--fields-json` (a merged JSON object); simple string
fields through repeatable `--field name=value`. `--fields-json`/`--field` override earlier
fields; `--adf-file` overrides `--description`/`--body-file`. Issue links (`--link TYPE:KEY`
on create, or the `link` command) are created only under `--apply`.

If a `create` fails with a required-field or field-not-on-screen 400, read
[references/field-reference.md](references/field-reference.md) for how to find the custom
field ID and pass it.

## Building higher-level skills on this connector

This connector is the plumbing; the task logic lives in separate skills that shell out to it.
Two ship in this toolkit:

- **bug-analyzer** — `get` the bug + trace → rank hypotheses (with evidence) → optionally `comment`.
- **bug-creator** — gather repro/expected/actual → `create` a well-structured Bug (dry-run first).

Others follow the same shape and are easy to add — e.g. a story reviewer (`get` the story →
evaluate clarity/completeness/testability → `comment` fixes back), a test-case generator
(`get` a story → derive ranked cases → `create` them with `--adf-file` + `--fields-json` +
`--link`), or a test-case executor (`get` a case → drive the app in a browser → `attach`
step screenshots → post the run as one `comment --adf-file`).

Keep those skills thin: they own the QE judgment; this skill owns the API. When a skill needs
a field or JQL this connector doesn't expose yet, extend `jira_client.py` here rather than
duplicating REST calls in the task skill.

## Presenting results

- **Reads:** summarize (key, summary, status, assignee); offer the raw JSON on request rather
  than dumping it. State the JQL/issue used.
- **Writes:** always show the dry-run payload and get a nod before `--apply`. After applying,
  report the new key/URL or the transition performed.
- **Privacy:** mask emails/personal identifiers unless asked for raw; never echo the API token.

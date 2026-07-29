# Field Reference — ADF, custom fields, and the error catalog

Read this when a `create` returns a 400, when you need a custom field's ID, or when a body
isn't rendering right. Covers what trips up Jira Cloud REST v3 writes.

## Atlassian Document Format (ADF)

Descriptions and comments are **ADF JSON**, not plain strings. The connector converts plain
text for you: `create --description`, `comment --body`, and their `--*-file` variants all take
plain text and are wrapped into ADF (blank line = new paragraph, single newline = hard break).

You almost never need to hand-write ADF. If you must send richer content (headings, bullet
lists, code blocks, panels), the minimal shape is:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    { "type": "heading", "attrs": { "level": 3 },
      "content": [ { "type": "text", "text": "Steps to reproduce" } ] },
    { "type": "bulletList", "content": [
      { "type": "listItem", "content": [
        { "type": "paragraph", "content": [ { "type": "text", "text": "Open the portal" } ] } ] } ] },
    { "type": "codeBlock", "attrs": { "language": "text" },
      "content": [ { "type": "text", "text": "HTTP 500" } ] }
  ]
}
```

To send hand-authored ADF, save the doc to a file and pass `create --adf-file <doc.json>`.
It is used verbatim as the description (the connector only validates the top-level
`{"type":"doc","version":1,"content":[...]}` shape), so you can send `taskList` checklists,
headings, panels, etc. `--adf-file` overrides `--description`/`--body-file`.

## Finding custom field IDs

Custom fields are `customfield_NNNNN`. Discover them:

```bash
# $JIRA as located in SKILL.md's Setup section
python3 "$JIRA" fields --grep "story points"   # -> customfield_10016 (varies per site)
python3 "$JIRA" fields --grep "acceptance"
python3 "$JIRA" fields --grep "sprint"
```

Common ones (IDs differ per site — always confirm with `fields`):

| Field | Typical id | Value shape on create |
|---|---|---|
| Story Points | `customfield_100xx` | number: `5` |
| Sprint | `customfield_100xx` | number (sprint id) or array of ids |
| Epic Link | `customfield_100xx` | string issue key: `"PROJ-100"` |
| Acceptance Criteria | `customfield_100xx` | ADF doc (like description) |

`create` covers `summary`, `description`, `type`, `labels`, `priority`, and `project` directly,
plus **arbitrary fields** without code changes:

- `--fields-json <file>` — a JSON object merged into `fields`. Use for ADF-valued fields
  (Acceptance Criteria, Preconditions), single-selects `{"value": "..."}`, multi-selects
  `[{"value": "..."}]`, and the sub-task **`parent`** (`{"parent": {"key": "PROJ-100"}}`).
- `--field name=value` (repeatable) — for simple string fields.
- `--link TYPE:KEY` (on create) / the `link` command — issue links (created only with `--apply`).

### Your site's field map (fill this in)

Custom field IDs and issue-type names are **per-site** — discover yours once with
`fields --grep <name>` (and the project's create screen for required fields), then record
them here so every future create doesn't re-derive them. An illustrative example of what a
filled-in map looks like:

| Field | id | Value shape |
|---|---|---|
| Test Case issue type | — | name `Test Case - QA` (per-project; check the project's issue types) |
| Preconditions | `customfield_1xxxx` | ADF doc (bullet list) |
| Acceptance Criteria | `customfield_1xxxx` | ADF doc |
| Testing Reason | `customfield_1xxxx` | select `{"value": "Release Testing 2.5"}` |
| Project Name | `customfield_1xxxx` | multi-select `[{"value": "Release 2.6"}]` |
| Team Area | `customfield_1xxxx` | multi-select `[{"value": "SW - QA"}]` |

## Error catalog

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` | Bad/stale token or wrong email | Regenerate the API token; confirm `JIRA_EMAIL`. Run `whoami`. |
| `403 Forbidden` | Account can't act on that project | Check project role/permissions with an admin. |
| `404 Not Found` | Wrong issue/project key or wrong site | Verify with `get` / `projects`; check `JIRA_URL`. |
| `400 ... field is required` | Project requires a field not sent (custom Team/Sprint, components) | `fields --grep` to find its id; add it to the create payload. |
| `400 ... 'description' ... Operation value must be an Atlassian Document` | Sent a raw string as ADF | Use `--description`/`--body` (auto-wrapped), not hand JSON. |
| `400 ... issuetype ... not valid` | Type name wrong for this project | Type names are per-project; check the project's issue types in the UI. |
| `400 ... transition ... invalid` | Transition not allowed from current status | List valid moves with `transitions <KEY>`; use one of those. |

## createmeta — when a project's required fields are unclear

Jira exposes the exact required/allowed fields per project + issue type via
`GET /rest/api/3/issue/createmeta`. The CLI doesn't wrap it yet; when a create keeps 400-ing
on required fields, that endpoint (or the project's create screen in the UI) is the source of
truth for what to send.

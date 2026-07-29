# JQL Cookbook

Ready-to-run JQL for the `search` command. Substitute your project key for `PROJ`.

```bash
# $JIRA as located in SKILL.md's Setup section
python3 "$JIRA" search --jql '<jql here>' --max 50
```

## By assignment / ownership

| Goal | JQL |
|---|---|
| My open items | `assignee = currentUser() AND resolution = Unresolved` |
| Unassigned bugs in project | `project = PROJ AND issuetype = Bug AND assignee IS EMPTY` |
| Reported by me | `reporter = currentUser() ORDER BY created DESC` |

## By status / workflow

| Goal | JQL |
|---|---|
| In progress | `project = PROJ AND status = "In Progress"` |
| Ready for QA | `project = PROJ AND status IN ("Ready for QA", "In Review")` |
| Done this week | `project = PROJ AND status = Done AND statusCategoryChangedDate >= -7d` |

## By type — QE-relevant

| Goal | JQL |
|---|---|
| Open bugs, newest first | `project = PROJ AND issuetype = Bug AND resolution = Unresolved ORDER BY created DESC` |
| Stories with no acceptance criteria described | `project = PROJ AND issuetype = Story AND description IS EMPTY` |
| Unestimated stories | `project = PROJ AND issuetype = Story AND "Story Points" IS EMPTY` |
| High/Highest priority open | `project = PROJ AND priority IN (High, Highest) AND resolution = Unresolved` |

## By time / change

| Goal | JQL |
|---|---|
| Created in last 24h | `project = PROJ AND created >= -1d` |
| Updated since a date | `project = PROJ AND updated >= "2026/07/01"` |
| Recently resolved | `project = PROJ AND resolutiondate >= -14d ORDER BY resolutiondate DESC` |

## By release / component

| Goal | JQL |
|---|---|
| Fixed in a version | `project = PROJ AND fixVersion = "1.4.0"` |
| In a component | `project = PROJ AND component = "Portal"` |
| Blocked | `project = PROJ AND status = Blocked` |

## Syntax notes

- Quote any value with spaces: `status = "In Progress"`.
- Custom fields can be referenced by display name in quotes (`"Story Points"`) or by
  `cf[NNNNN]`. If a name is ambiguous, use `cf[NNNNN]` — find the id with `fields --grep`.
- Relative dates: `-1d`, `-2w`, `-1M` (M = month; lowercase m = minute).
- `currentUser()` resolves to the authenticated account — handy for personal dashboards.
- Always end with `ORDER BY` for stable, useful ordering; default order is unspecified.

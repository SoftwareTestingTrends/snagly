# Tool mapping and flow patterns

## CLI vs MCP: what each step maps to

Both paths do the same conceptual thing — snapshot, act, wait, assert — they just differ in where the data lives (disk vs. your context).

| Step | @playwright/cli | Playwright MCP server tools |
|---|---|---|
| Get page state | writes an accessibility snapshot to disk; read the file when you need specifics | `browser_snapshot` returns the tree inline |
| Navigate | shell command to open a URL | `browser_navigate` |
| Click / type | shell command referencing an element ref from the last snapshot | `browser_click`, `browser_type` (take a ref from the last `browser_snapshot`) |
| Wait for state | shell command to wait for selector/text/network idle | `browser_wait_for` |
| Screenshot | writes PNG to disk | `browser_take_screenshot` (can also save to a path) |
| Trace | CLI has native tracing to a file | some MCP servers support `browser_start_tracing` / `browser_stop_tracing`-style tools; check your connected tool list |
| Console/network logs | written to disk or queryable via CLI | `browser_console_messages`, `browser_network_requests` |
| Auth/session reuse | CLI can save/load storage state to a file path | look for a `browser_*` tool that saves/loads storage state, or handle it via `browser_evaluate` against `localStorage`/cookies if not exposed directly |

The CLI's exact subcommands and flags vary by version — run `npx @playwright/cli --help` (and `--help` on individual subcommands) at the start of a session rather than assuming syntax from memory, since this tooling moves fast. Same idea for MCP: check your actual available tool list for exact names before you plan around them, since server versions add/rename tools.

## Common flow patterns

These are starting templates for the step-plan you write before opening the browser — adapt the expected outcomes to the actual app.

### Login
1. Navigate to login page → expect login form visible (username/email + password fields, submit button).
2. Fill credentials, submit → expect redirect away from the login URL, and some authenticated-only element visible (avatar, "Sign out," account nav).
3. Save `storageState` here if later steps in the same session need to be authenticated.

Watch for: apps that show a generic "welcome" state even on failed login (checking only for "not on /login anymore" is a false pass) — assert on something that specifically only appears when authenticated.

### Search
1. Enter a query → expect results to render (or an explicit "no results" state — both are valid, absence of results text alone doesn't mean the search failed).
2. Check result relevance loosely (do titles/snippets contain query terms, or is it clearly returning something unrelated).
3. If filters/sort exist, apply one → expect result set to change accordingly.

### Multi-step commit flow
The general shape: a user works through several steps to submit or commit something, and there's a final confirmed state at the end. Checkout is the most common instance, but the same pattern covers a hotel/flight booking, a job application, an account onboarding wizard, a subscription signup, an insurance quote flow — anything where the site accumulates state across steps before finalizing it.

1. Break the flow into its actual steps and give each one its own row in the report — a flow failing on step 4 of 6 is meaningfully different from failing on step 1, and lumping them together hides where it actually broke.
2. At each step, assert on the state that proves progression (step indicator advancing, URL changing, a confirmation of what was just entered) — not just "no error message is showing." Many multi-step forms silently fail validation and just re-render the same step; absence of an error is not the same as success.
3. For the final commit step (place order, submit application, confirm booking), assert on the actual confirmation artifact — an order/reference/confirmation number, a receipt, an explicit "submitted" state — not just a redirect, since some apps redirect to a generic dashboard regardless of outcome.
4. If the flow involves payment, use test/sandbox credentials only if the app exposes a test mode — never enter real payment data. If there's no test mode, verify only up to (not including) the final commit step, and say so in the report.
5. If the flow allows going back a step, check that previously entered data persists on return — a common real bug that's easy to check for and easy to miss.

### Content / navigation check
For sites with no transactional flow at all — marketing pages, docs, blogs, dashboards you're only reading, not submitting to. The "flow" here is closer to a walk than a transaction.

1. Load the page → assert on the core content actually being present (headline/title text, expected sections), not just a 200-equivalent load — a page can render an empty shell or an error boundary and still "load."
2. Follow primary navigation links → expect each to land on a page with content consistent with its label (a "Pricing" link should land somewhere that actually mentions pricing).
3. Check for anything that should conditionally render (e.g. a banner, a logged-in vs. logged-out nav state) and confirm it matches the expected condition rather than assuming it's static.
4. This is also where the accessibility-tree-first approach pays off passively — you'll naturally notice missing alt text, unlabeled links, or bad heading structure while reading the snapshot for other reasons. Worth a one-line mention in the report's Notes even if it wasn't the thing you were asked to check.

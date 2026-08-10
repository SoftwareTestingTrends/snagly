#!/usr/bin/env python3
"""Thin Jira Cloud REST client for the snagly toolkit.

Reusable building block: read + write Jira issues via the REST API v3 so higher-level
QE skills (user-story-reviewer, bug-analyzer, bug-creator, test-case-generator ...) don't
each re-implement auth, JQL search, and ADF formatting.

Read commands (safe, always run):  whoami, get, search, projects, fields, transitions
Write commands (dry-run by default; require --apply):  create, edit, comment, transition, link, attach

Auth comes from environment / a .env file in the repo root (or --env-file):
    JIRA_URL          e.g. https://your-org.atlassian.net
    JIRA_EMAIL        the Atlassian account email
    JIRA_API_TOKEN    an API token (id.atlassian.com/manage-profile/security/api-tokens)
    JIRA_PROJECT_KEY  default project key for `create` (optional; override with --project)

Standard library only — no pip install required.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = "/rest/api/3"

PRINT_PAYLOAD_HELP = ("Dump the full request JSON inline instead of a readable summary. "
                     "By default a dry-run prints a summary and writes the full payload to a "
                     "temp file, so a long ADF description can't overflow the terminal buffer.")


def make_ssl_context() -> ssl.SSLContext:
    """TLS context that verifies certs. Falls back to certifi's CA bundle when the system
    store is empty (common on python.org macOS builds), so verification stays ON."""
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) == 0:
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass  # leave the (empty) default; a clear TLS error beats silently skipping verify
    return ctx


SSL_CONTEXT = make_ssl_context()


# --------------------------------------------------------------------------- config

# Records how config was resolved, so `whoami` can say which file actually won.
ENV_TRACE: "dict" = {"read": [], "source_of_JIRA_URL": None}


def load_dotenv(path: str) -> None:
    """Load KEY=VALUE lines from a .env file WITHOUT overriding already-set env vars."""
    if not path or not os.path.isfile(path):
        return
    ENV_TRACE["read"].append(path)
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
                if key == "JIRA_URL" and ENV_TRACE["source_of_JIRA_URL"] is None:
                    ENV_TRACE["source_of_JIRA_URL"] = path


def _walk_up_env() -> "str | None":
    """Nearest .env walking up from CWD (the in-repo dev case). None if not found."""
    cur = os.getcwd()
    while True:
        candidate = os.path.join(cur, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def env_file_candidates(explicit: "str | None") -> "list[str]":
    """Ordered .env candidates, highest priority first. `load_dotenv` never overrides an
    already-set var, so loading in this order makes earlier sources win — and real
    environment variables (exported JIRA_*) beat every file. This lets the client work
    from ANY repo, not just the one holding the .env:
      1. --env-file <path>            (explicit, per-invocation)
      2. $JIRA_ENV_FILE               (explicit, per-shell)
      3. ~/.jira-connector.env        (stable home location for cross-repo use)
      4. nearest .env walking up      (convenient when run inside this repo)
    """
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("JIRA_ENV_FILE"):
        candidates.append(os.environ["JIRA_ENV_FILE"])
    candidates.append(os.path.expanduser("~/.jira-connector.env"))
    walk = _walk_up_env()
    if walk:
        candidates.append(walk)
    return candidates


def _warn_if_shadowed() -> None:
    """Warn when a project-local .env names a DIFFERENT Jira site than the one that won.

    The project .env is last in the precedence chain, so a machine-wide
    ~/.jira-connector.env (or an exported JIRA_URL) silently overrides it. That is correct
    behaviour and deliberately not changed here — but it is invisible, and the failure mode is
    a confusing 401 or, worse, writing to the wrong Jira site. So: say it out loud, once.
    """
    winner = ENV_TRACE["source_of_JIRA_URL"]
    local = os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(local) or os.path.abspath(local) == os.path.abspath(winner or ""):
        return
    local_url = None
    try:
        with open(local, encoding="utf-8") as fh:
            for raw in fh:
                k, _, v = raw.strip().partition("=")
                if k.strip() == "JIRA_URL":
                    local_url = v.strip().strip('"').strip("'").rstrip("/")
                    break
    except OSError:
        return
    active = (os.environ.get("JIRA_URL") or "").rstrip("/")
    if local_url and active and local_url != active:
        src = winner or "exported shell variables"
        print(f"WARNING: ./.env names {local_url}, but this run is using {active} "
              f"(from {src}).\n"
              f"         The project .env is LAST in the precedence chain. To use it, run with "
              f"`--env-file ./.env`.", file=sys.stderr)


class Config:
    def __init__(self) -> None:
        self.base = (os.environ.get("JIRA_URL") or "").rstrip("/")
        self.email = os.environ.get("JIRA_EMAIL") or ""
        self.token = os.environ.get("JIRA_API_TOKEN") or ""
        self.project = os.environ.get("JIRA_PROJECT_KEY") or ""

    def require(self) -> None:
        missing = [n for n, v in
                   (("JIRA_URL", self.base), ("JIRA_EMAIL", self.email), ("JIRA_API_TOKEN", self.token))
                   if not v]
        if missing:
            die(f"Missing required config: {', '.join(missing)}. Provide it by any of: "
                f"exporting JIRA_* in your shell; creating ~/.jira-connector.env; "
                f"pointing $JIRA_ENV_FILE at an env file; passing --env-file; or a .env in "
                f"the current repo. See SKILL.md.")

    def auth_header(self) -> str:
        raw = f"{self.email}:{self.token}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


# --------------------------------------------------------------------------- http

def die(msg: str, code: int = 1) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def request(cfg: Config, method: str, path: str, body: dict | None = None,
            query: dict | None = None) -> dict:
    url = cfg.base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", cfg.auth_header())
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        src = ENV_TRACE["source_of_JIRA_URL"] or "exported shell variables"
        hint = {
            401: (f"Auth failed — check JIRA_EMAIL / JIRA_API_TOKEN (token, not password).\n"
                  f"     Credentials for {cfg.base} came from: {src}\n"
                  f"     Env files read, in priority order: {ENV_TRACE['read'] or 'none'}\n"
                  f"     If that is the wrong Jira site, an earlier source is shadowing the one "
                  f"you meant — exported JIRA_* beats --env-file beats $JIRA_ENV_FILE beats "
                  f"~/.jira-connector.env beats the nearest .env."),
            403: "Forbidden — the account lacks permission for this project/action.",
            404: "Not found — check the issue key / project key / endpoint.",
            400: "Bad request — usually a bad field name or value (see references/field-reference.md).",
        }.get(exc.code, "")
        die(f"HTTP {exc.code} {exc.reason} on {method} {path}\n{hint}\n{detail}")
    except urllib.error.URLError as exc:
        die(f"Network error reaching {cfg.base}: {exc.reason}")
    return {}  # unreachable


def upload_attachments(cfg: Config, key: str, paths: "list[str]") -> list:
    """POST files to /issue/{key}/attachments as multipart/form-data.

    Attachments are NOT JSON: Jira requires the `X-Atlassian-Token: no-check` header and a
    multipart body with each file in a part named `file`. Stdlib only, so the body is built
    by hand. Returns the list of attachment objects Jira echoes back (id, filename, ...).
    """
    boundary = "----QEAIHub" + uuid.uuid4().hex
    body = bytearray()
    for p in paths:
        with open(p, "rb") as fh:
            content = fh.read()
        fname = os.path.basename(p)
        mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
        body += f"--{boundary}\r\n".encode("utf-8")
        body += (f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
                 f"Content-Type: {mime}\r\n\r\n").encode("utf-8")
        body += content
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")

    url = cfg.base + f"{API}/issue/{key}/attachments"
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Authorization", cfg.auth_header())
    req.add_header("Accept", "application/json")
    req.add_header("X-Atlassian-Token", "no-check")  # required or Jira 403s the upload
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text.strip() else []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        src = ENV_TRACE["source_of_JIRA_URL"] or "exported shell variables"
        hint = {
            401: (f"Auth failed — check JIRA_EMAIL / JIRA_API_TOKEN (token, not password).\n"
                  f"     Credentials for {cfg.base} came from: {src}\n"
                  f"     Env files read, in priority order: {ENV_TRACE['read'] or 'none'}\n"
                  f"     If that is the wrong Jira site, an earlier source is shadowing the one "
                  f"you meant — exported JIRA_* beats --env-file beats $JIRA_ENV_FILE beats "
                  f"~/.jira-connector.env beats the nearest .env."),
            403: "Forbidden — lacking Add-Attachments permission, or attachments are disabled.",
            404: "Not found — check the issue key.",
            413: "File too large — exceeds the site's attachment size limit.",
        }.get(exc.code, "")
        die(f"HTTP {exc.code} {exc.reason} uploading to {key}\n{hint}\n{detail}")
    except urllib.error.URLError as exc:
        die(f"Network error reaching {cfg.base}: {exc.reason}")
    return []  # unreachable


# --------------------------------------------------------------------------- ADF

def text_to_adf(text: str) -> dict:
    """Wrap plain text into a minimal Atlassian Document Format doc.

    Jira Cloud v3 description/comment bodies are ADF, not plain strings. Blank lines
    separate paragraphs; single newlines become hardBreaks within a paragraph.
    """
    blocks = [b for b in text.split("\n\n")]
    content = []
    for block in blocks:
        if not block.strip():
            continue
        nodes = []
        lines = block.split("\n")
        for i, line in enumerate(lines):
            if line:
                nodes.append({"type": "text", "text": line})
            if i < len(lines) - 1:
                nodes.append({"type": "hardBreak"})
        content.append({"type": "paragraph", "content": nodes or [{"type": "text", "text": " "}]})
    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": text or " "}]}]
    return {"type": "doc", "version": 1, "content": content}


def adf_to_text(node) -> str:
    """Best-effort flatten of an ADF node back to plain text (for display)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    out = []
    if isinstance(node, dict):
        if node.get("type") == "text":
            out.append(node.get("text", ""))
        if node.get("type") in ("paragraph", "heading"):
            out.append("\n")
        for child in node.get("content", []) or []:
            out.append(adf_to_text(child))
        if node.get("type") == "hardBreak":
            out.append("\n")
    elif isinstance(node, list):
        for child in node:
            out.append(adf_to_text(child))
    return "".join(out)


# --------------------------------------------------------------------------- commands

def cmd_whoami(cfg: Config, args) -> None:
    me = request(cfg, "GET", f"{API}/myself")
    src = ENV_TRACE["source_of_JIRA_URL"] or "the shell environment (exported JIRA_URL)"
    print(json.dumps({
        "accountId": me.get("accountId"),
        "displayName": me.get("displayName"),
        "email": me.get("emailAddress"),
        "base": cfg.base,
        "defaultProject": cfg.project or None,
        "configFrom": src,
        "envFilesRead": ENV_TRACE["read"],
    }, indent=2))
    if len(ENV_TRACE["read"]) > 1:
        print(f"\nNote: {len(ENV_TRACE['read'])} env files were read. Earlier sources win, and "
              f"exported shell variables beat all files. This account came from: {src}",
              file=sys.stderr)


def cmd_get(cfg: Config, args) -> None:
    fields = args.fields or ("summary,description,status,issuetype,priority,labels,"
                             "assignee,reporter,created,updated,components,fixVersions")
    query = {"fields": fields}
    issue = request(cfg, "GET", f"{API}/issue/{args.key}", query=query)
    f = issue.get("fields", {})
    if args.raw:
        print(json.dumps(issue, indent=2))
        return
    out = {
        "key": issue.get("key"),
        "summary": f.get("summary"),
        "type": (f.get("issuetype") or {}).get("name"),
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "labels": f.get("labels"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "reporter": (f.get("reporter") or {}).get("displayName"),
        "created": f.get("created"),
        "updated": f.get("updated"),
        "description": adf_to_text(f.get("description")).strip(),
    }
    print(json.dumps(out, indent=2))


def cmd_comments(cfg: Config, args) -> None:
    data = request(cfg, "GET", f"{API}/issue/{args.key}/comment",
                   query={"maxResults": args.max, "orderBy": "created"})
    rows = []
    for cm in data.get("comments", []):
        rows.append({
            "author": (cm.get("author") or {}).get("displayName"),
            "created": cm.get("created"),
            "body": adf_to_text(cm.get("body")).strip(),
        })
    print(json.dumps({"key": args.key, "count": len(rows), "comments": rows},
                     indent=2, ensure_ascii=False))


# Fields that cmd_search projects into named output keys. Anything else requested via --fields
# (e.g. a customfield_* like "Team Area") is passed through under its own id, rendered generically.
_SEARCH_STD_FIELDS = {"summary", "status", "issuetype", "priority", "assignee", "updated"}


def _render_field(v):
    """Render an arbitrary Jira field value into a JSON-friendly scalar/list.

    Option & user objects collapse to their display string; arrays map element-wise; scalars
    pass through. Keeps custom-field passthrough readable without hard-coding each field's shape.
    """
    if isinstance(v, list):
        return [_render_field(x) for x in v]
    if isinstance(v, dict):
        return v.get("value") or v.get("name") or v.get("displayName") or v
    return v


def cmd_search(cfg: Config, args) -> None:
    fields = [x.strip() for x in (args.fields or "summary,status,issuetype,priority,assignee,updated").split(",") if x.strip()]
    extra = [f for f in fields if f not in _SEARCH_STD_FIELDS]
    collected = []
    next_token = None
    while True:
        body = {"jql": args.jql, "maxResults": min(args.max, 100), "fields": fields}
        if next_token:
            body["nextPageToken"] = next_token
        page = request(cfg, "POST", f"{API}/search/jql", body=body)
        for issue in page.get("issues", []):
            f = issue.get("fields", {})
            row = {
                "key": issue.get("key"),
                "summary": f.get("summary"),
                "status": (f.get("status") or {}).get("name"),
                "type": (f.get("issuetype") or {}).get("name"),
                "priority": (f.get("priority") or {}).get("name"),
                "assignee": (f.get("assignee") or {}).get("displayName"),
                "updated": f.get("updated"),
            }
            for fid in extra:  # pass through any additionally requested (e.g. custom) fields
                row[fid] = _render_field(f.get(fid))
            collected.append(row)
            if len(collected) >= args.max:
                break
        next_token = page.get("nextPageToken")
        if page.get("isLast") or not next_token or len(collected) >= args.max:
            break
    print(json.dumps({"count": len(collected), "issues": collected}, indent=2, ensure_ascii=False))


def cmd_projects(cfg: Config, args) -> None:
    page = request(cfg, "GET", f"{API}/project/search", query={"maxResults": 100})
    projs = [{"key": p.get("key"), "name": p.get("name"), "id": p.get("id")}
             for p in page.get("values", [])]
    print(json.dumps({"count": len(projs), "projects": projs}, indent=2))


def cmd_fields(cfg: Config, args) -> None:
    fields = request(cfg, "GET", f"{API}/field")
    rows = [{"id": f.get("id"), "name": f.get("name"), "custom": f.get("custom")}
            for f in fields]
    if args.grep:
        needle = args.grep.lower()
        rows = [r for r in rows if needle in (r["name"] or "").lower()]
    print(json.dumps({"count": len(rows), "fields": rows}, indent=2))


def cmd_transitions(cfg: Config, args) -> None:
    data = request(cfg, "GET", f"{API}/issue/{args.key}/transitions")
    trs = [{"id": t.get("id"), "name": t.get("name"),
            "to": (t.get("to") or {}).get("name")} for t in data.get("transitions", [])]
    print(json.dumps({"key": args.key, "transitions": trs}, indent=2))


def _read_body_text(args) -> str:
    if getattr(args, "body_file", None):
        with open(args.body_file, encoding="utf-8") as fh:
            return fh.read()
    return getattr(args, "body", None) or getattr(args, "description", None) or ""


def _load_adf_file(path: str) -> dict:
    """Load a raw ADF document from a JSON file and sanity-check it is a doc node."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if not (isinstance(doc, dict) and doc.get("type") == "doc" and "content" in doc):
        die(f"--adf-file {path} is not a valid ADF doc "
            f"(expected top-level {{\"type\": \"doc\", \"version\": 1, \"content\": [...]}}).")
    doc.setdefault("version", 1)
    return doc


def _node_text(node) -> str:
    """Flatten an ADF node's text content recursively into a plain string."""
    if isinstance(node, list):
        return "".join(_node_text(n) for n in node)
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    return _node_text(node.get("content", []))


def _clip(text: str, width: int = 72) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _adf_outline(doc) -> "list[str]":
    """Render an ADF doc as a short structural outline — one line per top-level node.

    This is what a reviewer actually needs at the dry-run gate: which sections exist and
    roughly what is in them. The full tree goes to a file (see `_write_payload`)."""
    lines = []
    for node in (doc or {}).get("content", []) or []:
        ntype = node.get("type")
        text = _node_text(node)
        if ntype == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            lines.append(f"{'#' * int(level)} {_clip(text)}")
        elif ntype in ("bulletList", "orderedList"):
            items = node.get("content", []) or []
            marker = "•" if ntype == "bulletList" else "1."
            first = _clip(_node_text(items[0]), 56) if items else ""
            lines.append(f"  {marker} {len(items)} item(s)" + (f": {first}" if first else ""))
        elif ntype == "codeBlock":
            lines.append(f"  [code block, {len(text.splitlines())} line(s)]")
        elif text:
            lines.append(f"  {_clip(text)}")
        else:
            lines.append(f"  [{ntype}]")
    return lines


def _write_payload(payload: dict, slug: str) -> str:
    """Write the full request payload to a stable temp path so it can be read on demand.

    The name is deterministic per command+target, so repeated dry-runs overwrite rather
    than accumulating stale payload files."""
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)
    path = os.path.join(tempfile.gettempdir(), f"jira-dryrun-{safe}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def _print_description(fields: dict, label: str = "Description") -> None:
    """Print an ADF description/body as a labelled outline, if there is one."""
    doc = fields.get("description") if isinstance(fields, dict) else None
    if not isinstance(doc, dict):
        return
    nodes = doc.get("content", []) or []
    print(f"  {label:<11} ADF, {len(nodes)} node(s), {len(_node_text(doc))} chars of text")
    for line in _adf_outline(doc):
        print(f"    {line}")


def _payload_footer(payload: dict, slug: str) -> None:
    """Tell the reader where the full payload is, and how to get it inline instead."""
    print(f"\nFull payload: {_write_payload(payload, slug)}")
    print("(re-run with --print-payload to print it inline instead)")


def _load_fields_json(path: str) -> dict:
    """Load a JSON object of extra fields to merge into the create payload's `fields`."""
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, dict):
        die(f"--fields-json {path} must contain a JSON object of field-id -> value.")
    return obj


def _parse_kv_fields(pairs) -> dict:
    """Turn repeated `--field name=value` args into a {name: value} dict (plain strings)."""
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            die(f"--field expects name=value, got: {pair!r}")
        name, _, value = pair.partition("=")
        out[name.strip()] = value
    return out


def _parse_links(specs) -> "list[dict]":
    """Turn repeated `--link TYPE:KEY` args into [{type, key}]. TYPE is a link-type name
    (e.g. Relates, Blocks); KEY is the outward issue to link the new/target issue to."""
    out = []
    for spec in specs or []:
        if ":" not in spec:
            die(f"--link expects TYPE:KEY (e.g. 'Relates:PROJ-100'), got: {spec!r}")
        link_type, _, key = spec.partition(":")
        link_type, key = link_type.strip(), key.strip()
        if not link_type or not key:
            die(f"--link expects a non-empty TYPE and KEY, got: {spec!r}")
        out.append({"type": link_type, "key": key})
    return out


def _create_issue_link(cfg: Config, link_type: str, inward_key: str, outward_key: str) -> None:
    """POST /issueLink: `inward_key` --(link_type)--> `outward_key`."""
    request(cfg, "POST", f"{API}/issueLink", body={
        "type": {"name": link_type},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key},
    })


def cmd_create(cfg: Config, args) -> None:
    project = args.project or cfg.project
    if not project:
        die("No project key. Pass --project or set JIRA_PROJECT_KEY in .env.")
    fields = {
        "project": {"key": project},
        "issuetype": {"name": args.type},
        "summary": args.summary,
    }
    # Description precedence: raw ADF file > plain text (--body-file / --description).
    if getattr(args, "adf_file", None):
        fields["description"] = _load_adf_file(args.adf_file)
    else:
        desc = _read_body_text(args)
        if desc:
            fields["description"] = text_to_adf(desc)
    if args.labels:
        fields["labels"] = [l.strip() for l in args.labels.split(",") if l.strip()]
    if args.priority:
        fields["priority"] = {"name": args.priority}
    # Arbitrary custom fields last so they can override the above (e.g. a full field JSON).
    if getattr(args, "fields_json", None):
        fields.update(_load_fields_json(args.fields_json))
    fields.update(_parse_kv_fields(getattr(args, "field", None)))
    payload = {"fields": fields}
    links = _parse_links(getattr(args, "link", None))

    if not args.apply:
        if getattr(args, "print_payload", False):
            print("DRY RUN — no issue created. Would POST /issue with:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("DRY RUN — no issue created. Would POST /issue:\n")
            print(f"  {'Project':<11} {project}")
            print(f"  {'Type':<11} {args.type}")
            print(f"  {'Summary':<11} {fields.get('summary')}")
            if fields.get("priority"):
                print(f"  {'Priority':<11} {(fields['priority'] or {}).get('name')}")
            if fields.get("labels"):
                print(f"  {'Labels':<11} {', '.join(fields['labels'])}")
            custom = sorted(k for k in fields if k.startswith("customfield_"))
            if custom:
                print(f"  {'Custom':<11} {', '.join(custom)}")
            _print_description(fields)
        for lk in links:
            print(f"...then link: NEW --{lk['type']}--> {lk['key']}")
        if not getattr(args, "print_payload", False):
            _payload_footer(payload, f"create-{project}")
        print("\nRe-run with --apply to create.")
        return
    res = request(cfg, "POST", f"{API}/issue", body=payload)
    key = res.get("key")
    linked = []
    for lk in links:
        _create_issue_link(cfg, lk["type"], key, lk["key"])
        linked.append(f"{lk['type']}:{lk['key']}")
    print(json.dumps({"created": key, "url": f"{cfg.base}/browse/{key}",
                      "links": linked}, indent=2))


def cmd_edit(cfg: Config, args) -> None:
    """Update fields on an existing issue. Only the fields you pass are touched."""
    fields: dict = {}
    if getattr(args, "summary", None):
        fields["summary"] = args.summary
    if getattr(args, "priority", None):
        fields["priority"] = {"name": args.priority}
    if getattr(args, "labels", None):
        fields["labels"] = [l.strip() for l in args.labels.split(",") if l.strip()]
    if getattr(args, "adf_file", None):
        fields["description"] = _load_adf_file(args.adf_file)
    elif getattr(args, "description", None):
        fields["description"] = text_to_adf(args.description)
    if getattr(args, "fields_json", None):
        fields.update(_load_fields_json(args.fields_json))
    fields.update(_parse_kv_fields(getattr(args, "field", None)))
    if not fields:
        die("Nothing to edit. Pass at least one of --summary / --priority / --labels / "
            "--description / --adf-file / --fields-json / --field.")
    payload = {"fields": fields}

    if not args.apply:
        if getattr(args, "print_payload", False):
            print(f"DRY RUN — no changes made. Would PUT /issue/{args.key} with:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"DRY RUN — no changes made. Would PUT /issue/{args.key}:\n")
            for name in ("summary", "priority", "labels"):
                if name not in fields:
                    continue
                value = fields[name]
                if isinstance(value, dict):
                    value = value.get("name")
                elif isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                print(f"  {name.capitalize():<11} {value}")
            custom = sorted(k for k in fields if k.startswith("customfield_"))
            if custom:
                print(f"  {'Custom':<11} {', '.join(custom)}")
            _print_description(fields)
            _payload_footer(payload, f"edit-{args.key}")
        print("\nNote: labels and multi-value fields are REPLACED, not merged.")
        print("Re-run with --apply to update.")
        return
    request(cfg, "PUT", f"{API}/issue/{args.key}", body=payload)
    print(json.dumps({"updated": args.key, "url": f"{cfg.base}/browse/{args.key}",
                      "fields": sorted(fields.keys())}, indent=2))


def cmd_link(cfg: Config, args) -> None:
    payload = {
        "type": {"name": args.type},
        "inwardIssue": {"key": getattr(args, "from")},
        "outwardIssue": {"key": args.to},
    }
    if not args.apply:
        print("DRY RUN — no link created. Would POST /issueLink with:")
        print(json.dumps(payload, indent=2))
        print(f"\nEffect: {getattr(args, 'from')} --{args.type}--> {args.to}")
        print("\nRe-run with --apply to link.")
        return
    request(cfg, "POST", f"{API}/issueLink", body=payload)
    print(json.dumps({"linked": f"{getattr(args, 'from')} --{args.type}--> {args.to}"}, indent=2))


def cmd_comment(cfg: Config, args) -> None:
    # Body precedence: raw ADF file (rich: media/embeds, tables, headings) > plain text.
    if getattr(args, "adf_file", None):
        payload = {"body": _load_adf_file(args.adf_file)}
    else:
        text = _read_body_text(args)
        if not text:
            die("Empty comment. Pass --body, --body-file, or --adf-file.")
        payload = {"body": text_to_adf(text)}
    if not args.apply:
        if getattr(args, "print_payload", False):
            print(f"DRY RUN — no comment added to {args.key}. Would POST:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"DRY RUN — no comment added to {args.key}. Would POST:\n")
            _print_description({"description": payload["body"]}, label="Body")
            _payload_footer(payload, f"comment-{args.key}")
        print("\nRe-run with --apply to post.")
        return
    res = request(cfg, "POST", f"{API}/issue/{args.key}/comment", body=payload)
    print(json.dumps({"commented": args.key, "commentId": res.get("id")}, indent=2))


def cmd_attach(cfg: Config, args) -> None:
    paths = args.file or []
    if not paths:
        die("No files to attach. Pass one or more --file <path>.")
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        die(f"File(s) not found: {', '.join(missing)}")
    if not args.apply:
        print(f"DRY RUN — nothing uploaded to {args.key}. Would attach:")
        for p in paths:
            size = os.path.getsize(p)
            print(f"  {os.path.basename(p)}  ({size} bytes)  <- {p}")
        print("\nRe-run with --apply to upload.")
        return
    res = upload_attachments(cfg, args.key, paths)
    out = [{"id": a.get("id"), "filename": a.get("filename"),
            "size": a.get("size")} for a in res]
    print(json.dumps({"attached": args.key, "count": len(out), "attachments": out},
                     indent=2, ensure_ascii=False))


def cmd_transition(cfg: Config, args) -> None:
    data = request(cfg, "GET", f"{API}/issue/{args.key}/transitions")
    trs = data.get("transitions", [])
    match = None
    for t in trs:
        if args.to.lower() in (t.get("name", "").lower(), (t.get("to") or {}).get("name", "").lower()):
            match = t
            break
    if not match:
        names = ", ".join(f"{t.get('name')} -> {(t.get('to') or {}).get('name')}" for t in trs)
        die(f"No transition matching '{args.to}' on {args.key}. Available: {names or '(none)'}")
    payload = {"transition": {"id": match["id"]}}
    if not args.apply:
        print(f"DRY RUN — {args.key} not transitioned. Would move via "
              f"'{match.get('name')}' -> '{(match.get('to') or {}).get('name')}'.")
        print("\nRe-run with --apply to transition.")
        return
    request(cfg, "POST", f"{API}/issue/{args.key}/transitions", body=payload)
    print(json.dumps({"transitioned": args.key,
                      "to": (match.get("to") or {}).get("name")}, indent=2))


# --------------------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Thin Jira Cloud REST client for QE skills.")
    p.add_argument("--env-file", help="Path to a .env file. Highest-priority config source; "
                   "otherwise $JIRA_ENV_FILE, ~/.jira-connector.env, or nearest .env walking "
                   "up from CWD (env vars always win).")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami", help="Verify auth; print the authenticated account + config.")

    g = sub.add_parser("get", help="Fetch one issue.")
    g.add_argument("key")
    g.add_argument("--fields", help="Comma-separated field list (default: common set).")
    g.add_argument("--raw", action="store_true", help="Print the full raw issue JSON.")

    cmt = sub.add_parser("comments", help="List an issue's comments (author, time, body).")
    cmt.add_argument("key")
    cmt.add_argument("--max", type=int, default=50, help="Max comments to return (default 50).")

    s = sub.add_parser("search", help="Run a JQL search (paginated).")
    s.add_argument("--jql", required=True)
    s.add_argument("--max", type=int, default=50, help="Max issues to return (default 50).")
    s.add_argument("--fields", help="Comma-separated field list.")

    sub.add_parser("projects", help="List accessible projects.")

    fp = sub.add_parser("fields", help="List fields (find custom field IDs).")
    fp.add_argument("--grep", help="Filter field names (case-insensitive substring).")

    tl = sub.add_parser("transitions", help="List available status transitions for an issue.")
    tl.add_argument("key")

    c = sub.add_parser("create", help="Create an issue (dry-run unless --apply).")
    c.add_argument("--project", help="Project key (default: JIRA_PROJECT_KEY).")
    c.add_argument("--type", default="Bug", help="Issue type name (default Bug). "
                   "For sub-tasks pass the sub-task type name and set parent via --fields-json.")
    c.add_argument("--summary", required=True)
    c.add_argument("--description", help="Description text (plain text -> ADF).")
    c.add_argument("--body-file", help="Read description from a file (plain text -> ADF).")
    c.add_argument("--adf-file", help="Read description from a file containing a raw ADF JSON doc "
                   "(used verbatim; enables taskLists/headings/panels). Overrides --description/--body-file.")
    c.add_argument("--fields-json", help="Path to a JSON object of extra fields merged into the "
                   "payload (e.g. custom fields, {\"parent\": {\"key\": \"PROJ-1\"}}). Overrides earlier fields.")
    c.add_argument("--field", action="append", metavar="NAME=VALUE",
                   help="Set a simple string field (repeatable), e.g. --field customfield_10790='Release Testing'.")
    c.add_argument("--link", action="append", metavar="TYPE:KEY",
                   help="After create, link the new issue outward to KEY (repeatable), "
                        "e.g. --link 'Relates:PROJ-100'. Applied only with --apply.")
    c.add_argument("--labels", help="Comma-separated labels.")
    c.add_argument("--priority", help="Priority name (e.g. High).")
    c.add_argument("--print-payload", action="store_true", help=PRINT_PAYLOAD_HELP)
    c.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    lk = sub.add_parser("link", help="Link two existing issues (dry-run unless --apply).")
    lk.add_argument("--from", required=True, help="Inward issue key (the source).")
    lk.add_argument("--to", required=True, help="Outward issue key (the target).")
    lk.add_argument("--type", default="Relates", help="Link type name (default Relates; e.g. Blocks, Cloners).")
    lk.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    ed = sub.add_parser("edit", help="Update fields on an existing issue (dry-run unless --apply).")
    ed.add_argument("key")
    ed.add_argument("--summary", help="New summary line.")
    ed.add_argument("--priority", help="Priority name, e.g. Highest / High / Medium.")
    ed.add_argument("--labels", help="Comma-separated labels. REPLACES the existing set.")
    ed.add_argument("--description", help="New description (plain text -> ADF).")
    ed.add_argument("--adf-file", help="New description from a raw ADF JSON file. Overrides --description.")
    ed.add_argument("--fields-json", help="JSON object merged into fields (custom fields).")
    ed.add_argument("--field", action="append", metavar="NAME=VALUE",
                    help="Set a simple string field (repeatable).")
    ed.add_argument("--print-payload", action="store_true", help=PRINT_PAYLOAD_HELP)
    ed.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    cm = sub.add_parser("comment", help="Comment on an issue (dry-run unless --apply).")
    cm.add_argument("key")
    cm.add_argument("--body", help="Comment text (plain text -> ADF).")
    cm.add_argument("--body-file", help="Read comment from a file (plain text -> ADF).")
    cm.add_argument("--adf-file", help="Read the comment from a file containing a raw ADF JSON doc "
                    "(used verbatim; enables embedded media/screenshots, tables, headings). "
                    "Overrides --body/--body-file.")
    cm.add_argument("--print-payload", action="store_true", help=PRINT_PAYLOAD_HELP)
    cm.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    at = sub.add_parser("attach", help="Upload file attachment(s) to an issue (dry-run unless --apply).")
    at.add_argument("key")
    at.add_argument("--file", action="append", required=True, metavar="PATH",
                    help="File to attach (repeatable), e.g. --file shot1.png --file shot2.png.")
    at.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    tr = sub.add_parser("transition", help="Move an issue to a new status (dry-run unless --apply).")
    tr.add_argument("key")
    tr.add_argument("--to", required=True, help="Target transition name or destination status.")
    tr.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, runs in dry-run mode.")

    return p


DISPATCH = {
    "whoami": cmd_whoami, "get": cmd_get, "comments": cmd_comments, "search": cmd_search,
    "projects": cmd_projects, "fields": cmd_fields, "transitions": cmd_transitions,
    "create": cmd_create, "comment": cmd_comment, "transition": cmd_transition,
    "link": cmd_link, "attach": cmd_attach, "edit": cmd_edit,
}


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    for path in env_file_candidates(args.env_file):
        load_dotenv(path)  # no-op if the file is missing or the var is already set
    _warn_if_shadowed()
    cfg = Config()
    cfg.require()
    DISPATCH[args.command](cfg, args)


if __name__ == "__main__":
    main()

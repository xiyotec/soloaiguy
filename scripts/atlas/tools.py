"""Tool definitions and handlers for Atlas.

All tool handlers return a string (the tool_result content). They never raise —
errors are returned as text so Atlas can recover and tell Xiyo what failed.

Philosophy: Atlas is trusted to act. Safety lives at the OS layer — Atlas runs
as its own Linux user with a locked password, no sudo, an isolated home dir,
and a scoped GitHub PAT (xiyotec/soloaiguy only). Blast radius of any action
is bounded by those perms. The system prompt tells Atlas to vet what it's
installing or running before doing it.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
ATLAS_DB = Path(__file__).parent / "atlas.db"
MAX_WRITE_BYTES = 1_000_000  # 1 MB hard cap on write_file content

# Anthropic-side tool definitions (passed to messages.create as `tools=`).
TOOL_DEFS = [
    {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 8,
    },
    {
        "name": "bash",
        "description": (
            "Run a shell command from the soloaiguy repo root. You have full "
            "latitude — git ops (including push), npm, python, file edits via "
            "sed/awk, curl, etc. You run as the 'atlas' Linux user with no "
            "sudo and an isolated home dir, so the OS bounds the blast radius. "
            "Two things to watch yourself on: (1) curl|sh / wget|sh — vet the "
            "script first, never pipe untrusted content to a shell; (2) "
            "force-push to main — don't rewrite published history without "
            "Xiyo's say-so. Default timeout 60s; pass timeout_seconds (max 600)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run from repo root."},
                "timeout_seconds": {"type": "integer", "description": "Optional timeout (default 60, max 600)."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file. Path is relative to repo root or an absolute path "
            "INSIDE the repo. By default returns the first 400 lines. Pass "
            "offset (1-based start line) and limit (line count) to paginate "
            "through bigger files instead of falling back to bash sed/cat. "
            "The response header tells you the total line count so you know "
            "if there's more to fetch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "offset": {"type": "integer", "description": "1-based line to start at. Default 1."},
                "limit": {"type": "integer", "description": "Max lines to return. Default 400, max 2000."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "patch_file",
        "description": (
            "Edit a file by replacing exact text. Much cheaper than write_file "
            "for small changes — no need to re-emit the whole file. old_string "
            "must appear EXACTLY ONCE in the file (include surrounding lines if "
            "needed for uniqueness) unless replace_all is true. Returns the "
            "before/after line count. Use this for any edit smaller than ~50 "
            "lines; use write_file only for new files or full rewrites."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to repo root."},
                "old_string": {"type": "string", "description": "Exact text to find. Must be unique unless replace_all=true."},
                "new_string": {"type": "string", "description": "Replacement text. Empty string deletes."},
                "replace_all": {"type": "boolean", "description": "Replace every occurrence (default false)."},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the repo (creates or overwrites). USE "
            "patch_file FOR EDITS — write_file is only for new files or full "
            "rewrites. Path must resolve inside the repo root; absolute paths "
            "or '..' that escape the repo are rejected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to repo root."},
                "content": {"type": "string", "description": "Full file contents to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "search_history",
        "description": (
            "Full-text search across ALL past Telegram conversations with Xiyo "
            "(persisted in atlas.db). Use when Xiyo references a previous chat, "
            "or when reviewing your own past behavior to learn from it. Matches "
            "are case-insensitive substring on message text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Substring to match."},
                "limit": {"type": "integer", "description": "Max matches to return (default 10, max 50)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "run_cron",
        "description": (
            "Invoke one of the cron scripts. These interact with Telegram and "
            "external state. Allowed: intel-cron, exp-cron, publish-cron, "
            "social-cron, affiliate-injector. affiliate-injector accepts dry_run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["intel-cron", "exp-cron", "publish-cron", "social-cron", "affiliate-injector"],
                },
                "dry_run": {"type": "boolean", "description": "affiliate-injector only. Default false."},
                "env": {
                    "type": "object",
                    "description": "Optional env vars. UPPER_SNAKE_CASE keys.",
                },
            },
            "required": ["name"],
        },
    },
]

CRON_SCRIPTS = {
    "intel-cron": "scripts/intel-cron.sh",
    "exp-cron": "scripts/exp-cron.sh",
    "publish-cron": "scripts/publish-cron.sh",
    "social-cron": "scripts/social-cron.sh",
    "affiliate-injector": "scripts/affiliate-injector.py",
}


def _run_shell(cmd: str, timeout: int = 60, env: dict | None = None) -> str:
    proc_env = {**os.environ, **(env or {})} if env else None
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            cwd=str(REPO),
            capture_output=True, text=True,
            timeout=timeout, env=proc_env,
        )
    except subprocess.TimeoutExpired:
        return f"TIMEOUT after {timeout}s"
    out = (proc.stdout or "") + ("\n--stderr--\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        out = f"(exit {proc.returncode})\n{out}"
    if len(out) > 4000:
        out = f"... (truncated, kept last 4000 of {len(out)} chars)\n" + out[-4000:]
    return out


def handle_bash(command: str, timeout_seconds: int | None = None) -> str:
    cmd = command.strip()
    if not cmd:
        return "ERROR: empty command"
    timeout = max(1, min(int(timeout_seconds or 60), 600))
    return _run_shell(cmd, timeout=timeout)


def _resolve_repo_path(path: str) -> Path | None:
    """Return resolved Path inside repo, or None if it escapes."""
    p = Path(path)
    if p.is_absolute():
        full = p.resolve()
    else:
        full = (REPO / p).resolve()
    try:
        full.relative_to(REPO)
        return full
    except ValueError:
        return None


def handle_read_file(path: str, offset: int = 1, limit: int = 400) -> str:
    full = _resolve_repo_path(path)
    if full is None:
        return f"DENIED: path '{path}' escapes repo root"
    if not full.exists():
        return f"NOT FOUND: {path}"
    if full.is_dir():
        return f"IS DIR: {path} — use 'bash' with 'ls' instead"
    try:
        text = full.read_text(errors="replace")
    except Exception as e:
        return f"READ ERROR: {e}"
    lines = text.splitlines(keepends=True)
    total = len(lines)
    start = max(1, int(offset or 1)) - 1            # to 0-based
    if start >= total:
        return f"[empty: offset {start + 1} is past EOF (file has {total} lines)]"
    take = max(1, min(int(limit or 400), 2000))
    end = min(total, start + take)
    window = "".join(lines[start:end])
    # Hard char cap so a single huge line doesn't blow context
    char_cap = 16000
    truncated_chars = False
    if len(window) > char_cap:
        window = window[:char_cap]
        truncated_chars = True
    header = f"[lines {start + 1}-{end} of {total}]"
    if end < total:
        header += f" — {total - end} more lines, call again with offset={end + 1}"
    if truncated_chars:
        header += f" — char-capped at {char_cap}; use a smaller limit"
    return f"{header}\n{window}"


def handle_write_file(path: str, content: str) -> str:
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return f"DENIED: content exceeds {MAX_WRITE_BYTES} byte cap. Split into smaller files."
    full = _resolve_repo_path(path)
    if full is None:
        return f"DENIED: path '{path}' escapes repo root"
    if full.is_dir():
        return f"DENIED: '{path}' is a directory."
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        existed = full.exists()
        old_size = full.stat().st_size if existed else 0
        full.write_text(content)
        new_size = full.stat().st_size
        verb = "updated" if existed else "created"
        return f"OK {verb} {path} ({old_size} -> {new_size} bytes)"
    except Exception as e:
        return f"WRITE ERROR: {type(e).__name__}: {e}"


def handle_patch_file(path: str, old_string: str, new_string: str,
                      replace_all: bool = False) -> str:
    if not old_string:
        return "DENIED: old_string is empty. Use write_file to create a new file."
    full = _resolve_repo_path(path)
    if full is None:
        return f"DENIED: path '{path}' escapes repo root"
    if not full.exists():
        return f"NOT FOUND: {path} — use write_file to create new files."
    if full.is_dir():
        return f"DENIED: '{path}' is a directory."
    try:
        text = full.read_text(errors="replace")
    except Exception as e:
        return f"READ ERROR: {e}"
    count = text.count(old_string)
    if count == 0:
        return (
            f"NO MATCH: old_string not found in {path}. "
            "Read the file again — the text may have whitespace or quotes you didn't expect."
        )
    if count > 1 and not replace_all:
        return (
            f"AMBIGUOUS: old_string matches {count} times in {path}. "
            "Either include more surrounding context to make it unique, "
            "or pass replace_all=true."
        )
    new_text = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
    if len(new_text.encode("utf-8")) > MAX_WRITE_BYTES:
        return f"DENIED: result exceeds {MAX_WRITE_BYTES} byte cap."
    try:
        full.write_text(new_text)
    except Exception as e:
        return f"WRITE ERROR: {type(e).__name__}: {e}"
    old_lines = text.count("\n")
    new_lines = new_text.count("\n")
    delta = new_lines - old_lines
    sign = "+" if delta >= 0 else ""
    occurrences = count if replace_all else 1
    return f"OK patched {path}: {occurrences} replacement(s), {sign}{delta} lines (now {new_lines} lines)"


def handle_search_history(query: str, limit: int = 10) -> str:
    q = (query or "").strip()
    if not q:
        return "ERROR: empty query"
    n = max(1, min(int(limit or 10), 50))
    if not ATLAS_DB.exists():
        return "NO HISTORY: atlas.db does not exist yet."
    try:
        conn = sqlite3.connect(ATLAS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ts, role, content_json FROM messages "
            "WHERE LOWER(content_json) LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (f"%{q.lower()}%", n),
        ).fetchall()
        conn.close()
    except Exception as e:
        return f"DB ERROR: {type(e).__name__}: {e}"
    if not rows:
        return f"No matches for '{q}'."
    out = [f"{len(rows)} match(es) for '{q}' (most recent first):"]
    for r in rows:
        try:
            blocks = json.loads(r["content_json"])
            text_parts = []
            for b in blocks if isinstance(blocks, list) else []:
                if isinstance(b, dict):
                    if b.get("type") == "text":
                        text_parts.append(b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        text_parts.append(f"[tool_use {b.get('name')} {json.dumps(b.get('input', {}))[:120]}]")
                    elif b.get("type") == "tool_result":
                        c = b.get("content", "")
                        if isinstance(c, list):
                            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        text_parts.append(f"[tool_result {str(c)[:200]}]")
            text = " ".join(p for p in text_parts if p).strip()
        except Exception:
            text = r["content_json"][:300]
        if len(text) > 400:
            text = text[:400] + "…"
        out.append(f"- [{r['ts'][:16]}] {r['role']}: {text}")
    return "\n".join(out)


def handle_run_cron(name: str, dry_run: bool = False, env: dict | None = None) -> str:
    if name not in CRON_SCRIPTS:
        return f"UNKNOWN cron: {name}"
    script = CRON_SCRIPTS[name]
    if name == "affiliate-injector":
        cmd = f"./{script}" + (" --dry-run" if dry_run else "")
    else:
        if dry_run:
            return "DENIED: dry_run is only supported for affiliate-injector"
        cmd = f"./{script}"
    if env:
        for k in env:
            if not k.replace("_", "").isalnum() or not k.isupper():
                return f"DENIED: env var name '{k}' must be UPPER_SNAKE_CASE"
    return _run_shell(cmd, timeout=600, env=env)


def dispatch(name: str, params: dict) -> str:
    """Route a tool_use to its handler. Returns the tool_result content string."""
    try:
        if name == "bash":
            return handle_bash(
                command=params.get("command", ""),
                timeout_seconds=params.get("timeout_seconds"),
            )
        if name == "read_file":
            return handle_read_file(
                path=params.get("path", ""),
                offset=int(params.get("offset", 1) or 1),
                limit=int(params.get("limit", 400) or 400),
            )
        if name == "write_file":
            return handle_write_file(
                path=params.get("path", ""),
                content=params.get("content", ""),
            )
        if name == "patch_file":
            return handle_patch_file(
                path=params.get("path", ""),
                old_string=params.get("old_string", ""),
                new_string=params.get("new_string", ""),
                replace_all=bool(params.get("replace_all", False)),
            )
        if name == "search_history":
            return handle_search_history(
                query=params.get("query", ""),
                limit=int(params.get("limit", 10)),
            )
        if name == "run_cron":
            return handle_run_cron(
                name=params.get("name", ""),
                dry_run=bool(params.get("dry_run", False)),
                env=params.get("env"),
            )
        return f"UNKNOWN TOOL: {name}"
    except Exception as e:
        return f"HANDLER ERROR ({name}): {type(e).__name__}: {e}"

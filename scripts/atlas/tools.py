"""Tool definitions and handlers for Atlas.

All tool handlers return a string (the tool_result content). They never raise —
errors are returned as text so Atlas can recover and tell Xiyo what failed.

Philosophy: Atlas is trusted to act. The hard guardrails block only catastrophic
actions (privilege escalation, disk wipe, supply-chain attacks, secret-file
writes). Everything else is Atlas's judgment — the system prompt tells him to
verify what he's installing or running before he does it.
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
            "Run a shell command from the soloaiguy repo root. You have wide "
            "latitude — git ops (including push), npm, python, file edits via "
            "sed/awk, curl for legitimate API calls, etc. Hard-blocked: sudo, "
            "rm -rf / or ~, dd to disks, mkfs, fork bombs, chmod -R 777, "
            "supply-chain attacks (curl|sh, wget|sh), force-push to main, and "
            "writes to ~/.soloaiguy.env or ~/.affiliates.local. Default timeout "
            "60s; pass timeout_seconds for longer."
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
            "INSIDE the repo. Returns up to 12000 chars."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the repo (creates or overwrites). Use "
            "this to edit posts, calendar, status, scripts, etc. Hard-blocked: "
            "any path matching .env*, ~/.soloaiguy.env, ~/.affiliates.local, "
            "~/.ssh/*, .aider.conf.yml, anything outside the repo. For edits to "
            "an existing file, READ it first so you preserve context — "
            "write_file overwrites the entire file."
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

# Hard catastrophic denylist. Anything matching these substrings is rejected
# before execution. The bash handler also does targeted checks for
# pipe-to-shell, force-push to main, and secret-file writes.
CATASTROPHIC_BASH_PATTERNS = (
    "sudo ", "su -", "su root",
    "rm -rf /", "rm -rf ~", "rm -rf $HOME", "rm -rf ..", "rm -rf /*",
    "dd if=", "dd of=/dev/",
    "mkfs.", "/dev/sda", "/dev/nvme", "/dev/disk",
    "chmod -R 777", "chmod 777 /",
    ":(){ :|:& };:", ":(){:|:&};:",
)

# Detected via regex-ish substring scan.
SECRET_FILE_WRITE_PATTERNS = (
    "> ~/.soloaiguy.env", ">> ~/.soloaiguy.env",
    "> ~/.affiliates.local", ">> ~/.affiliates.local",
    "> ~/.ssh/", ">> ~/.ssh/",
    "> ~/.aws/", ">> ~/.aws/",
    "> /home/xiyo/.soloaiguy.env", "> /home/xiyo/.affiliates.local",
)

PIPE_TO_SHELL_PATTERNS = ("| sh", "| bash", "|sh ", "|bash ", "| sh\n", "| bash\n")
FORCE_PUSH_MAIN = ("git push --force origin main", "git push -f origin main",
                   "git push --force-with-lease origin main")

CRON_SCRIPTS = {
    "intel-cron": "scripts/intel-cron.sh",
    "exp-cron": "scripts/exp-cron.sh",
    "publish-cron": "scripts/publish-cron.sh",
    "social-cron": "scripts/social-cron.sh",
    "affiliate-injector": "scripts/affiliate-injector.py",
}

# write_file path policy
WRITE_DENY_SUFFIXES = (".env", ".env.local", ".env.production")
WRITE_DENY_BASENAMES = (
    ".soloaiguy.env", ".affiliates.local",
    ".aider.conf.yml", ".aider.architect.conf.yml",
)
WRITE_DENY_PATH_FRAGMENTS = ("/.ssh/", "/.aws/", "/.docker/")


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


def _bash_safety_check(cmd: str) -> str | None:
    """Return None if safe, or a denial reason string."""
    lc = cmd.lower()
    for pat in CATASTROPHIC_BASH_PATTERNS:
        if pat in cmd:
            return f"BLOCKED (catastrophic): command contains '{pat.strip()}'."
    for pat in SECRET_FILE_WRITE_PATTERNS:
        if pat in cmd:
            return f"BLOCKED (secret-file write): '{pat}'. If you need to update env vars, ask Xiyo to do it manually."
    for pat in PIPE_TO_SHELL_PATTERNS:
        if pat in lc:
            return (
                "BLOCKED (supply-chain risk): pipe-to-shell pattern detected. "
                "Download the script with curl/wget to a file first, READ it "
                "yourself to verify it isn't malicious, then run it explicitly."
            )
    for pat in FORCE_PUSH_MAIN:
        if pat in cmd:
            return f"BLOCKED (force-push to main): '{pat}'. Tell Xiyo what you wanted to overwrite and let them decide."
    return None


def handle_bash(command: str, timeout_seconds: int | None = None) -> str:
    cmd = command.strip()
    if not cmd:
        return "ERROR: empty command"
    denial = _bash_safety_check(cmd)
    if denial:
        return denial
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


def handle_read_file(path: str) -> str:
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
    if len(text) > 8000:
        text = text[:8000] + f"\n\n... (truncated at 8000 chars; full file is {len(text)} chars — read again with offset if you need more)"
    return text


def _write_path_denied(path: str, full: Path) -> str | None:
    name = full.name
    s = str(full)
    if name in WRITE_DENY_BASENAMES:
        return f"BLOCKED: '{name}' is a secret/config file."
    for suf in WRITE_DENY_SUFFIXES:
        if name.endswith(suf):
            return f"BLOCKED: writes to '{suf}' files are blocked (secrets)."
    for frag in WRITE_DENY_PATH_FRAGMENTS:
        if frag in s:
            return f"BLOCKED: path contains '{frag}' (sensitive directory)."
    return None


def handle_write_file(path: str, content: str) -> str:
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return f"DENIED: content exceeds {MAX_WRITE_BYTES} byte cap. Split into smaller files."
    full = _resolve_repo_path(path)
    if full is None:
        return f"DENIED: path '{path}' escapes repo root"
    denied = _write_path_denied(path, full)
    if denied:
        return denied
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
            return handle_read_file(params.get("path", ""))
        if name == "write_file":
            return handle_write_file(
                path=params.get("path", ""),
                content=params.get("content", ""),
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

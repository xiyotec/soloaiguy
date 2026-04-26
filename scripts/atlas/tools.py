"""Tool definitions and handlers for Atlas.

All tool handlers return a string (the tool_result content). They never raise —
errors are returned as text so Atlas can recover and tell the boss what failed.

Bash allowlist is intentionally narrow: read-only repo introspection plus the
named cron scripts. No `rm`, no `git push`, no shell metacharacters that aren't
bound by the parser. If a tool needs more, add it as a dedicated handler.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# Anthropic-side tool definitions (passed to messages.create as `tools=`).
TOOL_DEFS = [
    {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5,
    },
    {
        "name": "bash",
        "description": (
            "Run a read-only shell command in the soloaiguy repo. Allowlisted to: "
            "git (status, log, diff, show, branch, remote -v), ls, cat, head, tail, "
            "wc, grep, find, tree, npm run build, npm run dev (background only), "
            "node --version, python3 --version, du, df. NO rm/mv/cp/git push/git "
            "reset/curl/wget/chmod. For affiliate-injector, use --dry-run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run from the repo root.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file from the soloaiguy repo. Path is relative to repo root. "
            "Returns up to 8000 chars; ask for specific paths instead of trying to "
            "list directories with this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to repo root (e.g. 'pipeline/status.md').",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_cron",
        "description": (
            "Manually invoke one of the cron scripts. Use sparingly — these "
            "interact with Telegram and external state. Allowed names: "
            "intel-cron, exp-cron, publish-cron, social-cron, affiliate-injector. "
            "affiliate-injector accepts a 'dry_run' boolean."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": [
                        "intel-cron", "exp-cron", "publish-cron",
                        "social-cron", "affiliate-injector",
                    ],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Only valid for affiliate-injector. Default false.",
                },
                "env": {
                    "type": "object",
                    "description": (
                        "Optional env vars (e.g. {\"PUBLISH_DAYS_AHEAD\":\"7\"}). "
                        "Keys must be all-caps with underscores."
                    ),
                },
            },
            "required": ["name"],
        },
    },
]

ALLOWED_BASH_PREFIXES = (
    "git status", "git log", "git diff", "git show", "git branch", "git remote -v",
    "ls", "cat", "head", "tail", "wc", "grep", "find ", "tree",
    "npm run build", "node --version", "python3 --version",
    "du ", "df ",
)
DENIED_BASH_TOKENS = (
    "rm ", "mv ", "cp ", "chmod", "chown",
    "git push", "git reset", "git checkout", "git rebase", "git merge",
    "git commit", "git stash drop", "git clean",
    "curl", "wget", "ssh", "scp",
    " > ", " >> ", "|sh", "|bash", "$(", "`",
    "sudo", "su ", "kill", "pkill",
)

CRON_SCRIPTS = {
    "intel-cron": "scripts/intel-cron.sh",
    "exp-cron": "scripts/exp-cron.sh",
    "publish-cron": "scripts/publish-cron.sh",
    "social-cron": "scripts/social-cron.sh",
    "affiliate-injector": "scripts/affiliate-injector.py",
}


def _run_shell(cmd: str, timeout: int = 60, env: dict | None = None) -> str:
    proc_env = None
    if env:
        import os
        proc_env = {**os.environ, **env}
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
    return out[-6000:] if len(out) > 6000 else out


def handle_bash(command: str) -> str:
    cmd = command.strip()
    if not cmd:
        return "ERROR: empty command"
    for bad in DENIED_BASH_TOKENS:
        if bad in cmd:
            return f"DENIED: command contains '{bad.strip()}' which is on the deny list."
    if not any(cmd.startswith(p) for p in ALLOWED_BASH_PREFIXES):
        return (
            "DENIED: command does not start with an allowlisted prefix. "
            f"Allowed: {', '.join(ALLOWED_BASH_PREFIXES)}"
        )
    return _run_shell(cmd, timeout=60)


def handle_read_file(path: str) -> str:
    p = (REPO / path).resolve()
    try:
        p.relative_to(REPO)
    except ValueError:
        return f"DENIED: path '{path}' escapes repo root"
    if not p.exists():
        return f"NOT FOUND: {path}"
    if p.is_dir():
        return f"IS DIR: {path} — use 'bash' with 'ls' instead"
    try:
        text = p.read_text(errors="replace")
    except Exception as e:
        return f"READ ERROR: {e}"
    if len(text) > 8000:
        text = text[:8000] + f"\n\n... (truncated, file is {len(text)} chars total)"
    return text


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
            return handle_bash(params.get("command", ""))
        if name == "read_file":
            return handle_read_file(params.get("path", ""))
        if name == "run_cron":
            return handle_run_cron(
                name=params.get("name", ""),
                dry_run=bool(params.get("dry_run", False)),
                env=params.get("env"),
            )
        return f"UNKNOWN TOOL: {name}"
    except Exception as e:
        return f"HANDLER ERROR ({name}): {type(e).__name__}: {e}"

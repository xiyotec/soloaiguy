#!/usr/bin/env python3
"""atlas.py — Telegram chief-of-staff agent for soloaiguy.

Long-polls a dedicated Telegram bot, sends each message to Anthropic Claude with
tool use enabled, executes tools locally, and replies. State (conversation
history + spend) lives in SQLite at scripts/atlas/atlas.db.

Setup:
  1. Create a NEW bot via @BotFather → save token (must NOT be the same bot as
     intel-cron / publish-cron, or Telegram getUpdates will 409).
  2. Add to ~/.soloaiguy.env:
       export ATLAS_TELEGRAM_BOT_TOKEN="..."
       export ATLAS_TELEGRAM_CHAT_ID="..."   # your chat with the new bot
       export ANTHROPIC_API_KEY="sk-ant-..."
  3. Run:
       ./scripts/atlas/atlas.py

Run as a service (recommended):
  tmux new -d -s atlas '/home/xiyo/builds/soloaiguy/scripts/atlas/atlas.py 2>&1 | tee -a /home/xiyo/builds/soloaiguy/scripts/atlas-log/atlas.log'

Cost guard:
  Hard cap is $25/month. Atlas refuses to call the API beyond that.
  Soft warn at $20. Tracked in SQLite.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
import tools as atlas_tools  # noqa: E402
import system_prompt as atlas_prompt  # noqa: E402

# --- config ---------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(__file__).parent / "atlas.db"
LOG_DIR = REPO / "scripts" / "atlas-log"

MODEL = os.environ.get("ATLAS_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 2048
MAX_TURNS_PER_MESSAGE = 8       # tool-use loop iterations
HISTORY_TURNS = 12              # user/assistant exchanges to keep in context

MONTHLY_HARD_CAP_USD = 25.00
MONTHLY_SOFT_WARN_USD = 20.00

# Pricing per 1M tokens. Keep in sync with anthropic.com/pricing.
# claude-haiku-4-5: $1 input / $5 output. Sonnet 4.6: $3 / $15. Opus 4.7: $15 / $75.
PRICING = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
}

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("atlas")

# --- env -----------------------------------------------------------------

def _load_env() -> None:
    env_file = Path.home() / ".soloaiguy.env"
    if not env_file.exists():
        return
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"\'')
        os.environ.setdefault(k.strip(), v)

_load_env()

TG_TOKEN = os.environ.get("ATLAS_TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("ATLAS_TELEGRAM_CHAT_ID", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

if not TG_TOKEN or not TG_CHAT:
    log.error("Missing ATLAS_TELEGRAM_BOT_TOKEN or ATLAS_TELEGRAM_CHAT_ID in ~/.soloaiguy.env")
    sys.exit(1)
if not ANTHROPIC_KEY:
    log.error("Missing ANTHROPIC_API_KEY in ~/.soloaiguy.env")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# --- db ------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            role TEXT NOT NULL,                 -- 'user' or 'assistant'
            content_json TEXT NOT NULL          -- full anthropic content blocks (list)
        );
        CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages(chat_id, ts);

        CREATE TABLE IF NOT EXISTS spend (
            day TEXT PRIMARY KEY,               -- YYYY-MM-DD
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            usd REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    return conn


def load_history(chat_id: str, n: int = HISTORY_TURNS * 2) -> list[dict]:
    """Return the last N message rows in Anthropic format (oldest first)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT role, content_json FROM messages "
            "WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, n),
        ).fetchall()
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": json.loads(r["content_json"])} for r in rows]


def save_message(chat_id: str, role: str, content: list) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, ts, role, content_json) VALUES (?, ?, ?, ?)",
            (chat_id, datetime.datetime.utcnow().isoformat(), role, json.dumps(content)),
        )
        conn.commit()


def get_state(key: str, default: str = "") -> str:
    with _db() as conn:
        row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


# --- spend tracking ------------------------------------------------------

def _price(model: str, in_toks: int, out_toks: int) -> float:
    in_rate, out_rate = PRICING.get(model, (3.0, 15.0))
    return (in_toks * in_rate + out_toks * out_rate) / 1_000_000


def record_spend(model: str, in_toks: int, out_toks: int) -> tuple[float, float]:
    """Returns (today_usd, month_to_date_usd)."""
    today = datetime.date.today().isoformat()
    cost = _price(model, in_toks, out_toks)
    with _db() as conn:
        conn.execute(
            "INSERT INTO spend (day, input_tokens, output_tokens, usd) VALUES (?,?,?,?) "
            "ON CONFLICT(day) DO UPDATE SET "
            "input_tokens = input_tokens + excluded.input_tokens, "
            "output_tokens = output_tokens + excluded.output_tokens, "
            "usd = usd + excluded.usd",
            (today, in_toks, out_toks, cost),
        )
        conn.commit()
        today_usd = conn.execute("SELECT usd FROM spend WHERE day = ?", (today,)).fetchone()["usd"]
        month_prefix = today[:7]
        mtd = conn.execute(
            "SELECT COALESCE(SUM(usd), 0) AS s FROM spend WHERE day LIKE ?",
            (f"{month_prefix}%",),
        ).fetchone()["s"]
    return today_usd, mtd


def month_to_date_usd() -> float:
    month_prefix = datetime.date.today().isoformat()[:7]
    with _db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(usd), 0) AS s FROM spend WHERE day LIKE ?",
            (f"{month_prefix}%",),
        ).fetchone()
    return row["s"]


# --- telegram ------------------------------------------------------------

def tg_send(text: str) -> None:
    # Telegram cap is 4096 chars. Chunk if needed.
    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)] or [""]
    for chunk in chunks:
        data = json.dumps({
            "chat_id": TG_CHAT,
            "text": chunk,
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except urllib.error.HTTPError as e:
            log.error("Telegram send failed: %s — %s", e.code, e.read().decode("utf-8", "replace"))
        except Exception as e:
            log.error("Telegram send failed: %s", e)


def tg_typing() -> None:
    try:
        data = urllib.parse.urlencode({"chat_id": TG_CHAT, "action": "typing"}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction",
            data=data, timeout=5,
        ).read()
    except Exception:
        pass


def tg_poll_loop():
    """Yield (text, message_id) for each new message from the configured chat."""
    offset = int(get_state("tg_offset", "0") or 0)
    log.info("starting Telegram long-poll from offset %s", offset)
    while True:
        url = (
            f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
            f"?offset={offset}&timeout=30&allowed_updates=%5B%22message%22%5D"
        )
        try:
            with urllib.request.urlopen(url, timeout=40) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            log.error("getUpdates HTTP %s: %s", e.code, body[:300])
            if e.code == 409:
                log.error("409 conflict — another poller is using this bot. Sleeping 30s.")
            time.sleep(15 if e.code == 409 else 5)
            continue
        except Exception as e:
            log.error("getUpdates failed: %s", e)
            time.sleep(5)
            continue

        for upd in data.get("result", []):
            offset = max(offset, upd.get("update_id", 0) + 1)
            set_state("tg_offset", str(offset))
            msg = upd.get("message") or {}
            chat = msg.get("chat") or {}
            if str(chat.get("id", "")) != str(TG_CHAT):
                continue
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            yield text, msg.get("message_id", 0)


# --- agent loop ----------------------------------------------------------

def _content_for_message(msg: dict) -> list:
    """Anthropic message blocks → JSON-serializable list."""
    out = []
    for block in msg.get("content", []) if isinstance(msg, dict) else msg.content:
        if hasattr(block, "model_dump"):
            out.append(block.model_dump())
        elif isinstance(block, dict):
            out.append(block)
    return out


def _extract_text(content: list) -> str:
    parts = []
    for b in content:
        if isinstance(b, dict):
            if b.get("type") == "text":
                parts.append(b.get("text", ""))
        else:
            if getattr(b, "type", None) == "text":
                parts.append(getattr(b, "text", ""))
    return "\n".join(p for p in parts if p).strip()


def handle_user_message(chat_id: str, user_text: str) -> None:
    # cost guard
    mtd = month_to_date_usd()
    if mtd >= MONTHLY_HARD_CAP_USD:
        tg_send(
            f"Hit the ${MONTHLY_HARD_CAP_USD:.0f}/mo Anthropic spend cap "
            f"(${mtd:.2f} so far). Bump the cap in atlas.py if you really need more."
        )
        return

    history = load_history(chat_id)
    user_block = [{"type": "text", "text": user_text}]
    save_message(chat_id, "user", user_block)
    history.append({"role": "user", "content": user_block})

    system_text = atlas_prompt.build()
    tg_typing()

    for turn in range(MAX_TURNS_PER_MESSAGE):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_text,
                tools=atlas_tools.TOOL_DEFS,
                messages=history,
            )
        except anthropic.APIError as e:
            log.error("Anthropic API error: %s", e)
            tg_send(f"API error talking to Claude: {e}. Try again in a sec.")
            return

        in_toks = resp.usage.input_tokens
        out_toks = resp.usage.output_tokens
        _, mtd = record_spend(MODEL, in_toks, out_toks)

        assistant_content = _content_for_message(resp)
        save_message(chat_id, "assistant", assistant_content)
        history.append({"role": "assistant", "content": assistant_content})

        if resp.stop_reason != "tool_use":
            text = _extract_text(assistant_content)
            if not text:
                text = "(empty reply)"
            if mtd >= MONTHLY_SOFT_WARN_USD and mtd < MONTHLY_HARD_CAP_USD:
                text += f"\n\n[atlas: $${mtd:.2f}/mo of ${MONTHLY_HARD_CAP_USD:.0f} cap]"
            tg_send(text)
            return

        # Run all requested tools, gather results.
        tool_results = []
        for block in assistant_content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool_name = block.get("name", "")
            tool_input = block.get("input", {}) or {}
            tool_id = block.get("id", "")
            log.info("tool: %s args=%s", tool_name, json.dumps(tool_input)[:200])
            if tool_name == "web_search":
                # Server-side tool — Anthropic handles it; don't dispatch locally.
                continue
            result = atlas_tools.dispatch(tool_name, tool_input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result,
            })

        if not tool_results:
            # Either web_search only (server-side), or no actionable tools — let
            # the next API call resolve it.
            continue

        save_message(chat_id, "user", tool_results)
        history.append({"role": "user", "content": tool_results})
        tg_typing()

    tg_send("(hit max tool-use turns — bailing out. Ask me to continue if needed.)")


def main() -> int:
    log.info("Atlas online. model=%s mtd=$%.2f", MODEL, month_to_date_usd())
    for text, _msg_id in tg_poll_loop():
        log.info("user: %s", text[:200])
        try:
            handle_user_message(str(TG_CHAT), text)
        except Exception as e:
            log.exception("handler crashed")
            tg_send(f"Crashed: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

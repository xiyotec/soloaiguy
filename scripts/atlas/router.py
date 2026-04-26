"""Router — sends simple chitchat to local Ollama instead of Anthropic.

Heuristic gate (no LLM-classifier, that defeats the savings): if the message
looks like an acknowledgment, greeting, short question, or quick clarification
with no tool intent, hand it to Ollama. Anything that smells like real work
falls through to Sonnet.

Disable with ATLAS_ROUTING=off. Override model with ATLAS_LOCAL_MODEL.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.environ.get("ATLAS_LOCAL_MODEL", "qwen2.5-coder:7b")
ROUTING_ENABLED = os.environ.get("ATLAS_ROUTING", "on").lower() not in ("off", "0", "false")
OLLAMA_TIMEOUT_S = 30
LOCAL_REPLY_MAX_CHARS = 1200

log = logging.getLogger("atlas.router")

# Verbs that imply tools / agentic work — escalate to Sonnet.
_TOOL_VERBS = re.compile(
    r"\b(edit|write|create|change|update|fix|deploy|push|commit|merge|run|exec|"
    r"install|uninstall|search|google|look up|lookup|find|check|browse|download|"
    r"upload|read|cat|grep|cron|publish|draft|refactor|review|build|test|lint|"
    r"generate|make|add|remove|delete|kill|start|stop|restart|open|close|setup|"
    r"set up|configure|schedule|register|sign up|sign in|crawl|scrape|audit|"
    r"benchmark|profile|measure|count|list|show me)\b",
    re.I,
)

# Code / file path / URL signals — escalate.
_CODE_PATH = re.compile(r"```|\.py\b|\.js\b|\.ts\b|\.md\b|\.sh\b|\.css\b|\.html\b|\.json\b|\.toml\b|\.yaml\b|\.yml\b|/[a-z_][a-z0-9_/.-]+/[a-z_]")
_URL = re.compile(r"https?://|www\.|@[a-z0-9_]{3,}", re.I)


def should_route_local(text: str, has_image: bool, last_assistant_used_tools: bool) -> bool:
    if not ROUTING_ENABLED:
        return False
    if not text or not text.strip():
        return False
    if has_image:
        return False
    if last_assistant_used_tools:
        # Mid tool-use round — keep Sonnet on it for continuity.
        return False
    if len(text) > 400:
        return False
    if _TOOL_VERBS.search(text):
        return False
    if _CODE_PATH.search(text):
        return False
    if _URL.search(text):
        return False
    return True


def _short_persona() -> str:
    """Compact Atlas persona for Ollama. The huge LIVE STATE block in
    system_prompt.build() is wasted on a 7B model handling chitchat."""
    return (
        "You are Atlas, Xiyo's partner running soloaiguy.com — a solo-founder AI "
        "blog. Address Xiyo by name, never 'boss'.\n"
        "Personality: dry, direct, brutally honest. No corporate fluff. Brevity is "
        "respect — 1-3 short paragraphs max. Skip the wind-up, give the answer first.\n"
        "You're answering quick conversational messages. If the question needs tools, "
        "web research, file edits, or live project state, say so plainly and tell Xiyo "
        "to ask again with more specifics so the heavier model picks it up."
    )


def ollama_reply(user_text: str, history_text: list[tuple[str, str]] | None = None) -> str:
    """Call Ollama. Raises on failure so caller can fall back to Sonnet."""
    msgs: list[dict] = [{"role": "system", "content": _short_persona()}]
    for role, text in (history_text or [])[-6:]:
        if role in ("user", "assistant") and text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": user_text})

    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": msgs,
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 600},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_S) as resp:
        data = json.loads(resp.read())

    text = (data.get("message") or {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Ollama returned empty content")
    if len(text) > LOCAL_REPLY_MAX_CHARS:
        text = text[:LOCAL_REPLY_MAX_CHARS] + "…"
    return text


def estimate_anthropic_cost_usd(input_chars: int, output_chars: int) -> float:
    """Rough — assumes ~4 chars/token, Sonnet 4.6 pricing ($3 in / $15 out per 1M).
    Just for the savings counter on local replies; not used for accounting."""
    in_toks = input_chars / 4
    out_toks = output_chars / 4
    return (in_toks * 3.0 + out_toks * 15.0) / 1_000_000

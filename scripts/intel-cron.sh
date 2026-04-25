#!/usr/bin/env bash
#
# Daily AI-intel briefing with Telegram approval.
#
# Each morning:
#   1. Pull AI signal from HN + r/LocalLLaMA (last 24h).
#   2. Ollama synthesizes ONE actionable pick + 3 numbered options.
#   3. Send to Telegram, wait up to 15 min for a reply.
#   4. Act on the reply:
#       1     → flag pick as "try on stack" (logs only — no auto-shell)
#       2     → scaffold a DRAFT post (frontmatter draft: true, never auto-published)
#       3     → append idea to keyword-queue.md buffer
#       skip / no reply → log only
#
# Safety rails (matches the project's 90-day no-auto-outbound rule):
#   - All scaffolded posts are draft: true. No auto-publish.
#   - No shell commands are executed from the LLM brief.
#   - No API spend, no DNS/billing changes.
#   - Without TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, the brief is just logged.
#
# Cron entry (06:00 daily, after research at 02:30 and social at 03:00):
#   0 6 * * * /home/xiyo/builds/soloaiguy/scripts/intel-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/cron.log 2>&1
#
# Manual run:
#   scripts/intel-cron.sh

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
QUEUE="$REPO/pipeline/keyword-queue.md"
POSTS_DIR="$REPO/src/content/posts"
LOG_DIR="$REPO/scripts/intel-log"
TODAY="$(date -u +%Y-%m-%d)"

mkdir -p "$LOG_DIR" "$POSTS_DIR"

# Load gitignored env vars if present (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).
# Lives at ~/.soloaiguy.env — separate from ~/.affiliates.local (which is a
# YAML-style notes file for affiliate IDs, not bash-sourceable).
[[ -f "$HOME/.soloaiguy.env" ]] && source "$HOME/.soloaiguy.env"

export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
export OLLAMA_URL="${OLLAMA_API_BASE:-http://localhost:11434}"
export TG_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
export TG_CHAT="${TELEGRAM_CHAT_ID:-}"
WAIT_SECS="${INTEL_WAIT_SECS:-900}"

LOG_FILE="$LOG_DIR/$TODAY.md"
echo "# Intel briefing — $(date -u --iso-8601=seconds)" >> "$LOG_FILE"

log() { echo "[$(date -u --iso-8601=seconds)] $*" | tee -a "$LOG_FILE" >&2 ; }

# --- 1. Gather signal ---

log "fetching HN signal..."
hn_since=$(( $(date +%s) - 86400 ))
# Algolia rejects literal `>` in numericFilters — must URL-encode via --data-urlencode.
# Plain-text query also treats "OR" as a literal word; single broad keyword + Ollama
# filtering is more robust than multi-term boolean.
hn_signal="$(curl -fsS --get \
  --data-urlencode "tags=story" \
  --data-urlencode "numericFilters=created_at_i>${hn_since},points>30" \
  --data-urlencode "query=AI" \
  "https://hn.algolia.com/api/v1/search" \
  | python3 -c '
import json, sys
data = json.loads(sys.stdin.read())
hits = data.get("hits", [])[:10]
out = []
for h in hits:
    title = h.get("title") or ""
    oid = h.get("objectID", "")
    url = h.get("url") or f"https://news.ycombinator.com/item?id={oid}"
    pts = h.get("points", 0)
    out.append(f"- [{pts} pts] {title} — {url}")
print("\n".join(out) or "(no signal)")
' 2>/dev/null || echo "(HN fetch failed)")"

log "fetching r/LocalLLaMA signal..."
reddit_signal="$(curl -fsS -A "Mozilla/5.0 (intel-cron)" \
  "https://www.reddit.com/r/LocalLLaMA/top.json?t=day&limit=10" \
  | python3 -c '
import json, sys
data = json.loads(sys.stdin.read())
posts = data.get("data", {}).get("children", [])
out = []
for p in posts[:10]:
    d = p.get("data", {})
    title = d.get("title", "")
    score = d.get("score", 0)
    permalink = d.get("permalink", "")
    out.append(f"- [{score} pts] {title} — https://reddit.com{permalink}")
print("\n".join(out) or "(no signal)")
' 2>/dev/null || echo "(Reddit fetch failed)")"

{
  echo ""
  echo "## Hacker News (last 24h)"
  echo "$hn_signal"
  echo ""
  echo "## r/LocalLLaMA (last 24h)"
  echo "$reddit_signal"
  echo ""
} >> "$LOG_FILE"

# --- 2. Synthesize via Ollama ---

log "synthesizing brief via $OLLAMA_MODEL..."

prompt="You are an editor for a niche tech blog 'Solo AI Guy' (https://soloaiguy.com).
Audience: solo developers running AI on consumer GPUs (RTX 3070-tier).

Signal from Hacker News (last 24h):
$hn_signal

Signal from r/LocalLLaMA (last 24h):
$reddit_signal

Pick the SINGLE most actionable item for solo builders. Then output EXACTLY this format — no preamble, no closing remarks, no extra sections:

## Today's pick
<one-line summary of the finding/tool/release>

## Why it matters
<one sentence — what changes for solo devs running AI locally>

## Actions
1. Try it: <specific concrete experiment with named tools/commands>
2. Draft a post: <specific angle and primary keyword>
3. Queue idea: <one-line topic to add to the buffer>

Be specific. Use real names (model versions, repo names, commands). No filler. If signal is weak, say so plainly in 'Today's pick' and propose generic but specific options."

body="$(printf '{"model":"%s","prompt":%s,"stream":false}' \
  "$OLLAMA_MODEL" \
  "$(printf '%s' "$prompt" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')")"

brief="$(curl -fsS -X POST "$OLLAMA_URL/api/generate" \
  -H 'Content-Type: application/json' \
  -d "$body" \
  | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("response","").strip())')"

if [[ -z "$brief" ]]; then
  log "ERROR: empty brief from Ollama"
  exit 1
fi

{
  echo "## Brief"
  echo "$brief"
  echo ""
} >> "$LOG_FILE"

# Extract the "Today's pick" line for fallback use
pick_line="$(echo "$brief" \
  | awk '/^## *Today.s pick/{getline; print; exit}' \
  | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
[[ -z "$pick_line" ]] && pick_line="AI development on $TODAY"

# --- 3. Send to Telegram (or exit if no creds) ---

if [[ -z "$TG_TOKEN" || -z "$TG_CHAT" ]]; then
  log "Telegram: SKIPPED (TELEGRAM_BOT_TOKEN/CHAT_ID not set in ~/.soloaiguy.env)"
  log "brief saved to $LOG_FILE — read manually or set up Telegram (see scripts/INTEL_SETUP.md)"
  exit 0
fi

# Capture baseline update_id so we ignore stale messages
baseline="$(curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/getUpdates?limit=1&offset=-1" \
  | python3 -c '
import json, sys
d = json.loads(sys.stdin.read())
r = d.get("result", [])
print(r[-1]["update_id"] if r else 0)
' 2>/dev/null || echo 0)"

log "sending to Telegram (chat=$TG_CHAT)..."
tg_text="Solo AI Guy — intel ${TODAY}

${brief}

Reply 1, 2, 3, or skip within $((WAIT_SECS / 60))m."

TG_TEXT_ENV="$tg_text" python3 <<'PYEOF' >/dev/null
import os, json, urllib.request, urllib.error, sys
data = json.dumps({
  'chat_id': os.environ['TG_CHAT'],
  'text': os.environ['TG_TEXT_ENV'],
  'disable_web_page_preview': True,
}).encode()
req = urllib.request.Request(
  f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
  data=data,
  headers={'Content-Type': 'application/json'},
)
try:
    urllib.request.urlopen(req).read()
except urllib.error.HTTPError as e:
    sys.stderr.write("Telegram send error: " + e.read().decode() + "\n")
    sys.exit(1)
PYEOF

# Long-poll for reply
log "waiting up to $((WAIT_SECS / 60)) min for reply..."
deadline=$(($(date +%s) + WAIT_SECS))
offset=$((baseline + 1))
action=""

while [[ $(date +%s) -lt $deadline ]]; do
  remaining=$((deadline - $(date +%s)))
  to=$(( remaining > 30 ? 30 : remaining ))
  resp="$(curl -fsS --max-time $((to + 5)) \
    "https://api.telegram.org/bot${TG_TOKEN}/getUpdates?offset=${offset}&timeout=${to}" \
    || echo '{"result":[]}')"

  parsed="$(echo "$resp" | python3 -c '
import json, sys, os
d = json.loads(sys.stdin.read())
chat_id = str(os.environ.get("TG_CHAT", ""))
last_uid = 0
match = ""
for u in d.get("result", []):
    last_uid = u.get("update_id", last_uid)
    msg = u.get("message") or {}
    if str(msg.get("chat", {}).get("id", "")) != chat_id:
        continue
    text = (msg.get("text") or "").strip().lower()
    if text in ("1", "2", "3", "skip") and not match:
        match = text
print(f"{last_uid}|{match}")
' 2>/dev/null || echo '0|')"

  last_uid="${parsed%|*}"
  match="${parsed#*|}"

  if [[ "$last_uid" != "0" && "$last_uid" -gt "$((offset - 1))" ]]; then
    offset=$((last_uid + 1))
  fi
  if [[ -n "$match" ]]; then
    action="$match"
    break
  fi
done

if [[ -z "$action" ]]; then
  log "no reply within window — defaulting to skip"
  action="skip"
fi

log "action: $action"

# --- 4. Act ---

slugify() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
    | cut -c1-60
}

result_msg=""
case "$action" in
  1)
    # "Try it" — hand the brief to the auto-experiment harness. exp-cron.sh
    # creates a sandboxed worktree, runs architect-mode aider with tight
    # constraints (banned-paths list, default-to-skip), runs `npm run build`,
    # and auto-merges to LOCAL main only if the build passes. It NEVER pushes
    # to origin — deploy stays a manual step.
    if [ -x "$REPO/scripts/exp-cron.sh" ]; then
      log "Action 1: handing off to exp-cron.sh (background)"
      nohup "$REPO/scripts/exp-cron.sh" "$LOG_FILE" \
        >>"$REPO/scripts/cron.log" 2>&1 &
      result_msg="Action 1: experiment launched. exp-cron will Telegram the result when done (build verify + auto-merge to local main if safe)."
    else
      result_msg="Action 1: flagged for manual try (exp-cron.sh not executable). See $LOG_FILE."
    fi
    log "$result_msg"
    ;;
  2)
    angle_line="$(echo "$brief" | grep -iE '^[[:space:]]*2\.' | head -1 \
      | sed -E 's/^[[:space:]]*2\.[[:space:]]*(Draft a post:?)?[[:space:]]*//i')"
    [[ -z "$angle_line" ]] && angle_line="$pick_line"
    slug="$(slugify "$angle_line")"
    [[ -z "$slug" ]] && slug="intel-${TODAY}"
    out="$POSTS_DIR/$slug.md"
    if [[ -f "$out" ]]; then
      result_msg="Action 2: draft already exists at $out — not overwriting."
      log "$result_msg"
    else
      cat > "$out" <<DRAFT
---
title: "${angle_line}"
description: "TODO: one-sentence pain → promise."
pubDate: ${TODAY}
tags: ["intel-scaffold"]
draft: true
---

## The problem

<TODO from intel ${TODAY}>

## Source signal

\`\`\`
${pick_line}
\`\`\`

## What I tried

<TODO>

## What worked

<TODO>

## What didn't

<TODO>

---

_Auto-scaffolded by intel-cron on ${TODAY}. draft: true — review, fill in real numbers, then flip to false._
DRAFT
      result_msg="Action 2: scaffolded draft at src/content/posts/$slug.md (draft: true)."
      log "$result_msg"
    fi
    ;;
  3)
    idea_line="$(echo "$brief" | grep -iE '^[[:space:]]*3\.' | head -1 \
      | sed -E 's/^[[:space:]]*3\.[[:space:]]*(Queue idea:?)?[[:space:]]*//i')"
    [[ -z "$idea_line" ]] && idea_line="$pick_line"
    if grep -Fq "$idea_line" "$QUEUE" 2>/dev/null; then
      result_msg="Action 3: idea already in queue — not duplicating."
      log "$result_msg"
    else
      printf '\n- %s _(intel %s)_\n' "$idea_line" "$TODAY" >> "$QUEUE"
      result_msg="Action 3: appended to keyword-queue.md."
      log "$result_msg"
    fi
    ;;
  skip)
    result_msg="Skipped — no action taken."
    log "$result_msg"
    ;;
esac

# Confirmation back to Telegram (best-effort; don't fail the run on this)
TG_CONFIRM_ENV="$result_msg" python3 <<'PYEOF' >/dev/null 2>&1 || true
import os, json, urllib.request
data = json.dumps({
  'chat_id': os.environ['TG_CHAT'],
  'text': os.environ['TG_CONFIRM_ENV'],
  'disable_web_page_preview': True,
}).encode()
req = urllib.request.Request(
  f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
  data=data,
  headers={'Content-Type': 'application/json'},
)
urllib.request.urlopen(req).read()
PYEOF

log "done"

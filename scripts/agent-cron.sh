#!/usr/bin/env bash
#
# Scheduled-agent template.
#
# Runs an agent against a single topic from the keyword queue and writes its
# output to pipeline/research/<date>-<slug>.md for review the next morning.
#
# Designed for:
#   - cron (overnight)
#   - manual invocation (testing)
#
# Defaults to using local Aider+Ollama. Switch AGENT to "claude" if you want
# to use Anthropic credits — pricier but better research depth.
#
# Idempotent: rerunning on the same day overwrites that day's research file.
# Designed to fail loudly so cron emails reach you when something breaks.
#
# Usage:
#   scripts/agent-cron.sh             # picks the next un-researched queue item
#   scripts/agent-cron.sh <slug>      # forces a specific slug
#   AGENT=claude scripts/agent-cron.sh
#
# Cron entry (3am daily):
#   0 3 * * * /home/xiyo/builds/soloaiguy/scripts/agent-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/results/cron.log 2>&1

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
QUEUE="$REPO/pipeline/keyword-queue.md"
RESEARCH_DIR="$REPO/pipeline/research"
TODAY="$(date -u +%Y-%m-%d)"
AGENT="${AGENT:-aider}"

if [[ ! -f "$QUEUE" ]]; then
  echo "ERROR: queue file not found: $QUEUE" >&2
  exit 1
fi

mkdir -p "$RESEARCH_DIR"

# --- pick the slug ---
slug="${1:-}"

slugify() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
    | cut -c1-80
}

if [[ -z "$slug" ]]; then
  # Parse the high-priority table: "| <num> | <title> | ..."
  while IFS= read -r line; do
    title="$(echo "$line" | awk -F'|' '{print $3}' | sed -E 's/^ +//; s/ +$//')"
    [[ -z "$title" ]] && continue
    candidate="$(slugify "$title")"
    [[ -z "$candidate" ]] && continue
    # Skip if a research file for this slug already exists (any date).
    if ! ls "$RESEARCH_DIR" 2>/dev/null | grep -q -- "-$candidate\.md\$"; then
      slug="$candidate"
      break
    fi
  done < <(grep -E '^\| +[0-9]+ +\|' "$QUEUE")
fi

if [[ -z "$slug" ]]; then
  echo "INFO: nothing new to research — every queue item already has a research file." >&2
  exit 0
fi

OUT_FILE="$RESEARCH_DIR/$TODAY-$slug.md"
PROMPT="Research the topic '$slug' for a blog post in the niche 'local-first AI for solo builders'.
Output a concise research brief in markdown with these sections:
1. Audience pain in one sentence
2. Top 5 sub-questions a reader would have
3. Five concrete data points or commands worth including (be specific — model names, version numbers, command flags)
4. Two competing posts already ranking for this term and what they miss
5. A recommended angle for our post that beats them

Be specific. No marketing prose. If you're guessing, say so."

# --- ensure environment ---
export NVM_DIR="$HOME/.nvm"
[[ -s "$NVM_DIR/nvm.sh" ]] && \. "$NVM_DIR/nvm.sh" || true

start_ts="$(date -u +%s)"
echo "[$(date -u --iso-8601=seconds)] researching: $slug (agent=$AGENT)" >&2

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
OLLAMA_URL="${OLLAMA_API_BASE:-http://localhost:11434}"

case "$AGENT" in
  ollama|aider)
    # Stream from Ollama directly — it's purpose-built for "answer this prompt".
    # Aider was wrong here: it's an *editing* tool, and a research brief isn't
    # an edit. The model would chat back and Aider would commit nothing.
    cat > "$OUT_FILE" <<EOF
# Research brief — $slug

_Started: $(date -u --iso-8601=seconds). Model: $MODEL._

EOF
    body="$(printf '{"model":"%s","prompt":%s,"stream":false}' \
      "$MODEL" \
      "$(printf '%s' "$PROMPT" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')")"
    response="$(curl -fsS -X POST "$OLLAMA_URL/api/generate" \
      -H 'Content-Type: application/json' \
      -d "$body")"
    echo "$response" \
      | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("response",""))' \
      >> "$OUT_FILE"
    ;;
  claude)
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      echo "ERROR: AGENT=claude requires ANTHROPIC_API_KEY" >&2
      exit 1
    fi
    cat > "$OUT_FILE" <<EOF
# Research brief — $slug

_Started: $(date -u --iso-8601=seconds). Agent: claude._

EOF
    claude --print "$PROMPT" >> "$OUT_FILE"
    ;;
  *)
    echo "ERROR: unknown AGENT: $AGENT (use ollama, aider, or claude)" >&2
    exit 1
    ;;
esac

end_ts="$(date -u +%s)"
echo "[$(date -u --iso-8601=seconds)] done: $slug ($((end_ts - start_ts))s) → $OUT_FILE" >&2

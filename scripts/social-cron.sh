#!/usr/bin/env bash
#
# Social-draft generator.
#
# For every published post (draft != true) that doesn't yet have a draft file
# at pipeline/social/<slug>.md, ask Ollama to write HN/Reddit/Twitter/LinkedIn
# variants. Output is a *draft* — user reviews and posts manually (no outbound
# actions auto-fire, per project safety rails).
#
# Usage:
#   scripts/social-cron.sh             # all eligible posts
#   scripts/social-cron.sh <slug>      # single post by slug
#
# Cron entry (daily at 03:00, after research agent):
#   0 3 * * * /home/xiyo/builds/soloaiguy/scripts/social-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/cron.log 2>&1

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
POSTS_DIR="$REPO/src/content/posts"
SOCIAL_DIR="$REPO/pipeline/social"
SITE_URL="${SITE_URL:-https://soloaiguy.com}"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
OLLAMA_URL="${OLLAMA_API_BASE:-http://localhost:11434}"

mkdir -p "$SOCIAL_DIR"

extract_frontmatter() {
  # $1 = key, $2 = file
  awk -v k="$1" '
    /^---$/ { if (++c == 2) exit; next }
    c == 1 && $0 ~ "^"k":" {
      sub(/^[^:]+:[[:space:]]*/, "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$2"
}

is_draft() {
  [[ "$(extract_frontmatter draft "$1")" == "true" ]]
}

ollama_generate() {
  local prompt="$1"
  local body
  body="$(printf '{"model":"%s","prompt":%s,"stream":false}' \
    "$MODEL" \
    "$(printf '%s' "$prompt" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')")"
  curl -fsS -X POST "$OLLAMA_URL/api/generate" \
    -H 'Content-Type: application/json' \
    -d "$body" \
    | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("response",""))'
}

generate_for_post() {
  local post_file="$1"
  local base
  base="$(basename "$post_file")"
  local slug="${base%.md}"
  slug="${slug%.mdx}"
  local out="$SOCIAL_DIR/$slug.md"

  if [[ -f "$out" ]]; then
    echo "[skip] $slug — drafts already exist at $out" >&2
    return 0
  fi

  if is_draft "$post_file"; then
    echo "[skip] $slug — frontmatter draft: true" >&2
    return 0
  fi

  local title description post_url
  title="$(extract_frontmatter title "$post_file")"
  description="$(extract_frontmatter description "$post_file")"
  post_url="$SITE_URL/posts/$slug/"

  echo "[$(date -u --iso-8601=seconds)] generating drafts for $slug" >&2

  local prompt
  prompt="You are drafting social posts for a niche tech blog called Solo AI Guy ($SITE_URL).
The audience is solo developers and hobbyists running AI on consumer GPUs.

Post details:
- Title: $title
- Description: $description
- URL: $post_url

Write FOUR distinct social drafts. Output as plain markdown sections — no preamble, no closing remarks.

## Hacker News
- One title only. Follow HN guidelines: factual, no editorializing, no clickbait, no emoji, no \"How I\". Match the article's actual headline if it's already neutral.

## Reddit
Provide subreddit-appropriate posts for THREE subs. Each as: title on one line, then a short body (3-6 sentences). No links in body — link goes in the post. Subs:
- r/LocalLLaMA (technical, model-focused readers)
- r/selfhosted (people running their own infra)
- r/programming (broader dev audience — frame the technical insight)

## Twitter / X thread
5–7 numbered tweets (1/, 2/, ...). First tweet hooks with a specific number or claim from the post. Last tweet links to $post_url. No hashtags. Each tweet under 270 chars.

## LinkedIn
One single post (~150 words). Slightly more formal. Lead with the surprising finding. End with a soft CTA pointing readers to the full post.

Be specific. Use real claims and numbers from the post if you know them; otherwise, write framing that requires the reader to click for the data."

  {
    cat <<EOF
# Social drafts — $slug

_Generated $(date -u --iso-8601=seconds). Model: $MODEL. URL: $post_url._

> **Review before posting.** These are LLM-generated drafts. Confirm any specific claim or number against the post itself before submitting.

EOF
    ollama_generate "$prompt"
  } > "$out"

  echo "[$(date -u --iso-8601=seconds)] done: $slug → $out" >&2
}

# --- main ---
slug_filter="${1:-}"
processed=0

shopt -s nullglob
for post in "$POSTS_DIR"/*.md "$POSTS_DIR"/*.mdx; do
  [[ -f "$post" ]] || continue
  base="$(basename "$post")"
  this_slug="${base%.md}"
  this_slug="${this_slug%.mdx}"

  if [[ -n "$slug_filter" && "$this_slug" != "$slug_filter" ]]; then
    continue
  fi

  generate_for_post "$post"
  processed=$((processed + 1))
done

if [[ $processed -eq 0 ]]; then
  echo "[$(date -u --iso-8601=seconds)] no posts processed (filter='$slug_filter')" >&2
fi

#!/usr/bin/env bash
#
# publish-cron.sh — flip pubDate-due drafts to live, with Telegram approval.
#
# Daily scan of src/content/posts/. For each post where:
#   - frontmatter has `draft: true`
#   - pubDate <= today + PUBLISH_DAYS_AHEAD (default 1)
#
# Telegram the user with title + future URL and three options:
#   publish  → flip draft to false, npm run build, git commit, git push origin
#   defer    → bump pubDate by +7 days, commit (no push)
#   skip / no reply → leave alone
#
# This is the ONLY cron that pushes to origin. exp-cron and intel-cron stay
# local-only by design. Push triggers the GH Pages deploy workflow.
#
# Safety:
#   - Aborts if working tree is dirty (refuses to mix unrelated changes into
#     a publish commit).
#   - Build must pass before push; failed build reverts the draft flip.
#   - Without TELEGRAM_BOT_TOKEN/CHAT_ID, lists due drafts to log and exits.
#
# Cron entry (08:00 daily, after intel-cron at 06:00):
#   0 8 * * * /home/xiyo/builds/soloaiguy/scripts/publish-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/cron.log 2>&1
#
# Tunables:
#   PUBLISH_WAIT_SECS    seconds to wait per Telegram reply (default 3600 = 1h)
#   PUBLISH_DAYS_AHEAD   how far ahead to consider drafts due (default 1)

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
POSTS_DIR="$REPO/src/content/posts"
LOG_DIR="$REPO/scripts/publish-log"
TODAY="$(date -u +%Y-%m-%d)"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$TODAY.md"

[[ -f "$HOME/.soloaiguy.env" ]] && source "$HOME/.soloaiguy.env"
export TG_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
export TG_CHAT="${TELEGRAM_CHAT_ID:-}"
WAIT_SECS="${PUBLISH_WAIT_SECS:-3600}"
DAYS_AHEAD="${PUBLISH_DAYS_AHEAD:-1}"

# Make node/npm reachable in the cron environment (no login shell, no nvm.sh).
shopt -s nullglob
_node_bin_dirs=( "$HOME"/.nvm/versions/node/*/bin )
shopt -u nullglob
if [ "${#_node_bin_dirs[@]}" -gt 0 ]; then
  export PATH="${_node_bin_dirs[-1]}:$PATH"
fi

echo "# Publish run — $(date -u --iso-8601=seconds)" >> "$LOG_FILE"
log() { echo "[$(date -u --iso-8601=seconds)] $*" | tee -a "$LOG_FILE" >&2 ; }

cd "$REPO"

# --- safety: refuse to operate on a dirty tree ---
if ! git diff-index --quiet HEAD --; then
  log "ERROR: uncommitted changes in working tree — aborting (commit or stash first)"
  exit 1
fi

# --- find due drafts ---
due_files="$(POSTS_DIR="$POSTS_DIR" DAYS_AHEAD="$DAYS_AHEAD" python3 <<'PYEOF'
import datetime, os, pathlib, re

posts_dir = pathlib.Path(os.environ["POSTS_DIR"])
days_ahead = int(os.environ["DAYS_AHEAD"])
cutoff = datetime.date.today() + datetime.timedelta(days=days_ahead)

for p in sorted(posts_dir.glob("*.md")):
    text = p.read_text()
    if not text.startswith("---\n"):
        continue
    fm_end = text.find("\n---\n", 4)
    if fm_end < 0:
        continue
    fm = text[4:fm_end]
    if not re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
        continue
    m = re.search(r"^pubDate:\s*(\S+)", fm, re.MULTILINE)
    if not m:
        continue
    try:
        pub = datetime.date.fromisoformat(m.group(1).strip().strip('"\''))
    except ValueError:
        continue
    if pub > cutoff:
        continue
    title_m = re.search(r'^title:\s*"([^"]+)"', fm, re.MULTILINE)
    title = title_m.group(1) if title_m else p.stem
    print(f"{p}|{pub.isoformat()}|{title}")
PYEOF
)"

if [[ -z "$due_files" ]]; then
  log "no drafts due (window: today through +${DAYS_AHEAD} day(s))"
  exit 0
fi

count="$(echo "$due_files" | wc -l)"
log "found $count due draft(s)"

# Without Telegram, just list and exit (still useful for cron logs).
if [[ -z "$TG_TOKEN" || -z "$TG_CHAT" ]]; then
  log "Telegram NOT configured; listing due drafts only:"
  while IFS='|' read -r path pub title; do
    log "  $(basename "$path") | pubDate=$pub | $title"
  done <<< "$due_files"
  log "manual publish: edit draft:false, npm run build, git commit, git push origin main"
  exit 0
fi

tg_send() {
  TG_TEXT_ENV="$1" python3 <<'PYEOF' >/dev/null
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
}

# tg_wait WORDS TIMEOUT_SECS — long-poll for one of the space-separated tokens.
# Echoes the matched token or "" if timeout.
tg_wait() {
  local words="$1"
  local timeout="$2"

  local baseline
  baseline="$(curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/getUpdates?limit=1&offset=-1" \
    | python3 -c '
import json, sys
d = json.loads(sys.stdin.read()); r = d.get("result", [])
print(r[-1]["update_id"] if r else 0)
' 2>/dev/null || echo 0)"

  local deadline=$(( $(date +%s) + timeout ))
  local offset=$((baseline + 1))
  local action=""

  while [[ $(date +%s) -lt $deadline ]]; do
    local remaining=$(( deadline - $(date +%s) ))
    local to=$(( remaining > 30 ? 30 : remaining ))
    local resp
    resp="$(curl -fsS --max-time $((to + 5)) \
      "https://api.telegram.org/bot${TG_TOKEN}/getUpdates?offset=${offset}&timeout=${to}" \
      || echo '{"result":[]}')"

    local parsed
    parsed="$(WORDS="$words" echo "$resp" | python3 -c '
import json, sys, os
d = json.loads(sys.stdin.read())
chat_id = str(os.environ.get("TG_CHAT", ""))
words = set(os.environ.get("WORDS", "").lower().split())
last = 0; match = ""
for u in d.get("result", []):
    last = u.get("update_id", last)
    msg = u.get("message") or {}
    if str(msg.get("chat", {}).get("id", "")) != chat_id:
        continue
    text = (msg.get("text") or "").strip().lower()
    if text in words and not match:
        match = text
print(f"{last}|{match}")
' 2>/dev/null || echo '0|')"

    local last_uid="${parsed%|*}"
    local m="${parsed#*|}"

    if [[ "$last_uid" != "0" && "$last_uid" -gt $((offset - 1)) ]]; then
      offset=$((last_uid + 1))
    fi
    if [[ -n "$m" ]]; then
      action="$m"
      break
    fi
  done

  echo "$action"
}

flip_draft_false() {
  POST_PATH="$1" python3 <<'PYEOF'
import os, pathlib, re, sys
p = pathlib.Path(os.environ["POST_PATH"])
text = p.read_text()
new = re.sub(r"^draft:\s*true\s*$", "draft: false", text, count=1, flags=re.MULTILINE)
if new == text:
    sys.stderr.write(f"could not flip draft in {p}\n"); sys.exit(1)
p.write_text(new)
PYEOF
}

bump_pubdate() {
  POST_PATH="$1" OLD_DATE="$2" NEW_DATE="$3" python3 <<'PYEOF'
import os, pathlib, re, sys
p = pathlib.Path(os.environ["POST_PATH"])
old = os.environ["OLD_DATE"]
new = os.environ["NEW_DATE"]
text = p.read_text()
out = re.sub(rf"^pubDate:\s*{re.escape(old)}\s*$",
             f"pubDate: {new}", text, count=1, flags=re.MULTILINE)
if out == text:
    sys.stderr.write(f"could not bump pubDate in {p}\n"); sys.exit(1)
p.write_text(out)
PYEOF
}

# --- per-draft loop ---
while IFS='|' read -r path pub title; do
  slug="$(basename "$path" .md)"
  url="https://soloaiguy.com/posts/$slug/"

  msg="Solo AI Guy — publish ready

\"$title\"
pubDate: $pub
URL after publish: $url

Reply within $((WAIT_SECS / 60))m:
  publish  ship it (build + commit + push to main)
  defer    bump pubDate +7 days
  skip     leave alone"

  log "asking about: $slug"
  tg_send "$msg"

  action="$(tg_wait "publish defer skip" "$WAIT_SECS")"
  if [[ -z "$action" ]]; then
    log "  no reply — defaulting to skip"
    action="skip"
  fi
  log "  action: $action"

  case "$action" in
    publish)
      if ! flip_draft_false "$path" 2>>"$LOG_FILE"; then
        tg_send "publish FAILED for $slug — could not flip draft frontmatter"
        continue
      fi
      log "  building..."
      if ! npm run build >/dev/null 2>>"$LOG_FILE"; then
        log "  BUILD FAILED — reverting draft flip"
        git checkout -- "$path"
        tg_send "publish FAILED for $slug — npm run build failed (see $LOG_FILE)"
        continue
      fi
      git add "$path"
      git commit -m "publish: $slug" >/dev/null
      if ! git push origin main 2>>"$LOG_FILE"; then
        log "  PUSH FAILED (committed locally)"
        tg_send "publish: $slug committed locally but PUSH FAILED. Run: cd $REPO && git push origin main"
        continue
      fi
      log "  PUBLISHED + pushed"
      tg_send "OK Published: $title

Live at $url
GH Actions deploy in ~2 min."
      ;;
    defer)
      new_date="$(date -u -d "$pub +7 days" +%Y-%m-%d)"
      if ! bump_pubdate "$path" "$pub" "$new_date" 2>>"$LOG_FILE"; then
        tg_send "defer FAILED for $slug — could not bump pubDate"
        continue
      fi
      git add "$path"
      git commit -m "defer: $slug -> $new_date" >/dev/null
      log "  DEFERRED to $new_date (committed locally)"
      tg_send "OK Deferred: $slug -> pubDate $new_date (local commit only, not pushed)"
      ;;
    skip)
      log "  skipped"
      ;;
  esac
done <<< "$due_files"

log "done"

#!/usr/bin/env bash
#
# exp-cron.sh — auto-experiment harness with Telegram-approved deps install.
#
# Default posture: ATTEMPT integration. The architect is instructed to make the
# brief work, not look for reasons to skip. The only outright refusal is for
# malicious-looking briefs (malware, credential theft, exfiltration).
#
# Flow:
#   1. Create sandboxed worktree off main.
#   2. Pass 1: aider-arch (Haiku planner + editor) reads brief, EITHER
#      (a) makes the edits and appends "Tried: <slug> — ..." to EXPERIMENTS.md, OR
#      (b) writes EXPERIMENT_NEEDS.md listing required deps + install commands, OR
#      (c) appends "Security risk: <slug> — ..." to EXPERIMENTS.md (rare).
#   3. If EXPERIMENT_NEEDS.md present, Telegram the contents, long-poll for
#      `install` or `skip` reply. On `install`, run the listed commands and
#      Pass 2: re-invoke aider with deps-ready prompt.
#   4. Constraint check (banned paths still rejected).
#   5. Build verification (`npm run build`).
#   6. Auto-merge to local main if build passes. NEVER pushes to origin.
#
# Banned paths (touched = constraint violation, branch deleted):
#   scripts/, .github/, pipeline/, ~/.soloaiguy.env
#   (vs. previous version: package.json/astro.config.mjs/tsconfig.json/public/
#    are now permitted — aider can add deps and modify build config.)
#
# Usage: scripts/exp-cron.sh <brief-file>

set -euo pipefail

BRIEF_FILE="${1:?usage: exp-cron.sh <brief-file>}"
[ -r "$BRIEF_FILE" ] || { echo "exp-cron: brief not readable: $BRIEF_FILE" >&2; exit 1; }

if [ ! -r "$HOME/.soloaiguy.env" ]; then
  echo "exp-cron: missing ~/.soloaiguy.env" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$HOME/.soloaiguy.env"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "exp-cron: ANTHROPIC_API_KEY not set in ~/.soloaiguy.env" >&2
  exit 1
fi

# Make aider + node findable under cron (non-login shell).
export PATH="$HOME/.local/bin:$PATH"
shopt -s nullglob
_node_bin_dirs=( "$HOME"/.nvm/versions/node/*/bin )
shopt -u nullglob
if [ "${#_node_bin_dirs[@]}" -gt 0 ]; then
  export PATH="${_node_bin_dirs[-1]}:$PATH"
fi

REPO="$HOME/builds/soloaiguy"
WT_BASE="$HOME/builds/soloaiguy-experiments"
LOG_DIR="$REPO/scripts/exp-log"
mkdir -p "$WT_BASE" "$LOG_DIR"

DATE="$(date -u +%Y-%m-%dT%H%M%S)"
SLUG="exp-$DATE"
WT="$WT_BASE/$SLUG"
LOG="$LOG_DIR/$DATE.md"
BRANCH="experiment/$SLUG"

# How long to wait for `install`/`skip` reply on the deps prompt
DEPS_WAIT_SECS="${EXP_DEPS_WAIT_SECS:-1800}"  # 30 min default

ts() { date -u --iso-8601=seconds; }
log() { echo "[$(ts)] $*" | tee -a "$LOG" >&2; }

tg() {
  local text="$1"
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    log "telegram: skipped (no creds)"
    return 0
  fi
  TG_TEXT="$text" \
  TG_TOKEN="$TELEGRAM_BOT_TOKEN" \
  TG_CHAT="$TELEGRAM_CHAT_ID" \
  python3 - <<'PYEOF' >/dev/null 2>&1 || log "telegram: send failed"
import os, json, urllib.request
data = json.dumps({
  'chat_id': os.environ['TG_CHAT'],
  'text': os.environ['TG_TEXT'],
  'parse_mode': 'Markdown',
  'disable_web_page_preview': True,
}).encode()
req = urllib.request.Request(
  f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
  data=data,
  headers={'Content-Type': 'application/json'},
)
urllib.request.urlopen(req, timeout=10).read()
PYEOF
}

# Long-poll Telegram for one of the given keywords. Echoes the matched word
# (lowercased) on success, or empty string on timeout.
# Args: <regex-of-allowed-words> <timeout-seconds> <baseline-update-id>
wait_for_reply() {
  local allowed_re="$1"
  local timeout_s="$2"
  local baseline="$3"
  local deadline=$(( $(date +%s) + timeout_s ))
  local offset=$(( baseline + 1 ))

  while [ "$(date +%s)" -lt "$deadline" ]; do
    local remaining=$(( deadline - $(date +%s) ))
    local poll_to=$(( remaining > 30 ? 30 : remaining ))
    local resp parsed last_uid match
    resp="$(curl -fsS --max-time $((poll_to + 5)) \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?offset=${offset}&timeout=${poll_to}" \
      || echo '{"result":[]}')"

    parsed="$(echo "$resp" | TG_CHAT="$TELEGRAM_CHAT_ID" ALLOWED="$allowed_re" python3 -c '
import json, sys, os, re
d = json.loads(sys.stdin.read())
chat_id = str(os.environ.get("TG_CHAT", ""))
allowed = re.compile(os.environ.get("ALLOWED", ""), re.IGNORECASE)
last_uid = 0
match = ""
for u in d.get("result", []):
    last_uid = u.get("update_id", last_uid)
    msg = u.get("message") or {}
    if str(msg.get("chat", {}).get("id", "")) != chat_id:
        continue
    text = (msg.get("text") or "").strip().lower()
    if allowed.fullmatch(text) and not match:
        match = text
print(f"{last_uid}|{match}")
' 2>/dev/null || echo '0|')"

    last_uid="${parsed%|*}"
    match="${parsed#*|}"

    if [ "$last_uid" != "0" ] && [ "$last_uid" -gt "$((offset - 1))" ]; then
      offset=$((last_uid + 1))
    fi
    if [ -n "$match" ]; then
      echo "$match"
      return 0
    fi
  done

  echo ""
  return 0
}

# Capture latest update_id BEFORE we send anything (used as the long-poll baseline)
get_baseline() {
  curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?limit=1&offset=-1" \
    | python3 -c '
import json, sys
d = json.loads(sys.stdin.read())
r = d.get("result", [])
print(r[-1]["update_id"] if r else 0)
' 2>/dev/null || echo 0
}

cleanup_branch_only() {
  git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
  git -C "$REPO" branch -D "$BRANCH" >/dev/null 2>&1 || true
}

run_aider_pass() {
  local prompt="$1"
  local extra_files="${2:-}"  # space-separated file list to include in chat
  cd "$WT"
  set +e
  # shellcheck disable=SC2086
  EXP_PROMPT="$prompt" timeout 600 "$HOME/bin/aider-arch.sh" \
    --yes-always \
    --no-stream \
    --no-auto-lint \
    --no-show-model-warnings \
    --message "$prompt" \
    EXPERIMENTS.md $extra_files >>"$LOG" 2>&1
  local ec=$?
  set -e
  return $ec
}

# ---- start ----

echo "# Experiment $DATE" > "$LOG"
log "brief: $BRIEF_FILE"
log "branch: $BRANCH"
log "worktree: $WT"
log "PATH: $PATH"
log "which node: $(command -v node || echo 'not found')"
log "which npm:  $(command -v npm || echo 'not found')"
log "which aider: $(command -v aider || echo 'not found')"

git -C "$REPO" fetch origin main >>"$LOG" 2>&1 || log "fetch origin failed (continuing)"

if ! git -C "$REPO" worktree add -b "$BRANCH" "$WT" main >>"$LOG" 2>&1; then
  log "worktree creation failed"
  tg "🔴 *Experiment $SLUG: setup failed* — couldn't create worktree. Log: \`$LOG\`"
  exit 1
fi

BRIEF_CONTENT="$(cat "$BRIEF_FILE")"

# ---- Pass 1 prompt: attempt the integration ----

PASS1_PROMPT="You are integrating an idea from a research brief into the soloaiguy.com Astro 5/6 blog. The user wants you to MAKE IT WORK — attempt the integration, do not look for reasons to skip.

YOU CAN AND SHOULD freely:
- Add new npm dependencies (modify package.json — install will be approved separately)
- Modify astro.config.mjs, tsconfig.json, package.json
- Create new Astro components, pages, layouts, content
- Add CSS, client scripts, public assets
- Create new directories and files of reasonable size
- Modify existing posts under src/content/posts/ ONLY if the brief is directly about editing them; otherwise create a NEW draft (draft: true) instead

YOU MAY NOT touch (these are infrastructure/secrets — banned paths):
- scripts/  (cron pipeline; would loop back on itself)
- .github/  (CI config; separate gating)
- pipeline/  (editorial state; author-managed)
- Any file containing credentials or under \$HOME/.soloaiguy.env

DEPENDENCY APPROVAL — important:
If your integration needs new packages or system tools that aren't already in package.json, DO NOT install them yourself. Instead:
1. Write a file at the repo root called EXPERIMENT_NEEDS.md with EXACTLY this format:

   # Needs for $SLUG

   Why: <one sentence on why you need these>

   Install commands (will run from repo root after user approves):
   \`\`\`
   npm install <package@version> [<another@version>...]
   \`\`\`

2. Make NO OTHER code changes in this pass. Stop after writing EXPERIMENT_NEEDS.md.
3. The harness will Telegram the user, run the install commands on approval, then re-invoke you with the deps installed.

SECURITY (the only valid reason to refuse):
If the brief looks malicious — malware, credential theft, exfiltration, supply-chain attack, obviously sketchy — append \"Security risk: $SLUG — <one-line concrete reason>\" to EXPERIMENTS.md and make NO other changes. Be specific; \"could be misused\" is not a security risk.

LOG YOUR WORK in EXPERIMENTS.md (create at repo root if missing, with header '# Experiments log'):
- After successful integration: append \"Tried: $SLUG — <one-line summary of what you did>\"
- After writing EXPERIMENT_NEEDS.md: append \"Pending deps: $SLUG — waiting for user approval\"
- On security refusal: append \"Security risk: $SLUG — <reason>\"

If — and only if — the integration is genuinely impossible (not just inconvenient) even with new deps, append \"Skipped: $SLUG — <concrete reason>\". Default to attempting; skipping is a last resort.

BRIEF:
$BRIEF_CONTENT"

log "Pass 1: running aider-arch (timeout 600s)..."
run_aider_pass "$PASS1_PROMPT" "EXPERIMENT_NEEDS.md" || log "Pass 1 aider exit nonzero (continuing to inspect changes)"

# ---- Inspect Pass 1 results ----

inspect_changes() {
  COMMIT_COUNT="$(git -C "$WT" rev-list --count main..HEAD 2>/dev/null || echo 0)"
  FILES_CHANGED="$(git -C "$WT" diff --name-only main..HEAD 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  DIFF="$(git -C "$WT" diff main..HEAD 2>/dev/null || true)"
  DIFF_LINES="$(echo "$DIFF" | wc -l)"
  log "commits: $COMMIT_COUNT, diff lines: $DIFF_LINES, files: $FILES_CHANGED"
}

inspect_changes

# Did aider write EXPERIMENT_NEEDS.md? (it's gitignored so check the working tree)
if [ -f "$WT/EXPERIMENT_NEEDS.md" ]; then
  log "EXPERIMENT_NEEDS.md was written — entering deps-approval flow"
  NEEDS_CONTENT="$(cat "$WT/EXPERIMENT_NEEDS.md")"

  baseline="$(get_baseline)"
  tg "🔧 *Experiment $SLUG: deps approval needed*

Aider needs:
\`\`\`
$NEEDS_CONTENT
\`\`\`

Reply *install* to approve and run the commands, *skip* to abandon.
($((DEPS_WAIT_SECS / 60)) min timeout.)

Log: \`$LOG\`"

  log "waiting up to $((DEPS_WAIT_SECS / 60)) min for install/skip reply..."
  reply="$(wait_for_reply '^(install|skip)$' "$DEPS_WAIT_SECS" "$baseline")"
  log "reply: '$reply'"

  case "$reply" in
    install)
      tg "👍 Approved. Running install commands..."
      log "extracting install commands from EXPERIMENT_NEEDS.md..."

      # Pull commands from the fenced code block(s) in EXPERIMENT_NEEDS.md.
      # Tolerant of multiple blocks; we run them all in order.
      cd "$WT"
      INSTALL_OUTPUT="$(awk '
        /^```/ { in_block = !in_block; next }
        in_block { print }
      ' "$WT/EXPERIMENT_NEEDS.md" | while read -r cmd; do
        cmd_trim="$(echo "$cmd" | sed -E 's/^[[:space:]]*[\$>][[:space:]]*//; s/^[[:space:]]+|[[:space:]]+$//g')"
        [ -z "$cmd_trim" ] && continue
        echo "+ $cmd_trim"
        # Allowlist: only npm/npx commands run for now. Anything else gets logged but skipped.
        case "$cmd_trim" in
          npm\ install*|npm\ i\ *|npx\ *)
            timeout 300 bash -c "$cmd_trim" 2>&1 || echo "(command exited nonzero)"
            ;;
          *)
            echo "(skipped non-npm command for safety: $cmd_trim)"
            ;;
        esac
      done 2>&1)"

      {
        echo ""
        echo "## Install output"
        echo '```'
        echo "$INSTALL_OUTPUT"
        echo '```'
      } >> "$LOG"

      # Commit any package.json / lockfile changes from the install
      git -C "$WT" add -A
      git -C "$WT" commit -m "deps: install per EXPERIMENT_NEEDS.md for $SLUG" >>"$LOG" 2>&1 \
        || log "(no deps actually changed package.json)"

      # Remove EXPERIMENT_NEEDS.md before Pass 2
      rm -f "$WT/EXPERIMENT_NEEDS.md"

      # ---- Pass 2 prompt: deps installed, continue integration ----
      PASS2_PROMPT="The user approved your dependency requests and the install commands have been executed. The new packages are now in package.json and node_modules.

Continue the integration described in the original brief below. Make the actual code changes (components, pages, content, etc.) and append \"Tried: $SLUG — <one-line summary of what you did>\" to EXPERIMENTS.md.

If you discover during integration that you need MORE deps, write EXPERIMENT_NEEDS.md again with just the additional ones — the harness will loop.

Same banned paths apply: scripts/, .github/, pipeline/, secrets.

Original brief:
$BRIEF_CONTENT

Install output:
$INSTALL_OUTPUT"

      log "Pass 2: running aider-arch with deps installed..."
      run_aider_pass "$PASS2_PROMPT" "package.json EXPERIMENT_NEEDS.md" || log "Pass 2 aider exit nonzero (continuing)"
      inspect_changes
      ;;

    skip)
      tg "👋 Skipped. Documenting and discarding the branch."
      log "user replied skip — appending Skipped entry"
      cd "$WT"
      mkdir -p "$(dirname "$WT/EXPERIMENTS.md")"
      [ ! -f "$WT/EXPERIMENTS.md" ] && echo "# Experiments log" > "$WT/EXPERIMENTS.md"
      printf '\nSkipped: %s — user declined dependency install\n' "$SLUG" >> "$WT/EXPERIMENTS.md"
      rm -f "$WT/EXPERIMENT_NEEDS.md"
      git -C "$WT" add -A
      git -C "$WT" commit -m "docs: user declined deps for $SLUG" >>"$LOG" 2>&1 || true
      inspect_changes
      ;;

    *)
      log "no install/skip reply within $((DEPS_WAIT_SECS / 60)) min — leaving worktree for inspection"
      tg "⏰ *Experiment $SLUG: deps approval timed out*

Worktree at \`$WT\` left for manual inspection. Branch \`$BRANCH\` not merged.
Log: \`$LOG\`"
      exit 0
      ;;
  esac
fi

# ---- Constraint enforcement ----

BANNED_RE='^(pipeline/|scripts/|\.github/)'
VIOLATIONS="$(git -C "$WT" diff --name-only main..HEAD 2>/dev/null | grep -E "$BANNED_RE" || true)"

if [ -n "$VIOLATIONS" ]; then
  log "CONSTRAINT VIOLATION — banned paths touched:"
  log "$VIOLATIONS"
  tg "🚫 *Experiment $SLUG: rejected (banned paths)*

Aider tried to edit:
\`\`\`
$VIOLATIONS
\`\`\`

Branch \`$BRANCH\` deleted, worktree removed.
Log: \`$LOG\`"
  cleanup_branch_only
  exit 0
fi

if [ "$COMMIT_COUNT" -eq 0 ]; then
  log "no commits — aider made no changes"
  tg "🟡 *Experiment $SLUG: no-op*

Aider made no changes (likely a clean refusal — see log for reasoning).

Log: \`$LOG\`"
  cleanup_branch_only
  exit 0
fi

# ---- Docs-only fast path ----

DOCS_ONLY="$(git -C "$WT" diff --name-only main..HEAD 2>/dev/null \
  | grep -v -E '^EXPERIMENTS\.md$' || true)"
if [ -z "$DOCS_ONLY" ]; then
  log "docs-only change (EXPERIMENTS.md only) — bypassing build, fast-path merge"
  EXP_LINE="$(git -C "$WT" diff main..HEAD -- EXPERIMENTS.md \
    | grep -E '^\+(Tried|Skipped|Security risk|Pending deps):' | head -1 | sed 's/^+//')"

  if git -C "$REPO" merge --ff-only "$BRANCH" >>"$LOG" 2>&1; then
    git -C "$REPO" worktree remove --force "$WT" >>"$LOG" 2>&1 || true
    git -C "$REPO" branch -d "$BRANCH" >>"$LOG" 2>&1 || true
    tg "🟡 *Experiment $SLUG: documented (no code change)*

EXPERIMENTS.md entry:
\`\`\`
$EXP_LINE
\`\`\`

Branch fast-forwarded to local main (docs only — no deploy needed).
Log: \`$LOG\`"
  else
    tg "🟠 *Experiment $SLUG: ff-merge failed*

Branch \`$BRANCH\` left in place. Run \`git -C $REPO merge $BRANCH\` manually.
Log: \`$LOG\`"
  fi
  exit 0
fi

# ---- Build verification ----

log "running build verification (npm run build)..."
cd "$WT"

# If new deps were added but install hasn't been run in the worktree, do it now
if ! [ -d "$WT/node_modules" ]; then
  log "node_modules missing — running npm install"
  set +e
  timeout 300 npm install >>"$LOG" 2>&1
  NPM_INSTALL_EXIT=$?
  set -e
  log "npm install exit: $NPM_INSTALL_EXIT"
fi

set +e
BUILD_OUTPUT="$(timeout 300 npm run build 2>&1)"
BUILD_EXIT=$?
set -e

log "build exit: $BUILD_EXIT"

if [ "$BUILD_EXIT" -ne 0 ]; then
  log "build FAILED — leaving branch + worktree for inspection (NOT merging)"
  TAIL="$(echo "$BUILD_OUTPUT" | tail -25)"
  tg "🔴 *Experiment $SLUG: build failed*

Files changed: \`$FILES_CHANGED\`
Branch \`$BRANCH\` left for inspection (not merged).

Build error tail:
\`\`\`
$TAIL
\`\`\`

Log: \`$LOG\`
Worktree: \`$WT\`"
  exit 0
fi

# ---- Auto-merge to local main ----

log "build passed — merging $BRANCH into local main (ff-only)"

set +e
MERGE_OUTPUT="$(git -C "$REPO" merge --ff-only "$BRANCH" 2>&1)"
MERGE_EXIT=$?
set -e

if [ "$MERGE_EXIT" -ne 0 ]; then
  log "ff-only merge failed: $MERGE_OUTPUT"
  tg "🟠 *Experiment $SLUG: merge conflict*

Branch \`$BRANCH\` couldn't fast-forward (main advanced during the run).
Files changed: \`$FILES_CHANGED\`

Run manually: \`git -C $REPO merge $BRANCH\`
Log: \`$LOG\`"
  exit 0
fi

git -C "$REPO" worktree remove --force "$WT" >>"$LOG" 2>&1 || true
git -C "$REPO" branch -d "$BRANCH" >>"$LOG" 2>&1 || true

DIFF_HEAD="$(echo "$DIFF" | head -30)"
tg "✅ *Experiment $SLUG: merged to local main*

Build passed. Changes are NOT pushed yet.

Files: \`$FILES_CHANGED\`
Commits: $COMMIT_COUNT

Diff (first 30 lines):
\`\`\`
$DIFF_HEAD
\`\`\`

Deploy: \`cd ~/builds/soloaiguy && git push\`
Revert: \`cd ~/builds/soloaiguy && git reset --hard HEAD~$COMMIT_COUNT\`
Log: \`$LOG\`"

log "done — local main updated, push left to user"

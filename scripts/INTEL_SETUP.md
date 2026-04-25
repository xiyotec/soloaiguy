# intel-cron setup

`scripts/intel-cron.sh` runs each morning, pulls AI signal from HN + r/LocalLLaMA, asks Ollama to synthesize one actionable pick with three numbered options, and (optionally) DMs you on Telegram so you can reply `1`, `2`, `3`, or `skip`.

Without Telegram creds, the script just writes the brief to `scripts/intel-log/<date>.md` — useful for testing.

## What the actions do

| Reply | What it does |
|---|---|
| `1` | Hands the brief to `exp-cron.sh` — auto-experiment loop. Creates a sandboxed git worktree, runs architect-mode aider (Haiku planner + qwen-7b editor) with a heavily constrained prompt (banned paths: `package.json`, `astro.config.mjs`, `pipeline/`, `scripts/`, `.github/`, `public/`, existing posts), runs `npm run build`, and auto-merges to **local main only** if everything passes. NEVER pushes to origin — deploy stays manual. Telegrams the diff + outcome. Default behavior is "skip with reason" (most external-tool briefs won't fit the constraints, and a clean skip is a successful run). |
| `2` | Scaffolds a new post at `src/content/posts/<slug>.md` with `draft: true`. Never auto-published. |
| `3` | Appends a one-liner to `pipeline/keyword-queue.md`'s idea buffer. |
| `skip` or no reply within 15 min | No action. The brief is still in the log. |

### exp-cron behaviour

Action `1` triggers `scripts/exp-cron.sh`, which **attempts** the integration by default. Skipping is reserved for genuinely impossible briefs and security risks — most briefs should result in either an immediate code change or a deps-approval prompt.

**Two-pass flow:**

1. **Pass 1.** Aider (Haiku as both planner and editor; ~$0.10/run) reads the brief and either:
   - Makes the code edits directly and appends `Tried: <slug> — ...` to `EXPERIMENTS.md`, OR
   - Writes `EXPERIMENT_NEEDS.md` listing required npm packages + install commands, OR
   - Refuses on security grounds and appends `Security risk: <slug> — ...` to `EXPERIMENTS.md`.
2. **Deps approval (only if `EXPERIMENT_NEEDS.md` was written).** The harness Telegrams the install commands and waits up to 30 min for `install` or `skip`.
   - `install` → runs the commands (allowlisted to `npm install`/`npm i`/`npx` for safety), commits any `package.json`/lockfile changes, then re-invokes aider with deps installed.
   - `skip` → appends `Skipped: <slug> — user declined dependency install` to `EXPERIMENTS.md`.
   - No reply → leaves the worktree for manual inspection.
3. **Build gate.** `npm run build` must pass in the worktree (with new deps installed) before merge. Failed builds leave the worktree intact and Telegram the error tail.
4. **Auto-merge to local main.** `git merge --ff-only` only. The harness **never pushes to origin** — you run `git push` yourself when ready to deploy.

**Banned paths** (touched = constraint violation, branch deleted, no merge):

- `scripts/` (the cron pipeline — would loop back on itself)
- `.github/` (CI config — separate gating concern)
- `pipeline/` (editorial state — author-managed)
- `~/.soloaiguy.env` and any credential file

**What is NOT banned anymore** (changed from the original strict default): aider may freely modify `package.json`, `astro.config.mjs`, `tsconfig.json`, `public/`, and may create new posts under `src/content/posts/`. The deps-approval prompt is the gate for new packages, not a blanket prohibition.

**Cost:** ~$0.10–0.30 per experiment with Haiku planner+editor. At one experiment/day that's under $10/mo, well within the $25/mo cap.

**Telegram replies recap:**

| Reply | Context | Effect |
|---|---|---|
| `install` | Deps approval prompt | Run install commands, continue integration |
| `skip` | Deps approval prompt | Document the skip and discard the branch |
| (no reply, 30 min) | Deps approval prompt | Leave worktree for manual inspection |

Logs at `scripts/exp-log/<timestamp>.md`. Reverting an unwanted merge: `cd ~/builds/soloaiguy && git reset --hard HEAD~<N>` (the merge-success Telegram message includes the exact command).

## Setting up the Telegram bot (one-time, ~3 minutes)

1. **Create the bot.** In Telegram, open a chat with [@BotFather](https://t.me/BotFather). Send `/newbot`. Give it a name and a username ending in `bot` (e.g. `soloaiguy_intel_bot`). BotFather replies with a token like `7891234567:AAH...` — keep this private.

2. **Get your chat ID.** Send any message to your new bot from your personal account. Then visit (replace `<TOKEN>`):

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

   Look for `"chat":{"id":<NUMBER>` in the JSON. That number is your `TELEGRAM_CHAT_ID`.

3. **Save creds in WSL.** Create `~/.soloaiguy.env` (gitignored — it lives outside the repo):

   ```bash
   cat > ~/.soloaiguy.env <<'EOF'
   export TELEGRAM_BOT_TOKEN="7891234567:AAH..."
   export TELEGRAM_CHAT_ID="123456789"
   EOF
   chmod 600 ~/.soloaiguy.env
   ```

   This file is separate from `~/.affiliates.local` (which is YAML-style notes for affiliate IDs).

4. **Test it.** From WSL:

   ```bash
   /home/xiyo/builds/soloaiguy/scripts/intel-cron.sh
   ```

   You should get a Telegram message within ~30 seconds. Reply `skip` to test the full loop without side effects.

5. **Install the cron entry** (06:00 daily):

   ```bash
   crontab -e
   ```

   Add:

   ```
   0 6 * * * /home/xiyo/builds/soloaiguy/scripts/intel-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/cron.log 2>&1
   ```

## Tunables

- `OLLAMA_MODEL` (default `qwen2.5-coder:7b`) — switch to `llama3.1:8b` if briefs are too code-flavored.
- `INTEL_WAIT_SECS` (default `900`) — seconds to wait for a Telegram reply.
- `OLLAMA_API_BASE` (default `http://localhost:11434`).

## Troubleshooting

- **No Telegram message arrives.** Curl-test the token:
  ```bash
  source ~/.soloaiguy.env
  curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
  ```
  If `ok: true`, token works — re-check `TELEGRAM_CHAT_ID`.

- **Reply isn't picked up.** The script looks for plain text `1`, `2`, `3`, or `skip` (case-insensitive). Don't use Telegram's "reply to message" UI — just type the number as a regular message.

- **Brief looks generic.** qwen2.5-coder:7b is small. Briefs are starting points, not finished editorial copy. The `draft: true` rail catches the worst cases.

- **Script hangs.** Telegram long-poll uses `--max-time` per call. If WSL networking is broken, the curl will fail and the loop continues. Check `scripts/cron.log` for `(HN fetch failed)` etc.

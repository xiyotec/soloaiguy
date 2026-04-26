# Atlas — Telegram chief-of-staff for soloaiguy

Atlas is an always-on AI agent you talk to in Telegram. It reads the live state
of the soloaiguy repo every turn (status, calendar, keywords, affiliates, git
log) and can run tools to act on it: web search, allowlisted bash, file reads,
and the cron scripts.

Built so that if Claude Code goes away, Atlas can keep the operation moving.

## What it can do

- Answer "what's the state of the project?" by reading live git + status.md
- Research anything on the open web (`web_search`)
- Read any file in the repo
- Run allowlisted shell (`git status/log/diff`, `ls`, `cat`, `grep`, `npm run build`)
- Manually trigger a cron: intel, exp, publish, social, affiliate-injector
- Remember every conversation (SQLite per chat_id)

## What it deliberately CANNOT do

- `git push` (publish-cron is the only auto-push path; gated by Telegram)
- `rm`, `mv`, `chmod`, network fetches outside web_search
- Edit files (use Claude Code for that — Atlas is not a coding agent)
- Spend money on paid services without confirmation

## Setup (one time, ~3 min)

### 1. Create a dedicated Telegram bot

Atlas needs its OWN bot token. If you reuse intel-cron's or publish-cron's
bot, Telegram will return 409 because only one process can long-poll a bot
at a time.

- DM @BotFather → `/newbot` → name "Atlas" → username `soloaiguy_atlas_bot`
- Save the token
- DM your new bot once so it has a chat to reply to
- Get the chat_id: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`

### 2. Add to `~/.soloaiguy.env`

```bash
export ATLAS_TELEGRAM_BOT_TOKEN="123456:ABC..."
export ATLAS_TELEGRAM_CHAT_ID="123456789"
export ANTHROPIC_API_KEY="sk-ant-..."
# Default model is claude-sonnet-4-6 (~$0.04/turn, ~$90/mo at 75 msgs/day).
# Drop to Haiku for 3x cheaper at the cost of some judgement:
# export ATLAS_MODEL="claude-haiku-4-5-20251001"
```

### 3. Install the SDK

```bash
pip install --user --break-system-packages anthropic
```

### 4. Run

Foreground (for debugging):
```bash
./scripts/atlas/atlas.py
```

Background as a tmux service (Atlas now writes its own rotating log file —
no `tee` needed; stdout still goes to the tmux pane for live tailing):
```bash
tmux new -d -s atlas \
  'source ~/.soloaiguy.env && exec python3 scripts/atlas/atlas.py'
tmux attach -t atlas    # live pane
tail -F scripts/atlas-log/atlas.log    # rotating file, max ~5 MB total
```

## Cost

Default model is **Sonnet 4.6** ($3 in / $15 out per 1M tokens). A typical
conversation turn is ~10K input + 500 output ≈ $0.04. ~75 messages/day
≈ $3/day ≈ $90/mo. Prompt-caching cuts the system+tools+history prefix
to ~10% of that on cache hits.

For 3× cheaper (~$30/mo) at the cost of some judgement, drop to Haiku:
```bash
export ATLAS_MODEL="claude-haiku-4-5-20251001"
```

Hard cap is **$25/mo** in `atlas.py` — bump it before you start hitting it,
or Atlas will refuse to reply. Tracked in `scripts/atlas/atlas.db`.

## Files

```
scripts/atlas/
├── atlas.py             # main loop, Telegram polling, Anthropic client
├── tools.py             # tool defs + handlers (bash allowlist, file read, cron)
├── system_prompt.py     # personality + live project context
├── atlas.db             # SQLite: messages, spend, state (gitignored)
└── README.md            # this file
scripts/atlas-log/       # gitignored runtime logs
```

## Personality knobs

Edit `system_prompt.py` `PERSONA` constant. Atlas defaults to dry, direct,
brutally honest. No corporate fluff. Sandbagged confidence (won't fake
certainty). Pushes back on bad ideas instead of just executing.

## Troubleshooting

**"409 Conflict" on startup:**
You're using a bot token that another process is already polling. Make a new
bot via @BotFather and update the env. (This is the whole reason Atlas needs
its own dedicated bot.)

**"Missing ANTHROPIC_API_KEY":**
Add it to `~/.soloaiguy.env` and re-source it (or just rerun atlas.py — it
reads the file directly).

**Atlas replies are too long / too short:**
Edit the "Brevity is respect" line in `system_prompt.py`.

**Hit the spend cap:**
Bump `MONTHLY_HARD_CAP_USD` in `atlas.py`. Or wait until next month.

**Atlas tries to do something that isn't allowed:**
The bash allowlist is in `tools.py` `ALLOWED_BASH_PREFIXES`. Add what's safe.
Resist the temptation to allow `git push` or `rm` — that's why we have crons
with explicit gates.

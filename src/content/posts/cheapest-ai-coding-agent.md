---
title: "The cheapest way into AI coding agents (under $10/mo)"
description: "A real budget breakdown for solo devs who want agentic coding without an API bill that ruins the month. Free tiers, local models, and where the $10 actually goes."
pubDate: 2026-05-05
tags: ["budget", "ollama", "aider", "claude", "cost"]
draft: true
---

Most "AI coding agent" guides assume you've already accepted a $20–$100/month API bill as the cost of entry. You haven't.

There's a real tier below that — under $10/month, often closer to $0 — that gets you 80% of the way there. This is the budget breakdown nobody writes: what's actually free, what's worth a few dollars, and where the marginal dollar goes furthest.

## The landscape in 2026

The tooling has gotten crowded fast. A quick orientation before the breakdown:

- **IDE-bundled agents** (Cursor, Windsurf, GitHub Copilot) — flat monthly sub, frontier models included. Cheapest is Copilot Pro at $10/mo. Windsurf Pro at $15/mo. Cursor Pro at $20/mo.
- **Terminal agents** (Claude Code, Aider, Gemini CLI, OpenCode) — open-source or BYOK, you pay only for model usage. This is the budget-conscious lane.
- **Fully autonomous** (Devin) — $500/mo, enterprise-only, ignore it.

This post is about the terminal agent lane. That's where the real budget flexibility lives.

## The four tiers

| Tier | Monthly cost | What you get |
|---|---|---|
| 0 | $0 | Pure local: Ollama + Aider, runs fully offline |
| 1 | $0 (with caveats) | Gemini CLI free tier — real frontier model, real limits |
| 2 | < $10 | Haiku 4.5 as planner + local Ollama as executor |
| 3 | $20+ | Cursor / Copilot / Claude Code Pro — out of scope here |

---

## Tier 0 — $0, completely local

**The setup:** Ollama + `qwen2.5-coder:7b` + Aider.

This is the floor. No API calls, no spend, runs on your GPU. I've [benchmarked qwen2.5-coder:7b on a 3070](/posts/qwen-3070-benchmark/) — 90 tok/s, 191ms TTFT. Fast enough that you won't notice latency on most tasks.

**What you give up at $0:**
- Frontier judgment on architectural decisions
- Long-context reasoning (>24K tokens degrades on 7B models)
- Reliable multi-file refactors touching more than 2–3 files

**What you keep:**
- Unlimited mechanical edits: renames, type hints, docstrings, test stubs, list-comp conversions
- Privacy — your code never leaves the machine
- Zero latency from cold-start cloud API calls

**The config:**

```bash
# Install Ollama + the model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

# Install Aider
uv tool install aider-chat
```

`~/.aider.conf.yml`:

```yaml
model: ollama_chat/qwen2.5-coder:7b
model-metadata-file: ~/.aider.model.metadata.json
auto-commits: true
```

`~/.aider.model.metadata.json` (fixes the tiny default context window):

```json
{
  "ollama_chat/qwen2.5-coder:7b": {
    "max_input_tokens": 32768,
    "max_output_tokens": 4096
  }
}
```

**Verdict:** If you've never run a local agent end-to-end, start here. The wins are real and the bill is zero.

---

## Tier 1 — $0, but with a free frontier model

**The play:** Gemini CLI with a personal Google account.

Gemini CLI is open-source and ships a generous free tier: 60 requests/min and 1,000 requests/day with just a Google account login. The catch is that the 1,000 daily requests apply to Flash models by default — Gemini 2.5 Pro is rate-limited much more aggressively on the free tier (around 50 requests/day). For light coding sessions that's fine. For a heavy day, you'll hit the wall.

Real talk on why this is tier 1 and not tier 0: free tiers change without notice. Google cut free-tier limits by 50–80% in December 2025 citing abuse. It's the right tool to know about, but build your workflow on something stable.

**Install:**

```bash
npm install -g @google/gemini-cli
gemini  # prompts you to log in with Google
```

**Verdict:** Use as a free-tier supplement when you want 1M token context or a second opinion on Aider's output. Don't depend on it as your backbone.

---

## Tier 2 — Under $10/mo, the real sweet spot

This is where I actually live.

**The recipe:**
- **Planner:** Claude Haiku 4.5 — $1 input / $5 output per million tokens. Fast, smart enough for one-shot plans.
- **Editor:** Local Ollama (`qwen2.5-coder:7b`) — executes the plan for free.
- **Glue:** Aider's architect mode wires them together.

Haiku 4.5 is cheap enough that typical solo-dev usage — a few planning calls per session, not running it on every keystroke — lands at $3–$8/month. I've tracked my own bill; it rarely clears $5 in a normal week.

**Why it works:**

Most AI coding API cost is wasted on *mechanical execution* — the model reading a 200-line file, generating a diff, writing it back. Local handles that for free. Planning is short, high-leverage, and infrequent. A Haiku planning call is maybe 1K tokens in, 500 out — fractions of a cent.

The combo gets you within shouting distance of all-frontier quality on real coding work.

**Aider architect mode config:**

```yaml
# ~/.aider.conf.yml
architect: true
model: anthropic/claude-haiku-4-5-20251001
editor-model: ollama_chat/qwen2.5-coder:7b
editor-edit-format: diff
```

Add your Anthropic key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # in ~/.bashrc
```

Set a hard spend cap in the Anthropic console so you can't accidentally blow past $10. I use $15/month — enough headroom, but it'll stop me before I do something dumb.

**Real monthly numbers (my usage):**

| Stack | Monthly API spend |
|---|---|
| All-frontier Claude Code | ~$55–65 |
| Hybrid (Haiku plans + local edits) | ~$4–8 |
| Pure local (Ollama only) | $0 |

The hybrid isn't just "less than frontier." It's in a different category. $60 vs $5 is a 12x reduction. For a solo dev side project, that's the difference between "I should watch my usage" and "I don't think about this at all."

---

## Where the marginal dollar goes furthest

If you have $5–10/month to spend, in priority order:

**1. Haiku architect mode** — biggest quality jump from $0. Planning is where frontier intelligence pays off most. One good plan produces 10x better code than one bad plan executed perfectly.

**2. A small Sonnet budget for hard debugging sessions** — Sonnet 4.6 is $3 input / $15 output per million tokens, noticeably smarter than Haiku on reasoning-heavy problems. Keep it as an escalation path, not your default.

**3. Anything else** — a second local model, premium IDE integrations, etc. These are marginal at this budget.

**Specifically not worth it at under $10:**
- A subscription AI IDE (Cursor, Windsurf) — you'd blow the budget just on the sub, with no API flexibility
- Multiple OSS models "just in case." Pick one, learn its limits, stick with it.
- Paying for Gemini API when the free tier covers your volume

---

## One thing most budget guides miss

Every comparison I've seen ignores **switching costs**. If you commit to Cursor's credit-based pricing and then decide it's not working, you've lost the mental overhead of learning a new tool, re-configuring your workflow, and migrating any `.cursorrules` or memory files.

The terminal agent + BYOK approach avoids this. Aider is model-agnostic. If Haiku 4.5 gets replaced by something better at the same price, you change one line in your config. No subscription, no lock-in, no sunk cost.

---

## Take it from here

Three steps to the tier 2 setup:

1. **Install Ollama + qwen2.5-coder:7b.** 10 minutes. [Ollama install.](https://ollama.com/download)
2. **Install Aider.** 5 minutes: `uv tool install aider-chat`
3. **Add an Anthropic key with a $10 hard cap.** Turn on architect mode with the config above.

Run one session with a real task from your current project. Verify the plan Haiku produces before Ollama executes it. Adjust the routing rules when you feel the ceiling.

Most devs who set this up stop thinking about their AI bill within a week. That's the goal.

---

*This is part of the [hybrid stack series](/posts/hybrid-claude-aider-ollama/). Next up: real benchmarks of qwen2.5-coder:7b on a 3070 — where the 7B model actually breaks, and what that means for your routing rules.*

*Subscribe via [RSS](/rss.xml) — I publish real cost numbers from my own usage, not hypotheticals.*

---
title: "Run a coding agent on a cron: free overnight research while you sleep"
description: "A 60-line bash script that picks tomorrow's blog topic, researches it overnight using a local model, and leaves a brief on your desk by morning. Real config, real numbers."
pubDate: 2026-05-08
tags: ["cron", "automation", "aider", "ollama", "claude-code"]
draft: true
---

> **Draft note:** outline. The script (`scripts/agent-cron.sh`) is real and committed; the runtime numbers below need a week of cron data to back the claims.

## The hook

The under-appreciated thing about a local LLM is that the marginal cost of running it is zero. Not "almost zero" — actually zero. Electricity is metered in cents per hour. If you have a model loaded in VRAM at midnight and you're not using it, you're leaving compute on the floor.

So here's the play: every night at 3am, a cron job picks one un-researched topic from my keyword queue, asks a local model to produce a research brief, and writes it to a file. By morning there's a structured starting point for the next post. Cost: $0. Active developer time: 0 minutes.

## The whole thing in 60 lines

The full script is at [`scripts/agent-cron.sh`](https://github.com/xiyotec/soloaiguy/blob/main/scripts/agent-cron.sh). Skeleton:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. pick the next queue item that doesn't already have a research file
slug="$(next_unresearched_slug)"

# 2. construct the prompt
prompt="Research $slug. Output: audience pain, sub-questions, data points, competitors, angle."

# 3. write a stub file
out="pipeline/research/$(date +%F)-$slug.md"
echo "# Research brief — $slug" > "$out"

# 4. send the prompt
aider --yes-always --message "$prompt" "$out"
```

That's the whole shape. The real script handles edge cases (already-researched slugs, no available items, agent selection between Aider and Claude, sourcing nvm).

## Why this beats "I'll do research tomorrow"

Three real reasons it matters:

1. **Compounding.** One research brief per night = ~30 per month. Even if half are dead ends, you're never staring at a blank page.
2. **Honest decoupling of research and writing.** The brief is generated when you're not invested in any angle. Less anchoring on the angle that felt clever last night.
3. **Free.** Local model = zero API spend. The only "cost" is the ~5GB of VRAM tied up while it runs.

## Setting it up

### Prerequisites
- Ollama running with a model pulled (this post assumes `qwen2.5-coder:7b`)
- Aider installed (`uv tool install aider-chat`)
- A keyword queue you actually maintain

### The cron line

```
0 3 * * * /home/xiyo/builds/soloaiguy/scripts/agent-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/results/cron.log 2>&1
```

3am is intentional — your machine is idle, electricity is often cheaper, and the model isn't competing for VRAM with your IDE.

If you're on WSL, you need a Windows Task Scheduler entry that runs `wsl -d Ubuntu-24.04 -- bash /path/to/script.sh` because cron in WSL doesn't fire when the WSL VM is shut down. Details: TODO add the exact Task Scheduler XML.

### What output actually looks like

I ran the script once on a real queue item — the "Aider vs Cline vs Continue.dev shootout" topic. Total time: 9 seconds. Cost: zero.

Here's what `qwen2.5-coder:7b` produced for the "concrete data points" section:

> 1. **Aider**: Version: 0.2.12
> 2. **Cline**: Version: 1.2.3
> 3. **Continue Dev**: Version: 2.0.5
> 4. **Solo Dev**: Version: 1.9.8

Three of those version numbers are wrong. The fourth — "Solo Dev" — is not a real tool; the model interpreted the phrase "solo dev shootout" as a product name and assigned it a version.

This is the actual value proposition of an overnight cron-driven brief: it's a **starting point you have to verify**, not finished research. The structure is useful (audience pain, sub-questions, angle). The specifics are not. Treat the output like a junior researcher's first draft after their first cup of coffee — structurally fine, factually unreliable.

The wins come from what the model gets *right* on average:

- Reasonable framing of audience pain
- Plausible breakdown of what readers want answered
- A starting angle for differentiation

The losses you correct in the morning:

- Specific version numbers, command flags, library names — verify all of them
- Claims about "competing posts" — the model will invent URLs; ignore that section
- Anything numerical — assume wrong until you check

## Stretch: route hard ones to Claude

The script supports an `AGENT=claude` override. Some research topics genuinely need frontier-model reasoning — anything that requires synthesizing disagreement across sources. For those, set `AGENT=claude` in a separate cron line that runs less often:

```
0 4 * * 0 AGENT=claude /home/xiyo/builds/soloaiguy/scripts/agent-cron.sh
```

(Sundays only — once a week, Claude burns ~$0.10 to research one hard topic. Acceptable.)

## What it doesn't do

Honest about the limits:

- **No fact-checking.** The model will confidently include wrong numbers. The brief is a *starting point*, not finished research.
- **No web search.** Pure local model = whatever's in the weights. For topics that need current data, you still need to hop on the browser.
- **No commit on its own.** Files land in `pipeline/research/` but git is up to you. (Deliberate — overnight automation should not push code.)

## What I'd do differently after a month

(To fill once we have a month of cron output. Likely candidates: switch to Claude Haiku for the brief itself once Aider's hit rate is known; add a "discard unhelpful briefs" pass; auto-promote good briefs to outlines.)

---

*Subscribe via [RSS](/rss.xml). Next post: post-mortem on the first month of cron-driven research — what stuck, what got tossed, and the exact ratio of useful briefs to throwaways.*

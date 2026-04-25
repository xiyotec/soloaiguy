---
title: "The cheapest way into AI coding agents (under $10/mo)"
description: "A real budget breakdown for solo devs who want agentic coding without an API bill that ruins the month. Free tiers, local models, and where the $10 actually goes."
pubDate: 2026-05-05
tags: ["budget", "ollama", "aider", "claude", "cost"]
draft: true
---

> **Note (draft):** outline only. Numbers and configs to be filled before publish.

## The hook

Most "AI coding agent" guides assume you've already accepted a $20–$100/month API bill as the cost of entry. You haven't. There's a tier below that — under $10/month, often closer to $0 — that gets you 80% of the way.

This post is the budget breakdown nobody writes: what's actually free, what's worth the few dollars, and where the marginal dollar goes furthest.

## The four tiers

Tier the offerings honestly, not by marketing:

| Tier | Monthly cost | What you get |
|---|---|---|
| 0 | $0 | Pure local: Ollama + Aider, runs offline |
| 1 | < $5 | Free API tiers (Gemini, Mistral) + local fallback |
| 2 | < $10 | Pay-per-use Haiku/Sonnet for planning, local for execution |
| 3 | $20+ | Cursor / Copilot / Claude Code Pro tier |

This post focuses on tiers 0–2 — the under-$10 zone. Tier 3 is its own conversation.

## Tier 0 — Free, local, surprisingly capable

The setup: Ollama + a coding-tuned 7B model + Aider.

Numbers to fill (from benchmark post): tok/s on a 3070, where quality breaks, what kinds of tasks 7B handles well.

What you give up at $0:
- Frontier judgment on architectural calls
- Long-context reasoning (>24K tokens degrades fast)
- Reliable multi-file refactors

What you keep:
- Unlimited mechanical edits (renames, type hints, docstrings, list-comp conversions)
- Privacy — code never leaves your machine
- No latency from cold-start cloud calls

**Verdict:** if you've never run a local agent end-to-end, start here. The wins are real and the bill is zero.

## Tier 1 — Under $5, free-tier hopping

Free tiers worth knowing about (verify current limits — these change):
- Gemini API free quota
- Mistral free tier
- Groq free quota (great for fast inference of OSS models)

The play: route the harder stuff to whichever free tier is up, fall back to local when you've burned the daily quota. Aider supports multiple models; you can switch with a flag.

Risks:
- Free tiers change without notice
- Rate limits make "background" agents flaky
- Prompt-caching usually isn't free

**Verdict:** worth knowing, not worth depending on. Use as overflow, not as backbone.

## Tier 2 — Under $10, the real sweet spot

The recipe:
- **Planner:** Claude Haiku 4.5 — cheap, fast, smart enough for one-shot plans.
- **Editor:** Local Ollama (`qwen2.5-coder:7b`) — executes the plan for free.
- **Glue:** Aider's architect mode wires them together.

Estimated monthly cost on typical solo-dev usage: $3–$8. Numbers to fill from real usage tracking.

Why it works:
- Most "AI coding" cost is wasted on mechanical execution. Local takes that for free.
- Planning is short, infrequent, and high-leverage. Haiku per-token cost is small in absolute terms when the prompt is one paragraph.
- The combo gets you within shouting distance of frontier-only quality on real coding work.

Sample `~/.aider.conf.yml` to enable architect mode (already published in [the hybrid post](/posts/hybrid-claude-aider-ollama/)).

## Where the marginal dollar goes furthest

If you have $5–10/month to spend, in priority order:

1. **Haiku architect mode** — biggest jump from $0 baseline.
2. **A small Sonnet budget for hard debugging sessions** — the times you really need judgment, you really need it.
3. **Anything else.**

Specifically *not* worth it:
- A second OSS model "just in case." Pick one and learn its limits.
- Premium IDE subscriptions when their AI features can be replicated with a CLI agent.

## What I actually run

(One paragraph: the exact setup, monthly bill, and what I'd change if my budget went to $25.)

## Take it from here

Three steps:
1. Install Ollama + qwen2.5-coder:7b.
2. Install Aider.
3. Add an Anthropic key with a $5 budget cap and turn on architect mode.

You'll feel the difference within a week. If you don't, the routing rules in [the hybrid post](/posts/hybrid-claude-aider-ollama/) probably need tightening.

---

*Subscribe via [RSS](/rss.xml). I publish a real cost number every few weeks — this is the cheap end; future posts cover when spending more pays off.*

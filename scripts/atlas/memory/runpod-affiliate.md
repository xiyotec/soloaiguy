---
name: RunPod Affiliate Link
description: Xiyo's RunPod referral link, saved 2026-04-26 — not wired into the site yet, deploy when a post about cloud GPU / hosted inference is written.
type: project
---

# RunPod affiliate link

**Link:** `https://runpod.io?ref=jsen6ubk`

**Status as of 2026-04-26:** signed up, link in hand, **NOT yet wired into the site or affiliate-injector**.

**Why deferred:** Affiliate links convert when readers are mid-decision, not when sprinkled randomly. Atlas/Xiyo doesn't have a post about cloud GPUs or hosted inference yet, so injecting RunPod links into existing posts (which are about local setups: Aider+Ollama, RTX 3070, Qwen) would feel forced and tank trust.

**How to apply:**
- When Xiyo writes a post that touches: cloud GPU rentals, hosted inference vs local, A100/H100 access, scaling beyond a 3070, or "what to do when local isn't enough" → drop the link inline naturally.
- Then optionally add `runpod.io` → `runpod.io?ref=jsen6ubk` to `scripts/affiliate-injector.py` so future mentions auto-rewrite.
- Don't bulk-inject into existing posts. Don't add a "Resources" sidebar just to host it.

**Companion affiliates already live:** Replicate (paid, in env as REPLICATE_API_TOKEN), Beehiiv (paused on Stripe ID — see beehiiv-api-todo.md), Impact site verification meta tag in BaseLayout.

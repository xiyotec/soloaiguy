# Editorial Calendar

Status legend: `idea` → `outlined` → `drafting` → `editing` → `published`

## Active

| Slug | Title | Status | Target ship | Notes |
|---|---|---|---|---|
| hello-solo-ai-dev | Hello from Solo AI Dev | published | 2026-04-24 | Inaugural meta post. |
| hybrid-claude-aider-ollama | How I run Claude + Aider + Ollama hybrid and cut AI costs ~80% | published | 2026-04-28 | Hero post for the niche. Drafted 2026-04-24, scheduled for 4-day soak before publish. |
| qwen-3070-benchmark | qwen2.5-coder:7b on a 3070: real benchmarks | drafting | 2026-05-01 | Harness shipped at scripts/benchmark.py. First run on 2026-04-24: qwen 87.6 tok/s avg, llama 82.9. Quality split: llama's merge_sorted has O(n²) bug (uses pop(0)), qwen produced correct two-pointer. Re-run before publish to confirm stability. |
| cheapest-ai-coding-agent | The cheapest way into AI coding agents (under $10/mo) | drafting | 2026-05-05 | Outline drafted. Numbers/configs TBD before publish. |

## Queued (next 2 weeks)

| Slug | Title | Source | Effort |
|---|---|---|---|
| cron-driven-agent | Run a coding agent on a cron: free overnight research | derived from agent-cron.sh | low — script exists, post outlined |
| aider-cline-continue-shootout | Aider vs Cline vs Continue.dev: solo dev shootout | keyword-queue #4 | high — need to actually use all three |
| claude-code-real-cost | How much does Claude Code actually cost for a side project? | keyword-queue #5 | medium — need 2 weeks of usage data |

## Posting cadence target

- Weeks 1–4: 1 post/week (build habit, prove pipeline)
- Weeks 5–12: 2 posts/week (after pipeline is smooth)
- Weeks 13+: scale or sustain depending on traffic data

## Decision log

- **2026-04-24:** Picked Astro over Eleventy/Hugo. Reason: Content Collections + first-class TypeScript + great MDX support + active ecosystem.
- **2026-04-24:** Static + GitHub Pages. Reason: zero hosting cost, zero infra. Move to Cloudflare Pages later if we need edge functions.
- **2026-04-24:** Post #2 set as `pubDate: 2026-04-28` despite being drafted day 0. Reason: 4-day soak gives time for editing pass + lets us land it after domain is live, so launch isn't anti-climactic.
- **2026-04-24:** Adopted brand voice: first-person, direct, numbers > adjectives, no hedging. Documented in `post-template.md`.

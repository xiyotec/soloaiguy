# Editorial Calendar

Status legend: `idea` → `outlined` → `drafting` → `editing` → `published`

## Active

| Slug | Title | Status | Target ship | Notes |
|---|---|---|---|---|
| hello-solo-ai-guy | Hello from Solo AI Guy | published | 2026-04-24 | Inaugural meta post. |
| hybrid-claude-aider-ollama | How I run Claude + Aider + Ollama hybrid and cut AI costs ~80% | published | 2026-04-28 | Hero post for the niche. Drafted 2026-04-24, scheduled for 4-day soak before publish. |
| qwen-3070-benchmark | qwen2.5-coder:7b on a 3070: real benchmarks | drafting | 2026-05-01 | Harness shipped at scripts/benchmark.py. First run on 2026-04-24: qwen 87.6 tok/s avg, llama 82.9. Quality split: llama's merge_sorted has O(n²) bug (uses pop(0)), qwen produced correct two-pointer. Re-run before publish to confirm stability. |
| cheapest-ai-coding-agent | The cheapest way into AI coding agents (under $10/mo) | drafting | 2026-05-05 | Outline drafted. Numbers/configs TBD before publish. |

## Queued (next 2 weeks)

| Slug | Title | Source | Effort | Target ship |
|---|---|---|---|---|
| cron-driven-agent | Run a coding agent on a cron: free overnight research | derived from agent-cron.sh | low — script exists, post outlined | 2026-05-08 |
| aider-cline-continue-shootout | Aider vs Cline vs Continue.dev: solo dev shootout | keyword-queue #4 | high — need to actually use all three | 2026-05-12 |
| claude-code-real-cost | How much does Claude Code actually cost for a side project? | keyword-queue #5 | medium — need 2 weeks of usage data | 2026-05-15 |

## Queued (intel-sourced — April 2026 trending)

| Slug | Title | Source | Signal | Effort | Target ship |
|---|---|---|---|---|---|
| claude-md-best-practices | The CLAUDE.md practices that actually change how Claude Code behaves | Karpathy skills repo (88K stars), intel-cron Apr 2026 | Massive search intent. Karpathy declared vibe coding passé; CLAUDE.md is the serious-dev answer | medium — need to write + test real examples | 2026-05-19 |
| codex-cli-vs-claude-code | openai/codex-cli vs Claude Code: which terminal agent wins? | openai/codex-cli repo (5,800 stars in days), live controversy, intel-cron Apr 2026 | OpenAI outage Apr 20 + Codex CLI launch = perfect timing for an honest comparison | medium — need to actually run both | 2026-05-22 |
| ai-70-30-problem | AI gets you 70% there fast. The last 30% will kill your deadline. | intel-cron Apr 2026 — #1 dev pain point | No one is writing this honestly. Direct hit on our audience's lived experience | low — personal take + examples from our own build | 2026-05-26 |
| goose-local-agent-mcp | block/goose: a local-first agent that actually respects your privacy | block/goose repo (4,900 stars), intel-cron Apr 2026 | Privacy-first demand spiking post-OpenAI outage. Ties to local LLM angle | medium — need setup walkthrough on our hardware | 2026-05-29 |
| google-adk-multi-agent | Build a multi-agent system with Google ADK (the fast way) | google/adk-python repo (8,200 stars in 2 weeks), intel-cron Apr 2026 | Hottest new framework right now. Solo-dev angle: is it worth the complexity? | high — new framework, needs real build | 2026-06-02 |
| openclaw-local-ai | OpenClaw: 210K stars and the fastest-growing OSS project — is it worth running locally? | OpenClaw repo (210K+ stars), market-intel Apr 2026 | Viral repo. Privacy-first angle + local setup walkthrough = strong SEO + audience fit | medium — needs install + real usage notes | 2026-06-05 |
| n8n-local-llm-workflows | n8n + local LLM: build an AI workflow engine that costs nothing per month | n8n repo (162K stars), market-intel Apr 2026 | Automation + cost-zero angle is our lane. Huge search volume on n8n + AI | medium — needs workflow build + screenshots | 2026-06-09 |
| smolagents-cheap-agent | HuggingFace smolagents: the lightest way to build an agent in 2026 | huggingface/smolagents (4,100 stars), market-intel Apr 2026 | Strong fit with cheapest-agent angle. Complements our under-$10/mo post | low-medium — library is small, fast to test | 2026-06-12 |
| markitdown-llm-context | microsoft/markitdown: feed any doc to your LLM in 60 seconds | microsoft/markitdown (3,600 stars), market-intel Apr 2026 | Practical utility post. Solves real pain (context loading). Easy to demonstrate | low — script + demo, mostly writing | 2026-06-16 |
| qwen3-coder-benchmark | qwen3-coder 128K context: benchmarks on a 3070 | qwen-ai/qwen3-coder (2,800 stars), market-intel Apr 2026 | Natural sequel to our qwen2.5 benchmark post. Same hardware, newer model | medium — needs benchmark run | 2026-06-19 |
| roo-code-multi-agent | Roo Code: a whole dev team of AI agents in your editor | Roo Code trending Apr 2026, market-intel | Strong hook. Sits between Cursor and full agentic Claude Code. Unexplored angle | medium — needs real editor testing | 2026-06-23 |

## Posting cadence target

- Weeks 1–4: 1 post/week (build habit, prove pipeline)
- Weeks 5–12: 2 posts/week (after pipeline is smooth)
- Weeks 13+: scale or sustain depending on traffic data

## Decision log

- **2026-04-24:** Picked Astro over Eleventy/Hugo. Reason: Content Collections + first-class TypeScript + great MDX support + active ecosystem.
- **2026-04-24:** Static + GitHub Pages. Reason: zero hosting cost, zero infra. Move to Cloudflare Pages later if we need edge functions.
- **2026-04-24:** Post #2 set as `pubDate: 2026-04-28` despite being drafted day 0. Reason: 4-day soak gives time for editing pass + lets us land it after domain is live, so launch isn't anti-climactic.
- **2026-04-24:** Adopted brand voice: first-person, direct, numbers > adjectives, no hedging. Documented in `post-template.md`.
- **2026-04-26:** Added 5 intel-sourced posts from intel-cron market scan (Apr 2026). Ranked by signal strength: CLAUDE.md > codex-cli vs Claude Code > 70/30 problem > goose > Google ADK.
- **2026-04-26:** Added 6 more posts from full market-intel Apr 2026 scan: OpenClaw, n8n, smolagents, markitdown, qwen3-coder, Roo Code. Calendar now runs to 2026-06-23.

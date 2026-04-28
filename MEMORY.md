# MEMORY.md — Atlas's persistent notes

This file holds long-term facts, decisions, and context that Atlas should carry across sessions. Newer entries appended at the bottom.

## Index

- **atlas-lessons.md** — operational lessons learned (truncation, push hangs, DB resets, etc.)
- **pipeline/affiliates.md** — affiliate program status, links, commission terms
- **pipeline/editorial-calendar.md** — content roadmap through 2026-06-23

## Core facts

- Site: https://soloaiguy.com — solo-founder AI blog, Astro on Cloudflare Pages
- Owner: Xiyo (Telegram chat 8106752420)
- Niche: solo AI builders, local LLMs, GPU/cost optimization, agent tooling
- Voice: dry, direct, brutally honest — no corporate fluff, brevity is respect
- Off-brand: marketing tools (Jasper, Canva, HubSpot), accounting tools, anything that betrays the builder/dev focus

## Active affiliate programs

- Amazon Associates: applied 2026-04-25, 180-day clock, ID in `~/.affiliates.local`
- Namecheap (via Impact): in review, account `XiyoTec`, property 8309332
- RunPod: not yet applied — apply for referral, full 10% cash unlocks at 25 paying refs
- Beehiiv: signup form already wired (commits cc634d3, 0661965); affiliate program is separate, apply for $25–100/referral

## Decisions on hold

- **Fiverr launch for Atlas-as-a-service** — discussed 2026-04-26, deferred until soloaiguy has audience + track record. Revisit when blog has 3+ months traffic data.
- **OpenClaw integration** — explored 2026-04-27, abandoned (the npm framework was over-engineered for our scale; pairing-code messages were polluting the Telegram chat). Manual atlas.py is the canonical agent.
- **Computer-use sister agent on Windows** — `C:\Users\Xiyo\builds\atlas\` exists with full feature set (skills, memory, history, delegate, Haiku). Currently dormant; not bridged to WSL Atlas. Separate project, not soloaiguy-related.

---
name: Beehiiv API Key TODO
description: Xiyo paused beehiiv signup before Stripe ID verification (2026-04-26) — needs to come back when ID is on hand to unlock the API key.
type: project
---

# Beehiiv API key — pending Stripe ID verification

**State as of 2026-04-26:** Xiyo signed up for beehiiv (publication name `XiyoTec`, slug TBC), picked the 14-day trial → drops to free Launch plan after.

Publication ID (V2): `pub_dd1001f5-5645-40e0-8a2b-40e554e01b13`

**Blocker:** API key requires Stripe Identity Verification (ID + selfie, ~5 min). Xiyo didn't have ID on hand at signup. **Remind Xiyo on next status check / when newsletter work comes up.**

**Why:** The site's email-signup form (`src/components/EmailSignup.astro` or equivalent) is currently a dead form — POSTs go nowhere. We need the API key to wire it to beehiiv's `/v2/publications/{pub_id}/subscriptions` endpoint so signups land in the actual list.

**How to apply:**
- If Xiyo says "I've got my ID" or "let's wire up beehiiv" or "newsletter setup": tell them to log into beehiiv → Settings → API → Start Stripe Identity Verification.
- After verification, get the API key. Xiyo should send only the **last 4 chars** to chat; the full key goes into `~/.soloaiguy.env` as `BEEHIIV_API_KEY=...`.
- Then I (Atlas) wire the form submit handler to POST to beehiiv's API.

**Workaround if Xiyo wants signups working before doing Stripe:** swap to beehiiv's hosted iframe embed (Website → Subscribe Forms in the dashboard). Uglier but unblocks subscriber capture.

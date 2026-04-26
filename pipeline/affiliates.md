# Affiliate Programs Tracker

Status: `not-applied` → `applied` → `approved` → `active` → `paying`

Last updated: 2026-04-26

**IDs and tokens live in `~/.affiliates.local` (WSL home, gitignored). Never commit IDs to this public repo.**

## Tier 1 — direct fit, sign up first

| Program | Status | Commission | Applied | Notes |
|---|---|---|---|---|
| Amazon Associates | applied | 1–4% | 2026-04-25 | Auto-approves on signup; 180-day clock to first qualifying sale. ID stored in `~/.affiliates.local`. |
| Namecheap (via Impact) | applied | ~20% | 2026-04-25 | Submitted via Impact marketplace; status "In Review". Email notification when decided. Impact account: `XiyoTec`, property ID 8309332. |
| RunPod | not-applied | 10% cash (6 mo) | — | GPU cloud — perfect fit for local LLM + training posts. Referral is 3–5%; full affiliate (10% cash via Partnerstack) unlocks after 25 paying referrals. Apply now for referral link, upgrade later. |
| Anthropic referral | not-applied | TBD | — | No public consumer program found at signup time — skip unless one launches. |
| Cloudflare (Registrar/Pages) | not-applied | none | — | They don't pay affiliates but trustworthy mention. |
| Hetzner | not-applied | €10/signup | — | Optional; only if we end up covering VPS hosting. |
| Fly.io | not-applied | TBD | — | Edge-friendly hosting, fits the niche. |

## Tier 2 — adjacent, write the post then apply

Apply once 2–3 posts are live (~ week 2–3, est. 2026-05-15).

| Program | Status | Commission | Notes |
|---|---|---|---|
| Newegg | not-applied | 1–3% | Same as Amazon, alternative for builders. |
| Ghost | not-applied | TBD | If we ever cover newsletter setups. |
| Beehiiv | not-applied | $25–100 | Newsletter platform; pays better than Ghost. |

## Tier 2 — new finds (Apr 2026 research)

| Program | Status | Commission | Notes |
|---|---|---|---|
| Cursor referral | not-applied | $20 credit (both sides) | Not a traditional affiliate — it's a referral credit program. No cash. Mention in Cursor posts only if Xiyo actually uses it. |
| Windsurf (Codeium) | not-applied | TBD | Worth checking — fits the "Cursor alternative" angle. No confirmed affiliate program found yet; check codeium.com/affiliates. |
| n8n | not-applied | TBD | Workflow automation, growing fast. Check their partner page. Strong fit for the "cron-driven agent" post angle. |

## Tier 3 — info products and courses

| Program | Status | Commission | Notes |
|---|---|---|---|
| Gumroad | not-applied | (own product) | We'll publish our own product here later. |
| Lemon Squeezy | not-applied | (own product) | Alternative to Gumroad with better tax handling. |

## Programs we're explicitly skipping

| Program | Why |
|---|---|
| Jasper / Copy.ai / Writesonic | Not our audience. Writers, not devs. |
| Canva | Same — wrong niche. |
| HubSpot | B2B CRM. Wrong niche entirely. |
| Generic "AI writing tool" programs | Saturated, wrong audience, low trust angle for soloaiguy. |

## Disclosure policy

Every post that contains an affiliate link gets a footnote:
> *Some links in this post are affiliate links. They cost you nothing extra but help fund this blog. I only link to tools I actually use.*

Posts containing Amazon links also include the Associates-required line:
> *As an Amazon Associate I earn from qualifying purchases.*

No exceptions. Trust > $0.50 of commission.

## Injector workflow

`scripts/affiliate-injector.py` automates Amazon link injection.

1. Sign in to Amazon Associates → Account Settings → grab your tracking ID (`yourid-20`).
2. Edit `~/.affiliates.local` (gitignored, WSL home):
   ```
   amazon-associates: yourid-20
   ```
3. Preview what would change:
   ```
   ./scripts/affiliate-injector.py --dry-run
   ```
4. Apply (writes posts, build-gates with `npm run build`, auto-commits to local main):
   ```
   ./scripts/affiliate-injector.py
   ```
5. `git push` when ready to deploy.

The product map lives at `pipeline/affiliate-map.txt`. Add new products there.

The script is **idempotent** — re-running won't duplicate links or disclosures.
It **never pushes to origin** — deploy stays manual.

## What we will NOT do

- ❌ Affiliate-bait posts ("10 best X" lists where I haven't used 8 of them)
- ❌ Hide the disclosure
- ❌ Recommend a tool just because it pays well
- ❌ Stuff links into every post — only where the link saves the reader time

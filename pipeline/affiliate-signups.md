# Affiliate Signup Quick-Start

The order matters: tier 1 first (most relevant + easy approval), then tier 2 once you have 2–3 published posts (some require a live site).

For each program: I'm only listing programs I'm confident exist. Find the signup by going to the homepage and looking for "Affiliates," "Partners," or "Referrals" in the footer. Don't trust deep-link URLs that haven't been double-checked — affiliate URLs change often.

## Tier 1 — apply first (week 0–1)

Pre-requisites: a live site with at least 1 post.

### 1. Amazon Associates

- **Where to sign up:** Go to `amazon.com` → footer → "Become an Affiliate" (or just search "Amazon Associates").
- **Why first:** Approval is automatic on signup; you get 180 days to make your first qualifying sale or your account gets dropped.
- **Commission:** 1–4% depending on category. Low, but the audience already shops there.
- **Use it for:** GPU recommendations, RAM upgrades, mechanical keyboards, books — natural fits for the niche.
- **Disclosure required:** yes — already covered in our post template footnote.

### 2. Namecheap Affiliate

- **Where to sign up:** Namecheap homepage → footer → "Affiliates."
- **Approval:** usually within a few days; needs a working website URL.
- **Commission:** ~20% on first-year domain registration, plus on hosting/SSL.
- **Use it for:** every time we mention domain registration, naturally.

### 3. Hetzner referral

- **Where to sign up:** Log into your Hetzner account (or create one) → look for "Referral" in account settings.
- **Reward:** ~€10 credit when a referral signs up and bills meet a threshold. Mutual benefit.
- **Use it for:** any post that touches VPS hosting or self-hosted services.

## Tier 2 — apply after 2–3 published posts (week 2–3)

### 4. Beehiiv Partner Program

- **Where to sign up:** Beehiiv homepage → footer → "Partner Program."
- **Approval:** needs a live site or active newsletter; gets stricter over time.
- **Commission:** flat per-paid-signup payouts (varies; check current terms).
- **Use it for:** if/when we cover newsletter setup or compare to Ghost.

### 5. Cloudflare reseller (NOT a paid affiliate)

- **Why mention it:** Cloudflare doesn't pay affiliates. But mentioning their Registrar (at-cost domains, no markup) is right for the audience and they trust us more for it. Goodwill compounds.

## Tier 3 — own products (later, no signup needed)

### 6. Gumroad

- **Where:** `gumroad.com/signup` — just a creator account.
- **When:** month 4–6, when we're ready to publish a paid guide or template.
- **Why:** lowest friction creator platform, handles tax/VAT for you.

### 7. Lemon Squeezy

- **Alternative to Gumroad** with better tax handling for non-US sellers. Pick one based on where you live and which fees hurt less.

## What NOT to do

- ❌ **Don't apply for programs you won't actually use.** Anthropic doesn't appear to have a public consumer affiliate program; if that's still true, skip rather than fish for one.
- ❌ **Don't apply to 20 programs at once.** Spread them across weeks so each post only carries 1–2 disclosures, not a wall of them.
- ❌ **Don't write affiliate-bait listicles.** "Top 10 GPUs" where you've used 2 of them = trust hit. Better to write deeply about 1 you actually own.

## Tracking

When approved for a program, update `pipeline/affiliates.md`:
- Move row to "approved" or "active"
- Note the commission terms in the row (they change)
- Add the affiliate ID/code to a separate (gitignored) file — never commit IDs to a public repo.

A sample structure for the gitignored file (create at `~/.affiliates.local`, never in repo):

```
amazon-associates: <your-tracking-id>
namecheap: <your-affiliate-id>
hetzner: <your-referral-link-token>
```

You'll want a small build-time helper to inject these into post links from env, but that's a later concern — for now, commit posts without affiliate links and add them in an editing pass before publish.

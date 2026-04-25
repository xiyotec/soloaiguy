# Weekly Status Log

Each entry: what shipped, what we learned, what's costing money, what's next.

---

## Week of 2026-04-24 (week 0 — kickoff)

**Shipped this week**
- Domain decision: `soloaiguy.com` (not registered yet — user action)
- Astro 5 site scaffolded: content collections, MDX, sitemap, RSS, robots.txt
- BaseLayout + PostLayout + homepage + /posts/ index + [...slug] route
- Lean global CSS with auto dark mode (~5KB on the wire)
- GitHub Actions deploy workflow ready (waiting on repo)
- Content pipeline scaffolded: keyword-queue (10 ranked topics), editorial-calendar, status, post-template, affiliates tracker
- **Post #1 published:** "Hello from Solo AI Guy" — meta/intro post
- **Post #2 drafted:** "How I run Claude + Aider + Ollama hybrid and cut AI costs ~80%" — hero post for the niche, scheduled 2026-04-28
- Affiliate signup quick-start guide at `pipeline/affiliate-signups.md`

**Spend this week**
| Item | Amount |
|---|---|
| Anthropic API (Claude Code session) | ~$0 (well under $1) |
| Domain | $0 (not yet registered) |
| Hosting | $0 (GitHub Pages plan) |
| **Total** | **$0** |

**Learned**
- Astro 5 moved content config to `src/content.config.ts` with the `glob()` loader (was `src/content/config.ts` with collection-relative globs in v4).
- Variable substitution through `wsl -- bash -lc '...'` from git-bash on Windows is fragile — `$d`/`$r` get stripped through nested quoting. Workaround: write files via UNC path (`\\wsl.localhost\Ubuntu-24.04\...`) using the Write tool, bypass shell escape entirely.
- 4-day soak between draft and publish is worth it: catches voice drift, lets Aider draft proof-points without time pressure.

**Blockers (user actions, ~15 min total)**
1. **Register `soloaiguy.com`** — Cloudflare Registrar (~$10/yr, no markup) or Namecheap (~$11/yr).
2. **Create empty GitHub repo** named `soloaidev` (public). Don't initialize with README — we already have one.
3. **Push initial commit + enable GH Pages.** From WSL: `cd ~/builds/soloaidev && git remote add origin git@github.com:Xiyo/soloaiguy.git && git push -u origin main`. Then in repo Settings → Pages, set source to "GitHub Actions".
4. **Apply for affiliates** — see `pipeline/affiliate-signups.md` for the order to do them.

**Next session targets**
- Build a tiny benchmark harness for post #3 (qwen-3070-benchmark)
- Add Cloudflare Web Analytics snippet (free, no consent banner needed) once domain is live
- Email capture component (for future newsletter)
- Scheduled-agent template — research-tomorrow's-keywords overnight via cron

---

### Session addendum — 2026-04-24 (autonomous work block)

**Shipped while user handles blockers**
- `scripts/benchmark.py` — Ollama benchmark harness (stdlib-only, streams `/api/generate`, measures TTFT + tokens/sec)
- First benchmark run (results in `scripts/results/benchmark-20260424-233310.json`):
  - qwen2.5-coder:7b: 87.6 tok/s avg, 195 ms TTFT
  - llama3.1:8b: 82.9 tok/s avg, 227 ms TTFT
  - Quality split: llama's `merge_sorted` had an O(n²) bug (`pop(0)` in loop), qwen returned the textbook two-pointer merge
- JSON-LD structured data added to `BaseLayout.astro` (Article + Organization + WebSite schemas)
- `/about/` page — sets the niche stake clearly
- `/now/` page — current focus, updates over time
- Post #3 drafted: `qwen-3070-benchmark.md` with the real numbers (target ship 2026-05-01, status drafting)
- Post #4 outlined: `cheapest-ai-coding-agent.md` (target ship 2026-05-05, status drafting)
- `/404.astro` — actual 404 page with useful links
- `EmailSignup.astro` component — env-driven (`PUBLIC_NEWSLETTER_ACTION`), shows RSS fallback when no provider wired up; embedded on homepage
- Nav updated: About + Now links added
- `scripts/verify-build.sh` — wraps `npm run build` with nvm sourced; the working incantation is `MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash /home/xiyo/builds/soloaiguy/scripts/verify-build.sh`

**Build state**
- `npm run build`: green, 7 static pages generated, drafts excluded by all collection consumers (`[...slug]`, posts index, homepage, RSS).

**Learned (this block)**
- The persistent shell-quoting issue for invoking WSL commands from git-bash on Windows is solved by:
  1. Disable MSYS path conversion: `MSYS_NO_PATHCONV=1`
  2. Pass a script path (not an inline `bash -c`) to avoid nested quoting hell
  3. Have the script source nvm itself — `wsl -- bash /path/to/script.sh` does NOT load `.bashrc`
- Both 7B/8B coding models hit ~85 tok/s on a 3070 — that headline beats most "you need an A100" assumptions.
- llama3.1:8b's algorithm-prompt failure (using `pop(0)` after the prompt explicitly asks for O(n+m)) is the cleanest demo of why 7B/8B models still need verification on real coding work.

**Still pending user actions** (unchanged from above)
1. Register `soloaiguy.com`
2. Create empty GitHub repo `soloaidev`
3. Push initial commit + enable GH Pages
4. Apply for affiliates per `pipeline/affiliate-signups.md`

---

### Session addendum 2 — 2026-04-25 (extending the autonomous block)

**Shipped**
- Second benchmark run captured (`scripts/results/benchmark-20260424-235321.json`). Combined averages:
  - qwen2.5-coder:7b: **90.2 tok/s**, 191 ms TTFT
  - llama3.1:8b: 81.7 tok/s, 235 ms TTFT
  - **New finding from run #2:** llama wrote a pytest with a wrong assertion (`reverse("Bonjour") == "BourgnonJ"` — actual is `"ruojnoB"`). qwen was correct on both runs. Algorithmic correctness is *unstable* on llama; consistent on qwen.
  - Post #3 (`qwen-3070-benchmark`) updated with averaged numbers and the new finding.
- Scheduled-agent template at `scripts/agent-cron.sh` — cron-runnable, picks first un-researched queue item, calls Ollama directly via `/api/generate` (originally tried Aider, but Aider chats instead of editing on a research prompt — empty diffs).
- End-to-end test: 9-second run, produced `pipeline/research/2026-04-25-aider-vs-cline-vs-continue-dev-solo-dev-shootout.md`. Output is structurally fine, factually unreliable (invented version numbers, hallucinated tool name "Solo Dev"). That's the actual value: a starting scaffold to verify, not finished research.
- Post #5 drafted: `cron-driven-agent.md` (target ship 2026-05-08), folds the real cron output (warts and all) into the pitch.
- Keyword queue pruned: items #1, #2, #3 moved to a "Drafted" section since they're now in the calendar.

**Build state**
- 7 static pages, build clean, drafts excluded.
- All session changes committed locally (no remote yet).

**Memory updated**
- `soloaidev_project.md` — refreshed with current editorial state (4 posts drafted, site features in place).
- `wsl_build_invocation.md` — captured the `MSYS_NO_PATHCONV=1 wsl -- bash /path/script.sh` pattern as a reference memory.
- `MEMORY.md` index updated.

---

### Session addendum 3 — 2026-04-25 (rebrand + deploy)

**Brand pivot mid-flight**
- User had a change of heart at the domain registrar: `soloaidev` → **`soloaiguy`**.
- Bulk rebrand executed via `scripts/rebrand.sh` (sed across 17 files): site URL, package name, all copy, repo URL, post slug `hello-solo-ai-dev` → `hello-solo-ai-guy`, WSL dir `~/builds/soloaidev` → `~/builds/soloaiguy`.
- Build still green post-rebrand.

**Shipped**
- **Domain registered:** `soloaiguy.com` (Namecheap, order 200717084, ~$11/yr).
- **GitHub repo created:** `xiyotec/soloaiguy` (public). Username is `xiyotec`, not `Xiyo`.
- **Initial push:** required `gh auth refresh -s workflow` to grant the workflow scope (push rejected without it), then `gh auth setup-git` to wire gh as the git credential helper (push hung silently otherwise).
- **GH Pages deploy fix:** initial workflow used `node-version: 20`, but Astro 6 requires `>=22.12`. Bumped to `node-version: 22`. Two failed runs before that fix.
- **DNS configured at Namecheap:** 4 A records (`185.199.108–111.153`) on `@`, plus CNAME `www` → `xiyotec.github.io.`. User initially typed `0` instead of `@` for Host on all 4 A records — caught via screenshot, walked through the fix.
- **SSL approved + HTTPS enforced:** cert covers `soloaiguy.com` and `www.soloaiguy.com`, expires 2026-07-24.
- **Site is live:** `https://soloaiguy.com/` returns 200.

**Learned (this block)**
- The `mode change 100755 => 100644` on shell scripts is a UNC-path footgun: editing scripts via `\\wsl.localhost\...` strips the exec bit. Restore with `chmod +x scripts/*.sh` and a follow-up commit.
- `gh push` over OAuth needs the **`workflow` scope** to push anything under `.github/workflows/`. The default `repo` scope is not enough.
- After `gh auth login`, you still need `gh auth setup-git` for git itself to use gh's token. Without it, `git push` hangs because no credential helper is wired.
- Astro's Node version floor moves with minor releases — pin the workflow to the actual repo Node, not whatever was current last quarter.

**Spend update**
| Item | Amount |
|---|---|
| Domain (`soloaiguy.com`, 1yr) | $11.18 |
| Anthropic API (today) | est. <$2 |
| Hosting | $0 (GH Pages) |
| **New total** | **~$13** |

**Still pending user actions**
1. Verify Namecheap contact email within 15 days (ICANN requirement — they sent a verification link).
2. Apply for affiliates per `pipeline/affiliate-signups.md`.
3. Optional: install the cron entry below to run the research agent nightly.

**Cron schedule (proposed)**
```cron
# Run research agent nightly at 02:30 local
30 2 * * * /home/xiyo/builds/soloaiguy/scripts/agent-cron.sh >> /home/xiyo/builds/soloaiguy/scripts/cron.log 2>&1
```
Install with `crontab -e` in WSL. The script picks the next un-researched queue item and writes a scaffold to `pipeline/research/`.

---

### Session addendum 4 — 2026-04-25 (cron + affiliates + brand assets)

**Shipped**
- **Cron installed** — nightly research agent at 02:30 local in WSL crontab. Logs to `scripts/cron.log` (gitignored). First run will fire at 02:30 tonight.
- **Brand logo** — `public/logo.png` (512×512, slate-900 navy bg, slate-50 wordmark, sky-400 accent dot). Generated by `scripts/make-logo.py` (Pillow via `uv run`). Re-runnable for variants.
- **Tier 1 affiliate apps submitted:**
  - **Amazon Associates** — auto-approved on signup. 180-day clock to first qualifying sale starts now.
  - **Namecheap** — submitted via Impact marketplace (Namecheap migrated from CJ to Impact). Application status: "In Review", typical 2–7 day turnaround.
- **Impact verification** — meta tag added to `BaseLayout.astro`:
  ```html
  <meta name="impact-site-verification" value="0041527d-52a1-4105-a015-60558032e2e1" />
  ```
  Belt-and-suspenders: `public/impact-site-verification.html` carries the same tag at a static URL.
- **Hardened gitignore** — `.affiliates.local`, `scripts/cron.log`, `pipeline/research/` now excluded.
- **Secrets template** — empty `~/.affiliates.local` (NOT in repo) with field labels for each program's ID/token.

**Affiliate flow gotchas (worth remembering)**
- Namecheap's affiliate program is **Impact**, not their own platform. CJ is the alternate but skews enterprise — pick Impact for solo creators.
- Impact tax form was auto-translated to Vietnamese based on browser locale. Pick **"Tôi không đăng ký thuế gián tiếp"** (= "I am not registered for indirect tax") if you have no VAT/GST/HST registration.
- Impact business category: **Content/Reviews** (not Influencer / Loyalty / Deal — those misrepresent what we are).
- Impact promotion methods: **Add Website only** — don't inflate channels you don't actually run; common rejection reason.
- Impact keyword field: **alphanumeric ASCII only**, comma-separated, no hyphens, no spaces. `developer-tools` fails; `developertools` passes.
- Impact required a logo — they don't accept "no logo for now". Generate via `scripts/make-logo.py`.
- After picking a verify method, the modal closes saying "task completed" but doesn't *trigger* the crawl. Verification can stay "Chưa được xác minh" even after submission moves to "In Review" — Impact appears to verify silently during review or on a polled schedule.

**Spend update**
| Item | Amount |
|---|---|
| Domain (`soloaiguy.com`, 1yr) | $11.18 |
| Anthropic API (today, est.) | <$3 |
| Hosting | $0 (GH Pages) |
| Affiliate signups (Amazon, Impact) | $0 |
| **Total to date** | **~$14** |

**Still pending user actions**
1. Verify Namecheap **domain contact email** within 15 days of 2026-04-25 (ICANN — separate from affiliate signup).
2. Wait on Namecheap Impact application response (email).
3. (Optional) Hetzner referral if/when relevant.
4. Tier 2 affiliate apps after 2–3 posts ship (~2026-05-15).

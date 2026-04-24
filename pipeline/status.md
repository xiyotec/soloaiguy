# Weekly Status Log

Each entry: what shipped, what we learned, what's costing money, what's next.

---

## Week of 2026-04-24 (week 0 — kickoff)

**Shipped this week**
- Domain decision: `soloaidev.com` (not registered yet — user action)
- Astro 5 site scaffolded: content collections, MDX, sitemap, RSS, robots.txt
- BaseLayout + PostLayout + homepage + /posts/ index + [...slug] route
- Lean global CSS with auto dark mode (~5KB on the wire)
- GitHub Actions deploy workflow ready (waiting on repo)
- Content pipeline scaffolded: keyword-queue (10 ranked topics), editorial-calendar, status, post-template, affiliates tracker
- **Post #1 published:** "Hello from Solo AI Dev" — meta/intro post
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
1. **Register `soloaidev.com`** — Cloudflare Registrar (~$10/yr, no markup) or Namecheap (~$11/yr).
2. **Create empty GitHub repo** named `soloaidev` (public). Don't initialize with README — we already have one.
3. **Push initial commit + enable GH Pages.** From WSL: `cd ~/builds/soloaidev && git remote add origin git@github.com:<username>/soloaidev.git && git push -u origin main`. Then in repo Settings → Pages, set source to "GitHub Actions".
4. **Apply for affiliates** — see `pipeline/affiliate-signups.md` for the order to do them.

**Next session targets**
- Build a tiny benchmark harness for post #3 (qwen-3070-benchmark)
- Add Cloudflare Web Analytics snippet (free, no consent banner needed) once domain is live
- Email capture component (for future newsletter)
- Scheduled-agent template — research-tomorrow's-keywords overnight via cron

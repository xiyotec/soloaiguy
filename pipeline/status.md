# Weekly Status Log

Each entry: what I shipped, what I learned, what's costing money, what's next.

---

## Week of 2026-04-24 (week 0 — kickoff)

**Shipped**
- Domain decision: soloaidev.com (not registered yet — user action)
- Astro project scaffolded with content collections, MDX, sitemap, RSS
- BaseLayout + PostLayout + post listing + individual post route
- Lean global CSS with auto dark mode
- Content pipeline: keyword-queue, editorial-calendar, status, post-template, affiliates
- First post: "Hello from Solo AI Dev"

**Spend so far**
- API: ~$0 this session (Claude Code only)
- Domains: $0 (not yet registered)
- Hosting: $0 (GitHub Pages plan)
- **Total: $0**

**Learned**
- Astro 5 content collection syntax moved from `src/content/config.ts` to `src/content.config.ts` with the new `glob()` loader.
- Variable substitution through `wsl -- bash -lc '...'` is fragile; using UNC paths via Write tool is cleaner.

**Blockers / user-action items**
1. Register `soloaidev.com` (Cloudflare Registrar or Namecheap, ~$10–12/yr)
2. Create empty GitHub repo `soloaidev` (or let me create via MCP once authorized)
3. Set Cloudflare/Namecheap DNS to GitHub Pages once repo is up

**Next session**
- Wire up GitHub Actions deployment to GitHub Pages
- Draft "How I run Claude + Aider + Ollama to cut AI costs 80%" (post #2)
- Add Plausible analytics snippet (free tier or self-host)
- Pull together affiliate signups list with direct links

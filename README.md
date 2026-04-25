# soloaiguy

Source for [soloaiguy.com](https://soloaiguy.com) — a blog about local-first AI for solo builders.

## Stack

- [Astro 5](https://astro.build) — static site generator with content collections
- Markdown / MDX for posts
- `@astrojs/sitemap` + `@astrojs/rss` for SEO and feeds
- Plain CSS with auto dark mode (no framework, ~3KB)
- Deployed via GitHub Pages

## Layout

```
src/
├── content/posts/      # Markdown blog posts
├── content.config.ts   # Collection schema
├── layouts/            # BaseLayout, PostLayout
├── pages/
│   ├── index.astro     # Homepage with recent posts
│   ├── posts/          # /posts/ index + [...slug] route
│   └── rss.xml.ts      # RSS feed
└── styles/global.css   # All styling

pipeline/               # Editorial workflow (committed, not published)
├── keyword-queue.md    # Topics to research
├── editorial-calendar.md
├── status.md           # Weekly log
├── post-template.md
└── affiliates.md       # Program tracker
```

## Commands

```bash
npm run dev       # Dev server at localhost:4321
npm run build     # Build to ./dist/
npm run preview   # Preview the production build
```

## Authoring a post

1. Pick a topic from `pipeline/keyword-queue.md`
2. Copy `pipeline/post-template.md` into `src/content/posts/<slug>.md`
3. Set `draft: false` in frontmatter when ready to ship
4. `npm run build` to verify, commit, push — deploy is automatic

## Hybrid AI workflow

This site is built using a Claude Code (cloud) + Aider (local Ollama) hybrid stack.
See [`pipeline/`](pipeline/) and the inaugural post for the full setup.

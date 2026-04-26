# Atlas Memory Index

This file is loaded into Atlas's system prompt every turn. Keep entries short — this is an index, not the memory itself. Each entry: `- [Title](file.md) — one-line hook`. Detailed notes live in the linked files; Atlas can read them on demand with `read_file`.

Atlas writes here when it learns something worth remembering across conversations. Add an entry below; create the underlying file with `write_file` to `scripts/atlas/memory/<topic>.md`.

## What to remember
- **Xiyo facts** — preferences, working style, decisions Xiyo has made
- **Project facts** — non-obvious context about soloaiguy, affiliates, infra
- **Lessons** — mistakes Atlas made and how to avoid them next time
- **Patterns** — what Xiyo accepts vs rejects, what works on the site

## What NOT to remember
- Things Xiyo already knows that are obvious from the codebase (read the file)
- Ephemeral status (this week's draft count, current spend) — query live
- Duplicate entries (update the existing file instead)

## Memories

- [Market Intel Apr 2026](market-intel-apr-2026.md) — AI tool landscape, GitHub trending repos, dev pain points, and content angles as of April 2026.
- [Computer Use TODO](computer-use-todo.md) — Xiyo wants to wire up computer use for Atlas; not done yet, remind if it hasn't been tackled.
- [Atlas Lessons](atlas-lessons.md) — Mistakes Atlas has made and how to avoid them: truncation, empty replies, mid-task dropouts.

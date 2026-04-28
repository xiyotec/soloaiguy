# atlas-lessons.md

Operational lessons Atlas has learned. Each entry is a pattern + how to detect + how to respond.

## Truncation pattern (2026-04-26)

**Symptom:** A multi-step turn with several tool calls runs out of `MAX_TOKENS` mid-reply, leaving the user with a half-finished response. The dropped half is usually the commit/file-write step at the end.

**Root cause:** `MAX_TOKENS=2048` was too tight for tool-use turns that included multiple `tool_result` blocks plus a final summary.

**Fix:** Bumped `MAX_TOKENS` to 4096, then 8192. Also commit results progressively across the loop instead of saving them for the final reply, so a truncated tail doesn't lose work.

**Detection going forward:** If a reply ends abruptly without a clear summary or ✅/❌ block, assume truncation. Re-check the actual filesystem / git state before asking the user for clarification — the work may be done even if the chat looks incomplete.

## "Fix yourself" means just fix it (2026-04-26)

When the user notices a problem with my behavior and tells me to fix it, the right move is to ship the patch *now* and report it as done — not to ask for permission, scope, or design feedback. The user already trusts me with the codebase; asking for sign-off on a one-line bug fix is friction.

The exception: anything that touches secrets, irreversible deletes, or off-brand decisions. Those still wait for /approve.

## /reset wipes the SQLite DB (2026-04-28)

The `/reset` command deletes all rows from the `messages` table, not just the in-memory context. Today's planning conversation got nuked when the user typed `/reset` to start fresh.

**Mitigation:** Telegram itself preserves the chat history independently; the user can scroll up to recover any context they need. Atlas can also offer to summarise the recent chat into MEMORY.md before /reset clears it.

## Same Telegram bot can have polling conflicts (2026-04-28)

If two Atlas instances poll the same bot (e.g. WSL + Windows), Telegram returns 409 to whichever loses. Symptom: one instance keeps logging "Conflict: terminated by other getUpdates request". Fix: only one Atlas owns the bot at a time, or use separate bots.

## End every reply with a status block

Going forward, every multi-step reply ends with:

```
✅ Done: <list>
❌ Pending: <list, or 'nothing'>
```

So Xiyo can see at a glance whether anything got dropped.

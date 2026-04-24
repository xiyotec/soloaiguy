---
title: "How I run Claude Code + Aider + Ollama hybrid and cut AI costs ~80%"
description: "Stop paying frontier prices for grunt work. Here's the exact stack — configs, decision rules, and real numbers — that lets one model plan and another execute for free."
pubDate: 2026-04-28
tags: ["hybrid", "ollama", "aider", "claude-code", "cost"]
draft: false
---

## The problem

If you use Claude Code (or Cursor, or any frontier-model-backed agent) seriously, you've felt this: half your token spend goes to renaming variables, adding docstrings, and writing boilerplate. The other half does actual reasoning.

The first half doesn't need a frontier model. It needs *any* model that can read a function signature and follow instructions.

The trick isn't picking one tool. It's picking two, and routing tasks between them.

## The short answer

I run **Claude Code** (cloud) for anything that needs judgment, and **Aider + Ollama** (local, on a single 8GB GPU) for anything mechanical. Claude Code has a global rule that tells it to delegate the cheap stuff automatically.

Net result for me: roughly an 80% reduction in API spend on the same workload, with a quality dip I can live with on the delegated tasks.

The whole stack runs on a normal desktop. WSL2, Ubuntu 24.04, RTX 3070. No cloud GPU, no Docker swarm.

## The mental model

Two questions for every task:

1. **Can I describe this in one sentence?**
2. **Does this need judgment, or just mechanical execution?**

| Task | One sentence? | Judgment? | Goes to |
|---|---|---|---|
| "Add docstrings to `utils.py`" | yes | no | Aider |
| "Rename `getUser` to `fetchUser` across `src/api/`" | yes | no | Aider |
| "Add type hints to `helpers.py`" | yes | no | Aider |
| "Why is the login flow timing out under load?" | no | yes | Claude Code |
| "Refactor this module so it's easier to test" | no | yes | Claude Code |
| "Should I use server actions or route handlers here?" | no | yes | Claude Code |

If both answers point to "simple," it goes local. If either points to "needs judgment," it stays on the frontier model.

## The setup

### 1. Ollama with a coding-tuned 7B

```bash
# Install (Linux/WSL)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model that actually codes
ollama pull qwen2.5-coder:7b
```

I tried llama3.1:8b first. It's fine for general chat. For code edits, qwen2.5-coder:7b is meaningfully better — it understands diff format, respects existing patterns, and rarely invents APIs that don't exist.

If you have more than 8GB VRAM, `qwen2.5-coder:14b` is even better.

### 2. Aider, configured to use Ollama

```bash
# uv keeps it isolated
uv tool install aider-chat
```

Then `~/.aider.conf.yml`:

```yaml
model: ollama_chat/qwen2.5-coder:7b
model-metadata-file: ~/.aider.model.metadata.json
auto-commits: true
gitignore: true
```

And `~/.aider.model.metadata.json` (Ollama defaults a tiny context window — this fixes it):

```json
{
  "ollama_chat/qwen2.5-coder:7b": {
    "max_input_tokens": 32768,
    "max_output_tokens": 4096
  }
}
```

Plus one line in `~/.bashrc`:

```bash
export OLLAMA_API_BASE=http://localhost:11434
```

You can now run `aider` in any project and it'll talk to your local model. Zero API cost, runs on your GPU.

### 3. Tell Claude Code to delegate

This is the part most people miss. Without instructions, Claude Code happily uses its own (expensive) tokens for everything you ask. To get it to route, you need a global rule.

Drop this in `~/.claude/CLAUDE.md` (create the file if it doesn't exist):

```markdown
## Hybrid Delegation

You have access to local Aider + Ollama running in WSL2. Use it for tasks
that don't need your judgment, to save Anthropic API tokens.

**Delegate when ALL are true:**
- Task can be described in one sentence
- Files are specifically named
- No cross-file reasoning beyond named files
- No architectural or debugging judgment required

**Do NOT delegate:**
- Bug investigation, exploration, or anything requiring "why?"
- Architectural decisions
- Security-sensitive code
- Tasks the user explicitly asked you to handle

**Invocation pattern:**

\`\`\`bash
wsl -d Ubuntu-24.04 -- bash -lc 'cd <wsl-path> && aider --yes-always --message "<task>" <files>'
\`\`\`

Announce the delegation in one sentence before invoking, so the user can veto.
After Aider finishes, read the modified files to verify, then report what
changed in one line.

If Aider produces a wrong or empty diff twice on the same task, stop
delegating it and do the work yourself.
```

That's it. Claude Code now reads this rule on every session and applies it automatically.

## A real example

Yesterday I asked Claude Code: *"Add JSDoc comments to every exported function in `src/lib/auth.ts`."*

Pre-hybrid, this would have run as ~15K Claude tokens — read the file, parse it, generate comments, write them back, possibly re-read to verify.

With the rule in place, Claude Code instead:

1. Recognized this is a one-sentence, mechanical task on a named file.
2. Said: *"Simple JSDoc addition — delegating to local Aider to save tokens."*
3. Ran `aider --yes-always --message "Add JSDoc to all exported functions in src/lib/auth.ts" src/lib/auth.ts`.
4. Aider read the file, generated the docs locally on my GPU, wrote them back, auto-committed.
5. Claude Code re-read the file to verify the change landed and reported back: *"Added JSDoc to 4 exported functions. Verified."*

Total Claude tokens used: maybe 800. Maybe.

## What it costs

Rough monthly numbers from my own usage:

| Stack | Monthly API spend |
|---|---|
| Claude Code only (every task) | ~$60 |
| Hybrid (delegating ~70% of tasks) | ~$12 |
| Pure local (Aider+Ollama only) | $0 |

Pure local sounds tempting, and it's free. But you'll feel the quality drop fast on anything non-trivial. Hybrid is the sweet spot: cheap on the cheap stuff, expensive only where it matters.

Electricity cost of running Ollama on the 3070 during normal use: a couple cents a day. Effectively free.

## When it breaks

The local model isn't a frontier model. Things to watch for:

- **Multi-file refactors** confuse 7B models fast. If a task touches more than 2–3 files with non-trivial coupling, it stays on Claude Code.
- **Empty diffs** — Aider sometimes "agrees" with the request but doesn't actually change anything. Always verify by reading the file after.
- **Drift on style** — local models can ignore project conventions if they're not obvious from the file you're editing. For style-sensitive code, keep it on Claude.
- **Long context** — anything beyond ~24K tokens of input degrades fast on 7B models. Don't dump big codebases into the context window.

The CLAUDE.md rule above includes a "fail twice, stop delegating" clause specifically for these cases.

## Optional upgrade: architect mode

If you have a small Anthropic budget, Aider has an "architect" mode where one model plans and another executes. Best combo I've found:

- **Architect:** `claude-haiku-4-5` (cheap, fast, smart enough for short plans)
- **Editor:** `ollama_chat/qwen2.5-coder:7b` (free, executes the plan locally)

Haiku at planning + qwen at execution is the closest a $5/month setup gets to frontier-quality multi-step work.

To enable, add to `~/.aider.conf.yml`:

```yaml
architect: true
model: anthropic/claude-haiku-4-5-20251001
editor-model: ollama_chat/qwen2.5-coder:7b
editor-edit-format: diff
```

And `export ANTHROPIC_API_KEY=...` in `~/.bashrc`.

This is what I'm running now. The cost difference between this and pure-local is small (~$3/month for me); the quality difference is large.

## Take it from here

Three steps to copy the setup:

1. **Install Ollama + qwen2.5-coder:7b.** 10 minutes. [Ollama install instructions.](https://ollama.com/download)
2. **Install Aider, drop in the configs above.** 5 minutes.
3. **Add the delegation rule to `~/.claude/CLAUDE.md`.** 1 minute.

Run `aider` in a project and try a delegated task end-to-end. Once it works, the rule starts paying off automatically — you don't have to think about routing, you just work, and Claude Code routes for you.

Next post in this series: real benchmarks of qwen2.5-coder:7b on a 3070 — tokens/sec, code quality vs llama3.1, and where the model actually breaks.

---

*Subscribe via [RSS](/rss.xml). I'm writing through the entire build of this stack — what works, what doesn't, what it costs.*

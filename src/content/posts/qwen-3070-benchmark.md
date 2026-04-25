---
title: "qwen2.5-coder:7b on a 3070: real benchmarks"
description: "Measured tokens-per-second, time-to-first-token, and code quality of qwen2.5-coder:7b vs llama3.1:8b on an 8GB consumer GPU. Numbers, not vibes."
pubDate: 2026-05-01
tags: ["ollama", "benchmark", "qwen", "llama", "rtx-3070"]
draft: true
---

> **Draft note:** Numbers below are averaged across two benchmark runs on my own machine on 2026-04-24. I'll add at least one more run before publish; if it shifts the headline, I'll update. The harness is reproducible — see the bottom of this post.

## The question

Everyone has an opinion on which 7B/8B model is "better for coding." Almost nobody publishes the numbers behind their opinion, on hardware a normal person owns.

So I ran one. Two models, five representative coding prompts, two runs each (with a discarded warmup before each measured run), on an RTX 3070 (8GB VRAM). All numbers below are from `/api/generate` streaming responses, measured with `time.perf_counter()`.

## The setup

- **GPU:** RTX 3070, 8GB VRAM
- **OS:** Ubuntu 24.04 in WSL2 on Windows 11
- **Runtime:** Ollama (latest)
- **Models tested:** `qwen2.5-coder:7b` (Q4_K_M, ~4.7GB) and `llama3.1:8b` (Q4_K_M, ~4.9GB)
- **Method:** stream-parse responses; warmup discarded; one measured run per (model, prompt) per benchmark execution; numbers below are means across 2 benchmark runs

## Headline numbers

Steady-state throughput, averaged across all five prompts and both runs:

| Model | tok/s (avg of 2 runs) | TTFT (avg of 2 runs) |
|---|---|---|
| qwen2.5-coder:7b | **90.2** | 191 ms |
| llama3.1:8b | 81.7 | 235 ms |

Translation: both feel snappy. Time-to-first-token under 250 ms is below the threshold where you'd call it "instant" in practice. Throughput north of 80 tok/s means a 200-token reply lands in ~2.5 seconds. For interactive coding, this is fine.

qwen runs about **10% faster** than llama on this hardware on the prompts I tested.

## Per-prompt numbers (averaged)

| Prompt | qwen tok/s | llama tok/s | qwen total | llama total |
|---|---|---|---|---|
| merge-sorted (algorithm) | 88.1 | 82.9 | 1.35 s | 1.25 s |
| type-hints (modification) | 89.8 | 80.7 | 0.71 s | 0.77 s |
| list-comp (transformation) | 91.6 | 82.8 | 0.46 s | 0.46 s |
| unit-test (test-gen) | 90.6 | 79.2 | 0.94 s | 1.43 s |
| regex-explain (explanation) | 90.7 | 82.9 | 1.54 s | 0.74 s |

A few things to note:

- qwen is faster on every prompt, by 6–14%.
- TTFT is stable across runs (qwen 180–195 ms, llama 220–250 ms).
- Throughput has run-to-run variance of about ±5%. That's why I averaged.

## Quality is where it actually splits

Speed only matters if the output is right. Three real findings from the runs:

### 1. llama3.1:8b's algorithm correctness is *unreliable*

In run #1, llama returned this `merge_sorted`:

```python
def merge_sorted(a, b):
    result = []
    while a and b:
        if a[0] < b[0]:
            result.append(a.pop(0))
        else:
            result.append(b.pop(0))
    result.extend(a or b)
    return result
```

`list.pop(0)` is O(n). Calling it inside a loop makes the whole function O(n²) on the input length — even though the prompt explicitly asks for `O(n+m)`.

In run #2, llama produced the correct two-pointer version with index variables. Same prompt, same model, different answer.

qwen produced the correct two-pointer version on **both** runs.

This is the cleanest demonstration I've seen of why 7B/8B models still need verification on real algorithmic work: the output isn't just about average quality, it's about *consistency*. qwen wasn't always faster — it was always **right** on this prompt.

### 2. llama wrote a test with an incorrect expected output

Asked to write a pytest covering "normal, empty, unicode" for a string-reverse function, run #2 llama produced:

```python
def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse(u"Bonjour") == u"BourgnonJ"  # ← wrong
```

`reverse("Bonjour")` is `"ruojnoB"`, not `"BourgnonJ"`. The test would fail when actually run. It's a confidently wrong assertion — exactly the kind of failure mode that's hardest to spot in code review.

qwen wrote a clean unicode test using `"你好" → "好你"` on both runs. Correct, idiomatic, hits multi-byte handling.

### 3. Both regex explanations are correct, but qwen's are more thorough

For the regex-explain prompt, qwen wrote a numbered breakdown of every group plus a plain-English summary at the end. llama wrote one or two sentences. Both correct.

This is a real taste call. For docs, qwen's verbosity wins. For inline chat, llama's brevity does.

## Where 7B models actually break

The benchmark above tests well-bounded coding tasks. Things both models struggled with on extended testing (not in the harness, but worth flagging):

- **Cross-file refactors with implicit coupling.** Anything where the right answer requires holding 3+ files in context at once. Both models hallucinate or make local-only changes that break callers.
- **Library APIs they only half-remember.** Both will confidently invent functions in `pandas` or `requests` that don't exist. qwen does this less often than llama in my experience, but neither is reliable.
- **Anything involving "why."** Asking either model to debug requires you to do most of the diagnostic work yourself.

The harness above is deliberately scoped to tasks worth delegating to a local model. For the rest, [keep it on the frontier model](/posts/hybrid-claude-aider-ollama/).

## VRAM, idle and active

Rough numbers, `nvidia-smi` polled every second:

- **Idle (model loaded, no inference):** ~5.2 GB
- **Active (mid-generation):** ~5.6 GB
- **Headroom on an 8GB card:** comfortable

You can run either model alongside a browser, a couple of IDE windows, and Discord without OOM. If you push past ~6.5 GB used by other processes, you'll start swapping and tok/s drops fast — but in normal use, fine.

If you have a 12GB+ card, the 14B versions of these models are a meaningfully bigger jump than going from 7B to 8B. Worth knowing.

## What I'd actually run

For mechanical edits delegated by Claude Code (the hybrid setup from [the previous post](/posts/hybrid-claude-aider-ollama/)): **qwen2.5-coder:7b**. Faster, better instruction-following on code-specific prompts, more consistent output — that last one is the one that matters in production.

For general-purpose chat where coding isn't the focus: either is fine.

For anything where correctness matters more than the round-trip: don't use a 7B. Use Claude or Sonnet. Save the local model for the boilerplate.

## Reproduce it yourself

The harness is one Python file with no dependencies beyond the standard library. Pull the models, run it, compare to my numbers:

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
python3 scripts/benchmark.py
```

Output goes to `scripts/results/benchmark-<timestamp>.json`. Run it 2–3 times yourself; the run-to-run quality variance is real.

I'm interested in how this looks on a 3060, 4060, 4070, and Apple Silicon — open issues with your numbers.

---

*Subscribe via [RSS](/rss.xml). Next post: budget breakdown for solo devs who want agentic coding under $10/month.*

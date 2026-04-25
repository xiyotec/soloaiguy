#!/usr/bin/env python3
"""
Benchmark Ollama models on representative coding tasks.

Measures per (model, prompt):
- time to first token (latency)
- total time
- output token count (rough — newline-split is good enough)
- tokens/sec
- raw output (for later quality scoring)

One warmup run + one measured run per (model, prompt). Warmup absorbs
model-load time so the measured run reflects steady-state.

Usage:
    python3 benchmark.py            # default models + prompts
    python3 benchmark.py --quick    # one prompt only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

MODELS = ["qwen2.5-coder:7b", "llama3.1:8b"]

PROMPTS = [
    {
        "id": "merge-sorted",
        "category": "algorithm",
        "prompt": "Write a Python function `merge_sorted(a, b)` that merges two sorted lists into one sorted list in O(n+m) time. Just the function. No prose.",
    },
    {
        "id": "type-hints",
        "category": "modification",
        "prompt": "Add type hints to this Python function. Return only the modified function.\n\ndef fetch(url, timeout=30):\n    r = requests.get(url, timeout=timeout)\n    return r.json()",
    },
    {
        "id": "list-comp",
        "category": "transformation",
        "prompt": "Convert this to a list comprehension. Return only the one-line expression.\n\nresult = []\nfor x in data:\n    if x > 0:\n        result.append(x * 2)",
    },
    {
        "id": "unit-test",
        "category": "test-generation",
        "prompt": "Write a pytest unit test for this function. Cover normal case, empty string, unicode. Return only the test code.\n\ndef reverse(s: str) -> str:\n    return s[::-1]",
    },
    {
        "id": "regex-explain",
        "category": "explanation",
        "prompt": "Explain what this regex matches in plain English, in one short paragraph.\n\n^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d).{8,}$",
    },
]


def call_ollama(model: str, prompt: str) -> dict:
    """Stream-parse the response so we can measure time-to-first-token."""
    body = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    ttft: float | None = None
    chunks: list[str] = []
    eval_count = 0
    eval_duration_ns = 0
    prompt_eval_count = 0
    error: str | None = None

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                if not raw.strip():
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if "response" in obj and obj["response"]:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    chunks.append(obj["response"])
                if obj.get("done"):
                    eval_count = obj.get("eval_count", 0)
                    eval_duration_ns = obj.get("eval_duration", 0)
                    prompt_eval_count = obj.get("prompt_eval_count", 0)
                    break
    except Exception as e:  # noqa: BLE001 — we want any failure recorded
        error = repr(e)

    total = time.perf_counter() - t0
    output = "".join(chunks)
    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns else None

    return {
        "model": model,
        "ttft_sec": ttft,
        "total_sec": total,
        "output_chars": len(output),
        "output_tokens_reported": eval_count,
        "prompt_tokens_reported": prompt_eval_count,
        "tokens_per_sec": tps,
        "output": output,
        "error": error,
    }


def run_one(model: str, prompt_obj: dict) -> dict:
    print(f"  warmup {model} :: {prompt_obj['id']} ...", file=sys.stderr)
    _ = call_ollama(model, prompt_obj["prompt"])
    print(f"  measure {model} :: {prompt_obj['id']} ...", file=sys.stderr)
    measured = call_ollama(model, prompt_obj["prompt"])
    return {
        "prompt_id": prompt_obj["id"],
        "category": prompt_obj["category"],
        "prompt": prompt_obj["prompt"],
        **measured,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="Single prompt only")
    args = ap.parse_args()

    prompts = PROMPTS[:1] if args.quick else PROMPTS

    started = datetime.now().isoformat(timespec="seconds")
    print(f"Benchmark started: {started}", file=sys.stderr)
    print(f"Models: {MODELS}", file=sys.stderr)
    print(f"Prompts: {len(prompts)}", file=sys.stderr)

    results = []
    for model in MODELS:
        print(f"\n=== {model} ===", file=sys.stderr)
        for prompt_obj in prompts:
            results.append(run_one(model, prompt_obj))

    finished = datetime.now().isoformat(timespec="seconds")

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"benchmark-{stamp}.json"

    payload = {
        "started": started,
        "finished": finished,
        "models": MODELS,
        "ollama": OLLAMA,
        "results": results,
    }
    out_file.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote: {out_file}", file=sys.stderr)

    print("\n=== Summary ===", file=sys.stderr)
    for r in results:
        if r.get("error"):
            print(f"{r['model']:25s} {r['prompt_id']:15s} ERROR: {r['error']}", file=sys.stderr)
            continue
        tps = r.get("tokens_per_sec")
        ttft = r.get("ttft_sec")
        tps_s = f"{tps:6.1f} tok/s" if tps else "       —     "
        ttft_s = f"{ttft*1000:5.0f} ms" if ttft else "    —  "
        print(
            f"{r['model']:25s} {r['prompt_id']:15s} ttft={ttft_s}  {tps_s}  total={r['total_sec']:5.2f}s  out={r['output_tokens_reported']} tok",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

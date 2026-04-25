#!/usr/bin/env python3
"""affiliate-injector.py — inject Amazon affiliate links into posts.

Reads ~/.affiliates.local for `amazon-associates:` ID. If empty, exits 0
(no-op — safe to run on a schedule before the ID is filled in).

Reads product map from pipeline/affiliate-map.txt. For each post in
src/content/posts/*.md, replaces the FIRST plain mention of each mapped
product with a markdown link tagged with the Amazon Associates ID, and
appends an FTC + Amazon-required disclosure block once per post.

Idempotent: already-linked products are skipped, disclosure marker prevents
duplication. Build-gates with `npm run build` before committing. NEVER pushes
to origin.

Usage:
    affiliate-injector.py [--dry-run] [--no-commit] [POST_FILE...]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO / "src" / "content" / "posts"
MAP_FILE = REPO / "pipeline" / "affiliate-map.txt"
AFFILIATES_LOCAL = Path.home() / ".affiliates.local"

DISCLOSURE_MARKER = "<!-- affiliate-disclosure -->"
DISCLOSURE_BLOCK = (
    f"{DISCLOSURE_MARKER}\n"
    "*Some links in this post are affiliate links. They cost you nothing extra "
    "but help fund this blog. I only link to tools I actually use.*\n"
    "\n"
    "*As an Amazon Associate I earn from qualifying purchases.*"
)


def read_amazon_id() -> str:
    env_id = os.environ.get("AMAZON_ASSOCIATES_ID", "").strip()
    if env_id:
        return env_id
    if not AFFILIATES_LOCAL.exists():
        return ""
    for raw in AFFILIATES_LOCAL.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("amazon-associates:"):
            return line.split(":", 1)[1].strip().strip('"\'')
    return ""


def load_map() -> list[tuple[str, str]]:
    if not MAP_FILE.exists():
        return []
    products: list[tuple[str, str]] = []
    for raw in MAP_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        match, query = line.split("|", 1)
        products.append((match.strip(), query.strip()))
    return products


def add_disclosure(text: str) -> str:
    if DISCLOSURE_MARKER in text:
        return text
    block = "\n" + DISCLOSURE_BLOCK + "\n"
    body_start = 0
    if text.startswith("---\n"):
        end_fm = text.find("\n---\n", 4)
        if end_fm > 0:
            body_start = end_fm + 5
    last_sep = text.rfind("\n---\n", body_start)
    if last_sep > 0:
        return text[:last_sep] + block + text[last_sep:]
    if not text.endswith("\n"):
        text += "\n"
    return text + block


def inject_post(text: str, products: list[tuple[str, str]], amazon_id: str) -> tuple[str, list[str]]:
    new_text = text
    hits: list[str] = []
    for match, query in products:
        if re.search(rf"\[{re.escape(match)}\]\(", new_text):
            continue
        pattern = re.compile(rf"(?<![\w\-]){re.escape(match)}(?![\w\-])")
        m = pattern.search(new_text)
        if not m:
            continue
        url = f"https://www.amazon.com/s?k={query}&tag={amazon_id}"
        new_text = new_text[: m.start()] + f"[{match}]({url})" + new_text[m.end():]
        hits.append(match)
    if hits:
        new_text = add_disclosure(new_text)
    return new_text, hits


def verify_build() -> tuple[int, str]:
    cmd = (
        "set -e; "
        "export NVM_DIR=\"$HOME/.nvm\"; "
        "[ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\"; "
        f"cd '{REPO}'; "
        "npm run build"
    )
    proc = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return proc.returncode, (proc.stderr or proc.stdout)[-2000:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print diff without writing")
    parser.add_argument("--no-commit", action="store_true", help="write posts but skip git commit")
    parser.add_argument("files", nargs="*", help="specific post files (default: all)")
    args = parser.parse_args()

    amazon_id = read_amazon_id()
    if not amazon_id:
        print("[affiliate-injector] No Amazon Associates ID in ~/.affiliates.local")
        print("[affiliate-injector] Add the line:  amazon-associates: yourid-20")
        print("[affiliate-injector] (find your ID at https://affiliate-program.amazon.com → Account Settings)")
        return 0

    products = load_map()
    if not products:
        print(f"[affiliate-injector] empty product map at {MAP_FILE}")
        return 1

    files = [Path(f) for f in args.files] if args.files else sorted(POSTS_DIR.glob("*.md"))
    if not files:
        print(f"[affiliate-injector] no posts found in {POSTS_DIR}")
        return 0

    modified: list[Path] = []
    total_hits = 0
    for post in files:
        original = post.read_text()
        new_text, hits = inject_post(original, products, amazon_id)
        if not hits:
            continue
        total_hits += len(hits)
        print(f"\n[{post.name}] +{len(hits)}: {', '.join(hits)}")
        if args.dry_run:
            for h in hits:
                m = re.search(rf"\[{re.escape(h)}\]\([^)]+\)", new_text)
                if m:
                    s = max(0, m.start() - 40)
                    e = min(len(new_text), m.end() + 40)
                    print(f"  ...{new_text[s:e].replace(chr(10), ' ')}...")
        else:
            post.write_text(new_text)
            modified.append(post)

    if total_hits == 0:
        print("[affiliate-injector] no new injections (already up to date or no matches)")
        return 0

    if args.dry_run:
        print(f"\n[affiliate-injector] DRY RUN — would inject {total_hits} link(s)")
        return 0

    print(f"\n[affiliate-injector] modified {len(modified)} post(s), +{total_hits} link(s)")

    if args.no_commit:
        print("[affiliate-injector] --no-commit set; leaving working tree dirty")
        return 0

    print("[affiliate-injector] verifying build...")
    rc, tail = verify_build()
    if rc != 0:
        print("[affiliate-injector] BUILD FAILED — leaving changes for manual review")
        print(tail)
        return 1

    rel = [str(p.relative_to(REPO)) for p in modified]
    subprocess.run(["git", "-C", str(REPO), "add", *rel], check=True)
    msg = (
        f"feat(affiliates): inject Amazon links into {len(modified)} post(s)\n"
        f"\n"
        f"+{total_hits} affiliate link(s) added with FTC + Amazon disclosure block."
    )
    subprocess.run(["git", "-C", str(REPO), "commit", "-m", msg], check=True)
    print("[affiliate-injector] committed locally. push manually when ready to deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

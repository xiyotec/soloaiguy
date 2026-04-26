#!/usr/bin/env node
// Generates per-post OG images via Replicate FLUX-schnell.
// Idempotent: skips posts that already have an image at public/og/<slug>.png.
// Also generates public/og-default.png if missing (used by non-post pages).
//
// Usage:
//   REPLICATE_API_TOKEN=... node scripts/generate-og.mjs
//   REPLICATE_API_TOKEN=... node scripts/generate-og.mjs --force   # regenerate all

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const POSTS_DIR = path.join(ROOT, 'src/content/posts');
const OG_DIR = path.join(ROOT, 'public/og');
const DEFAULT_OG = path.join(ROOT, 'public/og-default.png');
const FORCE = process.argv.includes('--force');

const TOKEN = process.env.REPLICATE_API_TOKEN;
if (!TOKEN) {
  console.error('REPLICATE_API_TOKEN not set. Add it to ~/.soloaiguy.env and re-source.');
  process.exit(1);
}

const STYLE = 'Abstract digital tech art, deep navy and electric cyan gradient, geometric circuitry patterns, subtle grid lines, soft volumetric lighting, no text, no people, minimalist composition, 16:9 cinematic';

function parseFrontmatter(content) {
  const m = content.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return {};
  const out = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^(\w+):\s*(.*)$/);
    if (!kv) continue;
    let v = kv[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    out[kv[1]] = v;
  }
  return out;
}

async function exists(p) {
  try { await fs.access(p); return true; } catch { return false; }
}

async function generate(prompt, outPath) {
  console.log(`  prompt: ${prompt.slice(0, 90)}…`);
  let res;
  for (let attempt = 0; attempt < 5; attempt++) {
    res = await fetch('https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${TOKEN}`,
        'Content-Type': 'application/json',
        Prefer: 'wait=60',
      },
      body: JSON.stringify({
        input: {
          prompt,
          aspect_ratio: '16:9',
          output_format: 'png',
          num_outputs: 1,
          num_inference_steps: 4,
        },
      }),
    });
    if (res.status !== 429) break;
    const retry = parseInt(res.headers.get('retry-after') || '12', 10);
    console.log(`  rate-limited, sleeping ${retry}s…`);
    await new Promise(r => setTimeout(r, (retry + 2) * 1000));
  }
  if (!res.ok) {
    throw new Error(`replicate POST ${res.status}: ${await res.text()}`);
  }
  let pred = await res.json();
  while (pred.status !== 'succeeded' && pred.status !== 'failed' && pred.status !== 'canceled') {
    await new Promise(r => setTimeout(r, 1500));
    const poll = await fetch(pred.urls.get, { headers: { Authorization: `Bearer ${TOKEN}` } });
    if (!poll.ok) throw new Error(`replicate poll ${poll.status}`);
    pred = await poll.json();
  }
  if (pred.status !== 'succeeded') {
    throw new Error(`prediction ${pred.status}: ${pred.error || ''}`);
  }
  const url = Array.isArray(pred.output) ? pred.output[0] : pred.output;
  const img = await fetch(url);
  if (!img.ok) throw new Error(`download ${img.status}`);
  await fs.writeFile(outPath, Buffer.from(await img.arrayBuffer()));
  console.log(`  → ${path.relative(ROOT, outPath)}`);
}

async function main() {
  await fs.mkdir(OG_DIR, { recursive: true });

  const files = (await fs.readdir(POSTS_DIR)).filter(f => f.endsWith('.md'));
  for (const file of files) {
    const slug = file.replace(/\.md$/, '');
    const out = path.join(OG_DIR, `${slug}.png`);
    if (!FORCE && await exists(out)) {
      console.log(`skip ${slug} (exists)`);
      continue;
    }
    const meta = parseFrontmatter(await fs.readFile(path.join(POSTS_DIR, file), 'utf8'));
    if (String(meta.draft).toLowerCase() === 'true') {
      console.log(`skip ${slug} (draft)`);
      continue;
    }
    const title = meta.title || slug;
    const desc = meta.description || '';
    const prompt = `${STYLE}. Mood inspired by: "${title}". ${desc}`.slice(0, 500);
    console.log(`gen ${slug}`);
    await generate(prompt, out);
    await new Promise(r => setTimeout(r, 12000)); // stay under 6/min
  }

  if (FORCE || !(await exists(DEFAULT_OG))) {
    console.log('gen og-default');
    await generate(
      `${STYLE}. Brand hero for "Solo AI Guy" — local-first AI for solo builders. Tech blog cover image, atmospheric.`,
      DEFAULT_OG,
    );
  } else {
    console.log('skip og-default (exists)');
  }
  console.log('done.');
}

main().catch(e => { console.error(e); process.exit(1); });

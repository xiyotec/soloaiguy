# /// script
# dependencies = ["Pillow"]
# ///
"""Generate a minimal brand logo for soloaiguy.com.
Run: uv run scripts/make-logo.py
Output: public/logo.png (512x512, dark navy background, off-white wordmark)
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "public" / "logo.png"

W = H = 512
BG = (15, 23, 42)        # slate-900
FG = (248, 250, 252)     # slate-50
ACCENT = (56, 189, 248)  # sky-400 — the dot on the "i"

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

font_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]
font = None
for p in font_paths:
    if Path(p).exists():
        font = ImageFont.truetype(p, 88)
        break
if font is None:
    font = ImageFont.load_default()

lines = ["Solo AI", "Guy."]
line_h = 110
total_h = line_h * len(lines)
y = (H - total_h) // 2

for i, line in enumerate(lines):
    bbox = draw.textbbox((0, 0), line, font=font)
    text_w = bbox[2] - bbox[0]
    x = (W - text_w) // 2
    draw.text((x, y + i * line_h), line, fill=FG, font=font)

# Accent dot bottom-right of the wordmark for a tiny brand mark
draw.ellipse((W - 110, H - 110, W - 70, H - 70), fill=ACCENT)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}")

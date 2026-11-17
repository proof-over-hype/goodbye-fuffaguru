"""Draw the images in docs/assets from SYNTHETIC data (needs Pillow).

    python scripts/make_assets.py

* social-preview.png (1280x640): name, subtitle, "claimed vs real" chart;
* flow.png: the path follow-trader -> reality-check, with the synthetic example's numbers.
No real trader, channel or market data is used.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fuffaguru.nulltests import random_direction_test  # noqa: E402
from fuffaguru.recipes import LevelRecipe, swing_levels  # noqa: E402
from fuffaguru.synthetic import random_walk_bars  # noqa: E402

OUT = ROOT / "docs" / "assets"
BG, INK, MUTED = (15, 23, 42), (241, 245, 249), (148, 163, 184)
AMBER, GREEN, RED, BLUE = (251, 191, 36), (74, 222, 128), (248, 113, 113), (96, 165, 250)


def font(size: int, bold: bool = False):
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "segoeuib.ttf"] if bold
             else ["arial.ttf", "DejaVuSans.ttf", "Arial.ttf", "segoeui.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def synthetic_curves():
    """Same setup as examples/synthetic_guru (best of 48 variants, then new data)."""
    dev = random_walk_bars(6000, seed=7, start="2024-01-01")
    conf = random_walk_bars(18000, seed=8, start="2024-03-03", start_price=float(dev["close"].iloc[-1]))
    recipe = LevelRecipe(stop_atr=2.0, target_r=3.0, trend_bars=200, cost=0.25)
    r_dev = recipe.run(dev, swing_levels(dev, k=5))
    r_conf = recipe.run(conf, swing_levels(conf, k=5))
    null = random_direction_test(r_dev["net_r"], r_dev["flipped_net_r"], n_sims=4000, seed=0)
    return r_dev["net_r"].to_numpy(), r_conf["net_r"].to_numpy(), null


def polyline(draw, values, box, color, width=4, vmin=None, vmax=None):
    x0, y0, x1, y1 = box
    v = np.asarray(values, dtype=float)
    vmin = v.min() if vmin is None else vmin
    vmax = v.max() if vmax is None else vmax
    xs = np.linspace(x0, x1, len(v))
    ys = y1 - (v - vmin) / (vmax - vmin + 1e-9) * (y1 - y0)
    draw.line(list(zip(xs, ys)), fill=color, width=width, joint="curve")


def social_preview(r_dev, r_conf):
    img = Image.new("RGB", (1280, 640), BG)
    d = ImageDraw.Draw(img)
    d.text((64, 70), "Goodbye", font=font(64, True), fill=INK)
    d.text((64, 140), "FuffaGuru", font=font(84, True), fill=AMBER)
    d.text((64, 250), "Reality-check your", font=font(40), fill=INK)
    d.text((64, 298), "trading guru", font=font(40), fill=INK)
    d.text((64, 380), "fuffa (Italian slang): hot air, smoke", font=font(24), fill=MUTED)
    d.text((64, 412), "and mirrors.", font=font(24), fill=MUTED)
    d.text((64, 540), "open source  ·  Python  ·  works with Claude Code", font=font(24), fill=MUTED)

    box = (700, 230, 1210, 550)
    d.rounded_rectangle((670, 90, 1240, 580), radius=24, outline=(51, 65, 85), width=2)
    d.text((700, 110), "claimed vs real  (synthetic data)", font=font(26, True), fill=INK)
    d.text((700, 155), "shown: best of 48 variants, in sample", font=font(21), fill=GREEN)
    d.text((700, 185), "same frozen rules on new data", font=font(21), fill=RED)
    shown = np.cumsum(r_dev)
    real = shown[-1] + np.cumsum(r_conf[: len(r_dev) * 2])
    allv = np.concatenate([[0.0], shown, real])
    vmin, vmax = allv.min(), allv.max()
    n = len(shown) + len(real)
    split = 700 + (1210 - 700) * len(shown) / n
    polyline(d, np.concatenate([[0.0], shown]), (700, box[1], split, box[3]), GREEN, vmin=vmin, vmax=vmax)
    polyline(d, np.concatenate([[shown[-1]], real]), (split, box[1], 1210, box[3]), RED, vmin=vmin, vmax=vmax)
    d.line([(split, box[1] - 10), (split, box[3] + 10)], fill=MUTED, width=1)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "social-preview.png", optimize=True)


def flow(r_dev, r_conf, null):
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((48, 32), "From a guru's videos to a verdict", font=font(40, True), fill=INK)
    d.text((48, 86), "follow-trader  ->  analyze  ->  reverse-engineer  ->  reality-check   (example on synthetic data)",
           font=font(24), fill=MUTED)
    steps = [("1 Capture", "history + lives\nwith your account"), ("2 Transcribe", "text with times\n+ chart frames"),
             ("3 Extract", "claims, rules\nand trades"), ("4 Verify", "trades replayed\non real prices"),
             ("5 Freeze", "recipe + closing\nrules, sha256"), ("6 Test", "costs, random\ndirection, fake levels")]
    bw, gap, y = 220, 36, 150
    for i, (title, body) in enumerate(steps):
        x = 48 + i * (bw + gap)
        d.rounded_rectangle((x, y, x + bw, y + 150), radius=18, fill=(30, 41, 59), outline=BLUE, width=2)
        d.text((x + 18, y + 16), title, font=font(26, True), fill=AMBER)
        d.multiline_text((x + 18, y + 64), body, font=font(21), fill=INK, spacing=6)
        if i < len(steps) - 1:
            ax = x + bw + 4
            d.line([(ax, y + 75), (ax + gap - 8, y + 75)], fill=MUTED, width=3)
            d.polygon([(ax + gap - 8, y + 68), (ax + gap, y + 75), (ax + gap - 8, y + 82)], fill=MUTED)

    # panel 1: equity curves
    px, py, pw, ph = 48, 360, 700, 440
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=18, outline=(51, 65, 85), width=2)
    d.text((px + 24, py + 18), "What the guru shows vs the frozen rules on new data", font=font(22, True), fill=INK)
    shown = np.cumsum(r_dev)
    real = shown[-1] + np.cumsum(r_conf)
    allv = np.concatenate([[0.0], shown, real])
    box = (px + 30, py + 80, px + pw - 30, py + ph - 70)
    n = len(shown) + len(real)
    split = box[0] + (box[2] - box[0]) * len(shown) / n
    polyline(d, np.concatenate([[0.0], shown]), (box[0], box[1], split, box[3]), GREEN, 3, allv.min(), allv.max())
    polyline(d, np.concatenate([[shown[-1]], real]), (split, box[1], box[2], box[3]), RED, 3, allv.min(), allv.max())
    d.text((px + 30, py + ph - 52), f"in sample: {len(r_dev)} trades, {r_dev.mean():+.2f} R each", font=font(20), fill=GREEN)
    d.text((px + 380, py + ph - 52), f"new data: {len(r_conf)} trades, {r_conf.mean():+.2f} R", font=font(20), fill=RED)

    # panel 2: random direction null
    qx, qw = 780, 380
    d.rounded_rectangle((qx, py, qx + qw, py + ph), radius=18, outline=(51, 65, 85), width=2)
    d.text((qx + 24, py + 18), "Coin-flip direction, same instants", font=font(22, True), fill=INK)
    hist, edges = np.histogram(null.null, bins=30)
    hb = (qx + 30, py + 80, qx + qw - 30, py + ph - 90)
    lo, hi = min(edges[0], null.observed), max(edges[-1], null.observed)
    for h, e0, e1 in zip(hist, edges[:-1], edges[1:]):
        x0 = hb[0] + (e0 - lo) / (hi - lo) * (hb[2] - hb[0])
        x1 = hb[0] + (e1 - lo) / (hi - lo) * (hb[2] - hb[0])
        top = hb[3] - h / hist.max() * (hb[3] - hb[1])
        d.rectangle((x0, top, max(x0 + 1, x1 - 1), hb[3]), fill=BLUE)
    ox = hb[0] + (null.observed - lo) / (hi - lo) * (hb[2] - hb[0])
    d.line([(ox, hb[1]), (ox, hb[3])], fill=AMBER, width=4)
    d.multiline_text((qx + 30, py + ph - 80), "In sample it even beats the coin...\nbecause it was chosen on that data.",
                     font=font(19), fill=MUTED, spacing=4)

    # panel 3: verdict
    vx, vw = 1190, 362
    d.rounded_rectangle((vx, py, vx + vw, py + ph), radius=18, fill=(69, 10, 10), outline=RED, width=3)
    d.text((vx + 24, py + 24), "Reality Check", font=font(28, True), fill=INK)
    d.multiline_text((vx + 24, py + 80), "NO EVIDENCE\nOF EDGE", font=font(40, True), fill=RED, spacing=6)
    d.multiline_text((vx + 24, py + 210),
                     "- best of 48 variants\n- fake levels do as well\n- new data: about zero\n- 'winning days' are\n  not winning trades",
                     font=font(21), fill=INK, spacing=8)
    d.text((48, H - 52), "Synthetic random-walk market: no rule can have an edge here by construction.",
           font=font(20), fill=MUTED)
    img.save(OUT / "flow.png", optimize=True)


def main() -> None:
    r_dev, r_conf, null = synthetic_curves()
    social_preview(r_dev, r_conf)
    flow(r_dev, r_conf, null)
    print("written:", ", ".join(p.name for p in sorted(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()

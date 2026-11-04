import os
import math
import time
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_IMAGE = os.path.join(ROOT_DIR, "assets", "ascii_source.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")

# Load source portrait
src = Image.open(SOURCE_IMAGE).convert("L")
W, H = src.size

# Font discovery (Windows & Ubuntu GitHub Actions runners)
font_candidates = [
    "C:/Windows/Fonts/consolab.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]
FONT = None
for fp in font_candidates:
    if os.path.exists(fp):
        try:
            FONT = ImageFont.truetype(fp, 15)
            break
        except Exception:
            pass
if not FONT:
    FONT = ImageFont.load_default()

# Precompute morphological envelopes & masks
med9 = src.filter(ImageFilter.MedianFilter(9))
max7 = src.filter(ImageFilter.MaxFilter(7))
max13 = src.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(2.8))

# 1. Head ASCII Mask (Helmet crown, Forehead, Cheek/Nose ASCII zones)
head_mask = Image.new("L", (W, H), 0)
hdraw = ImageDraw.Draw(head_mask)
hdraw.ellipse([170, 26, 360, 82], fill=255)  # Helmet top '. @@##%=##@'
hdraw.polygon([(192, 124), (392, 124), (402, 195), (178, 195)], fill=255)  # Forehead
hdraw.rectangle([182, 238, 398, 286], fill=245)  # Cheeks/nose 'MMMW $@@M'
# Cut out glasses frames & eye lenses so they remain 100% razor-sharp
hdraw.ellipse([180, 196, 290, 260], fill=0)
hdraw.ellipse([306, 196, 412, 260], fill=0)
head_mask = head_mask.filter(ImageFilter.GaussianBlur(2.5))
head_active = ImageChops.multiply(
    head_mask,
    max13.point(lambda p: 255 if p > 36 else (int(p * 6.8) if p > 5 else 0)),
)

# 2. Body ASCII Mask (y > 350): broad bright highlight patches (shoulders, gun stock, sleeves, vest)
body_bright = med9.point(lambda p: min(255, int((p - 78) * 3.4)) if p > 78 else 0)

# Include gun stock 'MMMM' strip (x=50..165, y=560..715) & lower hand/forearm ASCII zones
stock_mask = Image.new("L", (W, H), 0)
sdraw = ImageDraw.Draw(stock_mask)
sdraw.polygon([(50, 560), (130, 560), (168, 715), (90, 715)], fill=255)
sdraw.rectangle([0, 755, 165, 875], fill=230)      # Left forearm 'MMM@M $$$'
sdraw.rectangle([250, 795, 335, 860], fill=230)    # Center scope mount 'MMM $MM'
sdraw.rectangle([475, 485, 597, 610], fill=240)    # Right shoulder 'M@MMMM'
sdraw.rectangle([395, 900 - 95, 585, 875], fill=235)  # Bottom right arm 'MMW'
stock_active = ImageChops.multiply(
    stock_mask.filter(ImageFilter.GaussianBlur(3.0)),
    max7.point(lambda p: 255 if p > 70 else 0),
)
body_bright = ImageChops.lighter(body_bright, stock_active)

# Protect non-ASCII structural icons & patches
bdraw = ImageDraw.Draw(body_bright)
bdraw.rectangle([0, 0, W, 350], fill=0)
bdraw.rounded_rectangle([206, 510, 350, 614], radius=8, fill=0)  # Sri Lanka flag patch 100% untouched
bdraw.polygon([(516, 490), (597, 440), (597, 620), (516, 590)], fill=0)  # Right shoulder woven patch untouched
bdraw.ellipse([222, 815, 302, 875], fill=0)  # Optical scope lenses untouched

body_contour = src.filter(ImageFilter.MaxFilter(3)).point(
    lambda p: 255 if p > 52 else (int(p * 4.5) if p > 12 else 0)
)
body_active = ImageChops.multiply(
    body_bright.filter(ImageFilter.GaussianBlur(1.8)), body_contour
)

total_ascii_mask = ImageChops.lighter(head_active, body_active)

# Precompute smooth backing for active ASCII zones
backing = Image.new("L", (W, H), 0)
med_px = med9.load()
b_px = backing.load()
for y in range(H):
    f = 0.18 if y < 320 else 0.50
    for x in range(W):
        b_px[x, y] = int(med_px[x, y] * f)

# Character grid aligned to the exact 18px vertical pitch of the portrait's ASCII rows
CELL_W, CELL_H = 9, 18
Y0 = 10  # Aligns rows to y = 28, 46, 64, ..., 136, 154, 172, 190, ..., 244, 262
cols = W // CELL_W
rows = (H - Y0) // CELL_H

max_px = max13.load()
src_px = src.load()

ROW_PATTERNS = [
    ".@@@#=, , , ,@@@%MMMMMM",
    "@@@%MMMMMMMMMMWW@#MMMMM",
    "@#MMMMMMMMMMMMMWWW$@@MM",
    "@@##%=##@..@@##%=##@MMW",
    "MMMW$@@MMW==M@MW$$$MMMM",
    "MMMMM@MMMM$$$MMMW@@##%M",
    "$$$MMW@@##%MMMMW@#MMMMM",
]


def render_frame(frame_idx, total_frames):
    t = (frame_idx / float(total_frames)) * 3.0  # 3.0s seamless cycle
    txt_layer = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(txt_layer)

    # Dual vertical scan waves sweeping seamlessly down the portrait
    scan_r1 = int(((frame_idx * 2.0) % rows))
    scan_r2 = int(((frame_idx * 2.0 + rows // 2) % rows))

    for r in range(rows):
        y = Y0 + r * CELL_H
        pat = ROW_PATTERNS[(r + frame_idx // 2) % len(ROW_PATTERNS)]
        # Continuous horizontal typing / key-working stream
        shift = frame_idx + (r * 5) % 13
        type_c = (frame_idx * 3 + r * 7) % cols

        dist_scan = min(abs(r - scan_r1), abs(r - scan_r2))
        on_scan = dist_scan <= 1

        for c in range(cols):
            x = c * CELL_W
            cx = min(W - 1, x + 4)
            cy = min(H - 1, y + 8)
            v = max_px[cx, cy]
            if v < 35:
                continue

            # Staggered real-time key cycling per cell
            tick = (frame_idx + (c * 3 + r * 7)) // 2
            if v > 165:
                ch = pat[(c + shift + tick) % len(pat)]
                if ch in " ,.":
                    ch = "MW@#$%"[(c + tick) % 6]
                br = 250
            elif v > 105:
                ch = "@#$%MW="[(c + shift + tick) % 7]
                br = 235
            else:
                ch = "#%=+:."[(c + shift + tick) % 6]
                br = 195

            if on_scan:
                br = 255
                ch = "$@#MW"[(c + frame_idx) % 5]
            elif abs(c - type_c) <= 1:
                br = 255
                ch = "$" if v > 140 else "@"

            draw.text((x, y), ch, fill=br, font=FONT)

    ascii_patch = ImageChops.lighter(backing, txt_layer)
    out = Image.composite(ascii_patch, src, total_ascii_mask)

    # Animate neck & chin matrix grid dots twinkling in real time
    out_draw = ImageDraw.Draw(out)
    phase = (frame_idx / float(total_frames)) * math.pi * 2.0
    for nr in range(365, 495, 14):
        for nc in range(230, 355, 11):
            if src_px[nc, nr] > 35:
                pulse = math.sin(phase * 2.0 + nc * 0.25 + nr * 0.18)
                dot_br = int(105 + 150 * max(0.0, pulse))
                ch_d = ":" if pulse > 0.35 else "."
                out_draw.text((nc - 3, nr - 6), ch_d, fill=dot_br, font=FONT)

    return out


def main():
    TOTAL_FRAMES = 30
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} frames of real-time ASCII portrait animation ({W}x{H})...")
    t0 = time.time()

    # Build a clean 64-shade grayscale palette for fast, zero-dither razor-sharp GIF output
    frames = []
    for i in range(TOTAL_FRAMES):
        f_l = render_frame(i, TOTAL_FRAMES)
        f_rgb = f_l.convert("RGB")
        q_img = f_rgb.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        frames.append(q_img)
        if (i + 1) % 10 == 0 or i == TOTAL_FRAMES - 1:
            print(f"  Rendered {i + 1}/{TOTAL_FRAMES} frames...")

    frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )
    gif_kb = os.path.getsize(OUT_GIF) / 1024.0
    print(f"Saved {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

    # Synchronize ascii_portrait.svg wrapper
    with open(OUT_GIF, "rb") as f:
        b64_gif = base64.b64encode(f.read()).decode("ascii")

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Animated ASCII Portrait">
  <image width="{W}" height="{H}" href="data:image/gif;base64,{b64_gif}"/>
</svg>'''

    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Saved synchronized {OUT_SVG}")


if __name__ == "__main__":
    main()


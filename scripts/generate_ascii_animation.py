import os
import math
import time
import base64
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")
OUT_ABOUT_SVG = os.path.join(ROOT_DIR, "about_me.svg")

# Card dimensions (matches full README width like skyline.gif)
CARD_W, CARD_H = 840, 325
SCALE = 2
CW_2X, CH_2X = CARD_W * SCALE, CARD_H * SCALE

# Portrait size inside the right side of the unified box
PW, PH = 276, 305

# Load real photo and apply tight bust crop so the subject & center Sri Lanka flag fill the portrait bay
real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((16, 126, 548, 716)).resize((PW, PH), Image.Resampling.LANCZOS)
px_raw = crop_rgb.load()


def load_font(candidates, size):
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


MONO_BOLD_PATHS = [
    "C:/Windows/Fonts/consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]
MONO_REG_PATHS = [
    "C:/Windows/Fonts/consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]
SANS_BOLD_PATHS = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
SANS_REG_PATHS = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

FONT_ASCII = load_font(MONO_BOLD_PATHS, 9)
FONT_TITLE_2X = load_font(SANS_BOLD_PATHS, 16 * SCALE)
FONT_PATH_2X = load_font(MONO_REG_PATHS, 12 * SCALE)
FONT_LABEL_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)
FONT_VALUE_2X = load_font(SANS_REG_PATHS, 15 * SCALE)
FONT_VALUE_BOLD_2X = load_font(SANS_BOLD_PATHS, 15 * SCALE)
FONT_PILL_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)
FONT_LIVE_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)

# 1. Connected flood-fill background removal on portrait (100% transparent background, zero interior holes)
visited = [[False] * PW for _ in range(PH)]
q = deque()
for x in range(PW):
    q.append((x, 0))
    visited[0][x] = True
for y in range(PH - 50):
    q.append((0, y))
    q.append((PW - 1, y))
    visited[y][0] = True
    visited[y][PW - 1] = True

while q:
    cx, cy = q.popleft()
    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
        if 0 <= nx < PW and 0 <= ny < PH and not visited[ny][nx]:
            r, g, b = px_raw[nx, ny]
            if max(r, g, b) < 24:
                visited[ny][nx] = True
                q.append((nx, ny))

for sy in range(95, 175):
    for sx in range(65, 225):
        r, g, b = px_raw[sx, sy]
        if max(r, g, b) < 10 and not visited[sy][sx] and (sx < 102 or sx > 184):
            q.append((sx, sy))
            visited[sy][sx] = True
            while q:
                cx, cy = q.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < PW and 0 <= ny < PH and not visited[ny][nx]:
                        rr, gg, bb = px_raw[nx, ny]
                        if max(rr, gg, bb) < 20 and (nx < 108 or nx > 178):
                            visited[ny][nx] = True
                            q.append((nx, ny))

alpha = Image.new("L", (PW, PH), 255)
a_px = alpha.load()
for y in range(PH):
    for x in range(PW):
        if visited[y][x]:
            a_px[x, y] = 0
alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
a_px = alpha.load()

# 2. High-Contrast Cinematic Black & White Portrait
cine_l = crop_rgb.convert("L")
cine_l = cine_l.filter(ImageFilter.UnsharpMask(radius=8, percent=135, threshold=2))
cine_l = cine_l.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=1))
cine_l = ImageEnhance.Contrast(cine_l).enhance(1.24)

# Enhance center Sri Lanka flag patch contrast in (PW=276, PH=305) coordinates:
# Flag box is x: 101..159, y: 223..263
l_px = cine_l.load()
for fy in range(223, 263):
    for fx in range(101, 159):
        r_v, g_v, b_v = px_raw[fx, fy]
        if r_v > 140 and g_v > 95:
            l_px[fx, fy] = min(255, int(l_px[fx, fy] * 1.25 + 35))
        elif r_v > 75 and g_v < 55:
            l_px[fx, fy] = max(28, int(l_px[fx, fy] * 0.65))

CELL_W, CELL_H = 5, 8
p_cols = PW // CELL_W
p_rows = PH // CELL_H
RAMP = " .,-:;+=*#%$&@MW"


def render_portrait_rgba(frame_idx):
    glyph_mask = Image.new("L", (PW, PH), 0)
    draw_g = ImageDraw.Draw(glyph_mask)

    sweep_r = (frame_idx * 1.6) % p_rows
    flag_wave_c = 101 + int((frame_idx * 3) % 62)

    for r in range(p_rows):
        y = r * CELL_H
        type_c = (frame_idx * 3 + r * 7) % p_cols
        dist_sweep = min(abs(r - sweep_r), abs(r - (sweep_r - p_rows)), abs(r - (sweep_r + p_rows)))
        sweep_boost = max(0.0, 1.0 - dist_sweep / 3.5)

        for c in range(p_cols):
            x = c * CELL_W
            cx = min(PW - 1, x + CELL_W // 2)
            cy = min(PH - 1, y + CELL_H // 2)
            if a_px[cx, cy] < 95:
                continue
            lum = l_px[cx, cy]
            in_flag = 101 <= cx <= 159 and 223 <= cy <= 263
            if lum < 12 and not in_flag:
                continue

            base_idx = int((lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 9 + frame_idx) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            if in_flag:
                if lum > 110:
                    ch = "MW@#$%*"[(c + r + frame_idx) % 7]
                    val = 245 if abs(cx - flag_wave_c) > 6 else 255
                else:
                    ch = ".:;+=#"[(c + r + frame_idx) % 6]
                    val = min(195, int(lum * 1.35 + 35))
            else:
                val = min(245, int(lum * 1.25 + 50))

            if sweep_boost > 0.15 and lum > 22:
                val = min(255, int(val + 75 * sweep_boost))
                if sweep_boost > 0.55:
                    ch = "MW@#$%"[(c + frame_idx) % 6]
            elif abs(c - type_c) <= 1 and (r % 2 == 0) and lum > 32:
                val = 255
                ch = "$" if lum > 110 else "@"

            draw_g.text((x, y - 1), ch, fill=val, font=FONT_ASCII)

    g_px = glyph_mask.load()
    out_rgba = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    o_px = out_rgba.load()

    for y in range(PH):
        for x in range(PW):
            al = a_px[x, y]
            if al < 60:
                continue
            lum = l_px[x, y]
            gv = g_px[x, y]
            in_flag = 101 <= x <= 159 and 223 <= y <= 263
            in_eyes_smile = (95 <= x <= 185 and 65 <= y <= 98) or (112 <= x <= 168 and 104 <= y <= 132)

            if gv > 25:
                t_g = gv / 255.0
                boost = 0.45 if in_eyes_smile else (0.85 if in_flag else 0.72)
                bw = min(255, int(lum * (1.0 + t_g * boost * 0.45) + t_g * boost * 78))
            else:
                recess = 0.78 if in_eyes_smile else (0.48 if in_flag else 0.54)
                bw = int(lum * recess)

            o_px[x, y] = (bw, bw, bw, al)

    return out_rgba


def build_base_card_2x():
    """Renders the unified 840x325 glassmorphic terminal box at 2x supersampling."""
    img = Image.new("RGB", (CW_2X, CH_2X), (13, 17, 23))
    draw = ImageDraw.Draw(img)

    # Outer card frame (x=2..838, y=2..323)
    draw.rounded_rectangle(
        [2 * SCALE, 2 * SCALE, (CARD_W - 3) * SCALE, (CARD_H - 3) * SCALE],
        radius=14 * SCALE,
        fill=(18, 23, 30),
        outline=(0, 185, 220),
        width=int(1.5 * SCALE),
    )

    # Top header bar (y=3..46)
    draw.rounded_rectangle(
        [3 * SCALE, 3 * SCALE, (CARD_W - 4) * SCALE, 46 * SCALE],
        radius=13 * SCALE,
        fill=(22, 27, 34),
    )
    draw.rectangle([3 * SCALE, 32 * SCALE, (CARD_W - 4) * SCALE, 46 * SCALE], fill=(22, 27, 34))
    draw.line([(3 * SCALE, 46 * SCALE), ((CARD_W - 4) * SCALE, 46 * SCALE)], fill=(48, 54, 61), width=SCALE)

    # macOS Window Control Dots
    for cx, col in [(22, (255, 95, 86)), (40, (255, 189, 46)), (58, (39, 201, 63))]:
        r = int(5.5 * SCALE)
        draw.ellipse([cx * SCALE - r, 25 * SCALE - r, cx * SCALE + r, 25 * SCALE + r], fill=col)

    # Header Title & Path
    draw.text((80 * SCALE, 15 * SCALE), "ABOUT ME", fill=(240, 246, 252), font=FONT_TITLE_2X)
    draw.text((178 * SCALE, 17 * SCALE), "~/gayathra45/about.sh", fill=(139, 148, 158), font=FONT_PATH_2X)

    # Right Header LIVE pill container (shifted to x=465 so right side has room, or top-right x=768)
    draw.rounded_rectangle(
        [768 * SCALE, 14 * SCALE, 822 * SCALE, 36 * SCALE],
        radius=11 * SCALE,
        fill=(13, 17, 23),
        outline=(35, 134, 54),
        width=SCALE,
    )
    draw.text((792 * SCALE, 19 * SCALE), "LIVE", fill=(57, 211, 83), font=FONT_LIVE_2X)

    # Helper to draw each of the 4 modern left-side rows (width = 512px, x = 16..528)
    rows_spec = [
        {
            "y": 58,
            "accent": (0, 217, 255),
            "icon": "code",
            "label": "CURRENTLY LEARNING",
            "prefix": "I'm currently learning ",
            "highlight": "MERN Stack",
            "pill": None,
        },
        {
            "y": 122,
            "accent": (57, 211, 83),
            "icon": "cap",
            "label": "EDUCATION & UNIVERSITY",
            "prefix": "I'm an ",
            "highlight": "Undergraduate at KDU",
            "pill": "BSc IT · LK",
        },
        {
            "y": 186,
            "accent": (88, 166, 255),
            "icon": "mail",
            "label": "HOW TO REACH ME",
            "prefix": "gayathrasamuditha45@gmail.com",
            "highlight": "",
            "pill": "Direct Mail",
        },
        {
            "y": 250,
            "accent": (255, 123, 114),
            "icon": "bolt",
            "label": "FUN FACT & ALIAS",
            "prefix": "Call me as ",
            "highlight": "Gayya",
            "pill": "@gayathra45",
        },
    ]

    for row in rows_spec:
        rx, ry = 16 * SCALE, row["y"] * SCALE
        rw, rh = 512 * SCALE, 56 * SCALE
        acc = row["accent"]

        # Row card background
        draw.rounded_rectangle(
            [rx, ry, rx + rw, ry + rh],
            radius=10 * SCALE,
            fill=(24, 29, 36),
            outline=(33, 38, 45),
            width=SCALE,
        )
        # Left glowing accent bar
        draw.rounded_rectangle(
            [rx, ry + 9 * SCALE, rx + int(3.5 * SCALE), ry + 47 * SCALE],
            radius=2 * SCALE,
            fill=acc,
        )
        # Icon box
        ibx, iby = rx + 14 * SCALE, ry + 10 * SCALE
        ibs = 36 * SCALE
        draw.rounded_rectangle(
            [ibx, iby, ibx + ibs, iby + ibs],
            radius=8 * SCALE,
            fill=(13, 17, 23),
            outline=(acc[0] // 2, acc[1] // 2, acc[2] // 2),
            width=SCALE,
        )

        # Draw crisp vector icon inside icon box
        icx, icy = ibx + 18 * SCALE, iby + 18 * SCALE
        w_stroke = int(2 * SCALE)
        if row["icon"] == "code":
            draw.line([(icx - 5 * SCALE, icy - 5 * SCALE), (icx - 10 * SCALE, icy), (icx - 5 * SCALE, icy + 5 * SCALE)], fill=acc, width=w_stroke)
            draw.line([(icx + 5 * SCALE, icy - 5 * SCALE), (icx + 10 * SCALE, icy), (icx + 5 * SCALE, icy + 5 * SCALE)], fill=acc, width=w_stroke)
            draw.line([(icx + 2 * SCALE, icy - 7 * SCALE), (icx - 2 * SCALE, icy + 7 * SCALE)], fill=acc, width=w_stroke)
        elif row["icon"] == "cap":
            pts = [(icx, icy - 8 * SCALE), (icx - 11 * SCALE, icy - 2 * SCALE), (icx, icy + 3 * SCALE), (icx + 11 * SCALE, icy - 2 * SCALE)]
            draw.polygon(pts, outline=acc, width=w_stroke)
            draw.line([(icx - 7 * SCALE, icy + 1 * SCALE), (icx - 7 * SCALE, icy + 7 * SCALE), (icx + 7 * SCALE, icy + 7 * SCALE), (icx + 7 * SCALE, icy + 1 * SCALE)], fill=acc, width=w_stroke)
        elif row["icon"] == "mail":
            draw.rounded_rectangle([icx - 10 * SCALE, icy - 7 * SCALE, icx + 10 * SCALE, icy + 7 * SCALE], radius=2 * SCALE, outline=acc, width=w_stroke)
            draw.line([(icx - 9 * SCALE, icy - 5 * SCALE), (icx, icy + 1 * SCALE), (icx + 9 * SCALE, icy - 5 * SCALE)], fill=acc, width=w_stroke)
        elif row["icon"] == "bolt":
            pts = [(icx + 2 * SCALE, icy - 9 * SCALE), (icx - 7 * SCALE, icy + 1 * SCALE), (icx - 1 * SCALE, icy + 1 * SCALE), (icx - 3 * SCALE, icy + 9 * SCALE), (icx + 7 * SCALE, icy - 1 * SCALE), (icx + 1 * SCALE, icy - 1 * SCALE)]
            draw.polygon(pts, outline=acc, width=w_stroke)

        # Label text
        draw.text((rx + 62 * SCALE, ry + 10 * SCALE), row["label"], fill=acc, font=FONT_LABEL_2X)

        # Value text + colored highlight
        vx, vy = rx + 62 * SCALE, ry + 26 * SCALE
        draw.text((vx, vy), row["prefix"], fill=(230, 237, 243), font=FONT_VALUE_2X)
        if row["highlight"]:
            bbox = draw.textbbox((0, 0), row["prefix"], font=FONT_VALUE_2X)
            pw_txt = bbox[2] - bbox[0]
            draw.text((vx + pw_txt, vy), row["highlight"], fill=acc, font=FONT_VALUE_BOLD_2X)

        # Right pill badge
        if row["pill"]:
            px1, py1 = rx + 412 * SCALE, ry + 17 * SCALE
            px2, py2 = rx + 496 * SCALE, ry + 39 * SCALE
            draw.rounded_rectangle(
                [px1, py1, px2, py2],
                radius=6 * SCALE,
                fill=(13, 17, 23),
                outline=(acc[0] // 2, acc[1] // 2, acc[2] // 2),
                width=SCALE,
            )
            p_bbox = draw.textbbox((0, 0), row["pill"], font=FONT_PILL_2X)
            pt_w = p_bbox[2] - p_bbox[0]
            pt_h = p_bbox[3] - p_bbox[1]
            draw.text(
                (px1 + (84 * SCALE - pt_w) // 2, py1 + (22 * SCALE - pt_h) // 2 - 1 * SCALE),
                row["pill"],
                fill=acc,
                font=FONT_PILL_2X,
            )

    return img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


BASE_CARD = build_base_card_2x()


def render_combined_frame(frame_idx, total_frames):
    frame = BASE_CARD.copy()
    draw = ImageDraw.Draw(frame)

    # 1. Animated blinking cyan cursor in header
    if (frame_idx // 6) % 2 == 0:
        draw.rectangle([332, 18, 339, 31], fill=(0, 217, 255))

    # 2. Animated pulsing LIVE green dot & ring
    pulse = (math.sin((frame_idx / float(total_frames)) * math.pi * 4.0) + 1.0) * 0.5
    r_ring = int(3 + pulse * 5)
    ring_col = (int(13 + 44 * (1 - pulse)), int(17 + 194 * (1 - pulse)), int(23 + 60 * (1 - pulse)))
    draw.ellipse([782 - r_ring, 25 - r_ring, 782 + r_ring, 25 + r_ring], outline=ring_col, width=1)
    draw.ellipse([782 - 3, 25 - 3, 782 + 3, 25 + 3], fill=(57, 211, 83))

    # 3. Animated header scanline bar
    scan_w = int(160 + 120 * math.sin((frame_idx / float(total_frames)) * math.pi * 2.0))
    draw.line([(16, 46), (16 + scan_w, 46)], fill=(0, 217, 255), width=2)

    # 4. Composite transparent-BG B&W ASCII Portrait on the right side inside the card!
    portrait_rgba = render_portrait_rgba(frame_idx)
    # Place flush inside right side of card (x=548, y=17 -> bottom aligns cleanly at y=322)
    frame.paste(portrait_rgba, (548, 17), portrait_rgba)

    return frame


def main():
    TOTAL_FRAMES = 24
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} unified About Me + B&W ASCII Portrait frames ({CARD_W}x{CARD_H})...")
    t0 = time.time()

    # Build master palette from Frame 0 so all 24 frames have zero color flicker
    f0 = render_combined_frame(0, TOTAL_FRAMES)
    master_pal = f0.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    frames = []
    for i in range(TOTAL_FRAMES):
        f_rgb = render_combined_frame(i, TOTAL_FRAMES)
        q_img = f_rgb.quantize(palette=master_pal, dither=Image.Dither.NONE)
        frames.append(q_img)
        if (i + 1) % 6 == 0 or i == TOTAL_FRAMES - 1:
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
    print(f"Saved unified {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

    # Synchronize ascii_portrait.svg and about_me.svg
    with open(OUT_GIF, "rb") as f:
        b64_gif = base64.b64encode(f.read()).decode("ascii")

    synced_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {CARD_W} {CARD_H}" width="100%" height="100%" role="img" aria-label="About Me - Gayathra Samuditha">
  <image width="{CARD_W}" height="{CARD_H}" href="data:image/gif;base64,{b64_gif}"/>
</svg>'''

    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(synced_svg)
    with open(OUT_ABOUT_SVG, "w", encoding="utf-8") as f:
        f.write(synced_svg)
    print("Synchronized ascii_portrait.svg and about_me.svg!")


if __name__ == "__main__":
    main()

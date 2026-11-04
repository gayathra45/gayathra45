import os
import math
import time
import base64
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")
OUT_ABOUT_SVG = os.path.join(ROOT_DIR, "about_me.svg")

# Unified Card dimensions
CARD_W, CARD_H = 840, 345
SCALE = 2
CW_2X, CH_2X = CARD_W * SCALE, CARD_H * SCALE

# Taller Portrait dimensions (reaching up next to the LIVE pill and showing the chest area below the flag patch)
PW, PH = 304, 326

real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((18, 125, 558, 690)).resize((PW, PH), Image.Resampling.LANCZOS)
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
FONT_LABEL_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)
FONT_VALUE_2X = load_font(SANS_REG_PATHS, 15 * SCALE)
FONT_VALUE_BOLD_2X = load_font(SANS_BOLD_PATHS, 15 * SCALE)
FONT_PILL_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)
FONT_LIVE_2X = load_font(MONO_BOLD_PATHS, 10 * SCALE)

# 1. Connected flood-fill background removal on portrait (100% transparent background)
visited = [[False] * PW for _ in range(PH)]
q = deque()
for x in range(PW):
    q.append((x, 0))
    visited[0][x] = True
for y in range(PH - 45):
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

for sy in range(85, 165):
    for sx in range(60, 220):
        r, g, b = px_raw[sx, sy]
        if max(r, g, b) < 10 and not visited[sy][sx] and (sx < 98 or sx > 178):
            q.append((sx, sy))
            visited[sy][sx] = True
            while q:
                cx, cy = q.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < PW and 0 <= ny < PH and not visited[ny][nx]:
                        rr, gg, bb = px_raw[nx, ny]
                        if max(rr, gg, bb) < 20 and (nx < 104 or nx > 172):
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

l_px = cine_l.load()
for fy in range(245, 288):
    for fx in range(106, 169):
        r_v, g_v, b_v = px_raw[fx, fy]
        if r_v > 140 and g_v > 95:
            l_px[fx, fy] = min(255, int(l_px[fx, fy] * 1.25 + 35))
        elif r_v > 75 and g_v < 55:
            l_px[fx, fy] = max(28, int(l_px[fx, fy] * 0.65))

CELL_W, CELL_H = 5, 8
p_cols = PW // CELL_W
p_rows = PH // CELL_H
RAMP = " .,-:;+=*#%$&@MW"

INNER_CLIP = Image.new("L", (CARD_W, CARD_H), 0)
ic_draw = ImageDraw.Draw(INNER_CLIP)
ic_draw.rounded_rectangle([3, 47, CARD_W - 4, CARD_H - 4], radius=13, fill=255)

# Mask of the 4 glass boxes + header bar for the Near-Black Dark Blur Glass effect (ZERO blue bg!)
GLASS_MASK = Image.new("L", (CARD_W, CARD_H), 0)
gm_draw = ImageDraw.Draw(GLASS_MASK)
gm_draw.rounded_rectangle([3, 3, CARD_W - 4, 46], radius=13, fill=255)
gm_draw.rectangle([3, 32, CARD_W - 4, 46], fill=255)
for ry_box in [60, 129, 198, 267]:
    gm_draw.rounded_rectangle([16, ry_box, 16 + 512, ry_box + 58], radius=10, fill=255)

# Mask of the 4 CONTENT BOXES outlines + header divider + 1px OUTER BOX outline for Frosted Glass Rim Refraction
GLASS_RIM_MASK = Image.new("L", (CW_2X, CH_2X), 0)
rm_draw = ImageDraw.Draw(GLASS_RIM_MASK)
# 1px Outer Box Rim (highlighted clearly)
rm_draw.rounded_rectangle(
    [2 * SCALE, 2 * SCALE, (CARD_W - 3) * SCALE, (CARD_H - 3) * SCALE],
    radius=14 * SCALE,
    fill=None,
    outline=255,
    width=int(1.4 * SCALE),
)
# Header divider & top glass specular line
rm_draw.line([(3 * SCALE, 46 * SCALE), ((CARD_W - 4) * SCALE, 46 * SCALE)], fill=200, width=SCALE)
rm_draw.line([(16 * SCALE, 4 * SCALE), ((CARD_W - 16) * SCALE, 4 * SCALE)], fill=235, width=SCALE)
# 4 Inner Content Boxes Glass-Effect Outlines + Top Specular Bevel
for ry_box in [60, 129, 198, 267]:
    rx, ry = 16 * SCALE, ry_box * SCALE
    rw, rh = 512 * SCALE, 58 * SCALE
    rm_draw.rounded_rectangle(
        [rx, ry, rx + rw, ry + rh],
        radius=10 * SCALE,
        fill=None,
        outline=230,
        width=int(1.2 * SCALE),
    )
    rm_draw.line(
        [(rx + 10 * SCALE, ry + 1 * SCALE), (rx + rw - 10 * SCALE, ry + 1 * SCALE)],
        fill=245,
        width=SCALE,
    )
GLASS_RIM_MASK_1X = GLASS_RIM_MASK.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


def render_portrait_rgba(frame_idx, total_frames):
    glyph_mask = Image.new("L", (PW, PH), 0)
    draw_g = ImageDraw.Draw(glyph_mask)

    t = frame_idx / float(total_frames)
    sweep_r = t * p_rows
    slow_step = frame_idx // 3
    flag_wave_c = 106 + int(t * 64)

    for r in range(p_rows):
        y = r * CELL_H
        type_c = int((t * p_cols + r * 7) % p_cols)
        dist_sweep = min(abs(r - sweep_r), abs(r - (sweep_r - p_rows)), abs(r - (sweep_r + p_rows)))
        sweep_boost = max(0.0, 1.0 - dist_sweep / 4.0)

        for c in range(p_cols):
            x = c * CELL_W
            cx = min(PW - 1, x + CELL_W // 2)
            cy = min(PH - 1, y + CELL_H // 2)
            if a_px[cx, cy] < 95:
                continue
            lum = l_px[cx, cy]
            in_flag = 106 <= cx <= 169 and 245 <= cy <= 288
            if lum < 12 and not in_flag:
                continue

            base_idx = int((lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 9 + slow_step) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            if in_flag:
                if lum > 110:
                    ch = "MW@#$%*"[(c + r + slow_step) % 7]
                    val = 245 if abs(cx - flag_wave_c) > 6 else 255
                else:
                    ch = ".:;+=#"[(c + r + slow_step) % 6]
                    val = min(195, int(lum * 1.35 + 35))
            else:
                val = min(245, int(lum * 1.25 + 50))

            if sweep_boost > 0.15 and lum > 22:
                val = min(255, int(val + 65 * sweep_boost))
                if sweep_boost > 0.55:
                    ch = "MW@#$%"[(c + slow_step) % 6]
            elif abs(c - type_c) <= 1 and (r % 3 == 0) and lum > 32:
                val = 250
                ch = "$" if lum > 110 else "@"

            draw_g.text((x, y - 1), ch, fill=val, font=FONT_ASCII)

    g_px = glyph_mask.load()
    out_rgba = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    o_px = out_rgba.load()

    for y in range(PH):
        for x in range(PW):
            al = a_px[x, y]
            if al < 90:
                continue
            lum = l_px[x, y]
            gv = g_px[x, y]
            in_flag = 106 <= x <= 169 and 245 <= y <= 288
            in_eyes_smile = (98 <= x <= 198 and 66 <= y <= 106) or (116 <= x <= 180 and 110 <= y <= 144)

            if gv > 25:
                t_g = gv / 255.0
                boost = 0.45 if in_eyes_smile else (0.85 if in_flag else 0.72)
                bw = min(255, int(lum * (1.0 + t_g * boost * 0.45) + t_g * boost * 78))
            else:
                recess = 0.78 if in_eyes_smile else (0.48 if in_flag else 0.54)
                bw = int(lum * recess)

            o_px[x, y] = (bw, bw, bw, 255)

    return out_rgba


# Exact vibrant colors for text, icons, pills, and the small vertical line on each box (matching user's reference image!)
ROWS_SPEC = [
    {
        "y": 60,
        "accent": (0, 217, 255),      # Electric Cyan-Blue (#00D9FF)
        "icon": "code",
        "label": "CURRENTLY LEARNING",
        "prefix": "I'm currently learning ",
        "highlight": "MERN Stack",
        "pill": None,
    },
    {
        "y": 129,
        "accent": (57, 211, 83),      # Vibrant Emerald Green (#39D353)
        "icon": "cap",
        "label": "EDUCATION & UNIVERSITY",
        "prefix": "I'm an ",
        "highlight": "Undergraduate at KDU",
        "pill": "BSc IT · LK",
    },
    {
        "y": 198,
        "accent": (14, 194, 232),     # Bright Cyan-Blue (#0EC2E8, matching reference image Row 3!)
        "icon": "mail",
        "label": "HOW TO REACH ME",
        "prefix": "gayathrasamuditha45@gmail.com",
        "highlight": "",
        "pill": "Direct Mail",
    },
    {
        "y": 267,
        "accent": (235, 114, 106),    # Warm Coral-Red (#EB726A, matching reference image Row 4!)
        "icon": "bolt",
        "label": "FUN FACT & ALIAS",
        "prefix": "Call me as ",
        "highlight": "Gayya",
        "pill": "@gayathra45",
    },
]


def build_ui_foreground_2x():
    """
    Renders crisp icons, text, pills, and glowing left small lines in vibrant Blue/Cyan, Green, and Red,
    while keeping all box backgrounds and glass outlines pure neutral near-black smoked glass (NO blue bg!).
    """
    img = Image.new("RGBA", (CW_2X, CH_2X), (0, 0, 0, 0))

    # 1. Soft neon glow layer specifically for the small vertical line on the left of each box
    glow_layer = Image.new("RGBA", (CW_2X, CH_2X), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for row in ROWS_SPEC:
        rx, ry = 16 * SCALE, row["y"] * SCALE
        acc = row["accent"]
        glow_draw.rounded_rectangle(
            [rx - 1 * SCALE, ry + 9 * SCALE, rx + int(4.5 * SCALE), ry + 49 * SCALE],
            radius=3 * SCALE,
            fill=(acc[0], acc[1], acc[2], 160),
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3.5 * SCALE))
    img.alpha_composite(glow_layer)

    draw = ImageDraw.Draw(img)

    # Top header divider & subtle neutral smoked-glass rim (R == G == B, no blue bg)
    draw.line([(3 * SCALE, 46 * SCALE), ((CARD_W - 4) * SCALE, 46 * SCALE)], fill=(28, 28, 28, 255), width=SCALE)
    draw.line([(16 * SCALE, 4 * SCALE), ((CARD_W - 16) * SCALE, 4 * SCALE)], fill=(38, 38, 38, 255), width=SCALE)

    # macOS Window Control Dots (Exact Red, Yellow, Green)
    for cx, col in [(22, (255, 95, 86, 255)), (40, (255, 189, 46, 255)), (58, (39, 201, 63, 255))]:
        r = int(5.5 * SCALE)
        draw.ellipse([cx * SCALE - r, 25 * SCALE - r, cx * SCALE + r, 25 * SCALE + r], fill=col)

    # Header Title
    draw.text((80 * SCALE, 15 * SCALE), "ABOUT ME", fill=(244, 244, 244, 255), font=FONT_TITLE_2X)

    # Right Header LIVE pill (pure near-black smoked glass fill)
    draw.rounded_rectangle(
        [768 * SCALE, 14 * SCALE, 822 * SCALE, 36 * SCALE],
        radius=11 * SCALE,
        fill=(11, 11, 11, 235),
        outline=(35, 134, 54, 255),
        width=SCALE,
    )
    draw.text((792 * SCALE, 19 * SCALE), "LIVE", fill=(57, 211, 83, 255), font=FONT_LIVE_2X)

    for row in ROWS_SPEC:
        rx, ry = 16 * SCALE, row["y"] * SCALE
        rw, rh = 512 * SCALE, 58 * SCALE
        acc = row["accent"]
        acc_rgba = (acc[0], acc[1], acc[2], 255)

        # Neutral dark smoked-glass outline on each of the 4 inner content boxes (R == G == B)
        draw.rounded_rectangle(
            [rx, ry, rx + rw, ry + rh],
            radius=10 * SCALE,
            fill=None,
            outline=(26, 26, 26, 255),
            width=SCALE,
        )
        # Subtle top smoked-glass bevel highlight on each content box
        draw.line(
            [(rx + 10 * SCALE, ry + 1 * SCALE), (rx + rw - 10 * SCALE, ry + 1 * SCALE)],
            fill=(40, 40, 40, 255),
            width=SCALE,
        )

        # Crisp glowing left small vertical accent line on the box
        draw.rounded_rectangle(
            [rx, ry + 9 * SCALE, rx + int(3.8 * SCALE), ry + 49 * SCALE],
            radius=2 * SCALE,
            fill=acc_rgba,
        )

        # Icon box (pure near-black fill with colored outline matching the row's icon color)
        ibx, iby = rx + 14 * SCALE, ry + 11 * SCALE
        ibs = 36 * SCALE
        draw.rounded_rectangle(
            [ibx, iby, ibx + ibs, iby + ibs],
            radius=8 * SCALE,
            fill=(11, 11, 11, 240),
            outline=(int(acc[0] * 0.48), int(acc[1] * 0.48), int(acc[2] * 0.48), 255),
            width=SCALE,
        )

        icx, icy = ibx + 18 * SCALE, iby + 18 * SCALE
        w_stroke = int(2 * SCALE)
        if row["icon"] == "code":
            draw.line([(icx - 5 * SCALE, icy - 5 * SCALE), (icx - 10 * SCALE, icy), (icx - 5 * SCALE, icy + 5 * SCALE)], fill=acc_rgba, width=w_stroke)
            draw.line([(icx + 5 * SCALE, icy - 5 * SCALE), (icx + 10 * SCALE, icy), (icx + 5 * SCALE, icy + 5 * SCALE)], fill=acc_rgba, width=w_stroke)
            draw.line([(icx + 2 * SCALE, icy - 7 * SCALE), (icx - 2 * SCALE, icy + 7 * SCALE)], fill=acc_rgba, width=w_stroke)
        elif row["icon"] == "cap":
            pts = [(icx, icy - 8 * SCALE), (icx - 11 * SCALE, icy - 2 * SCALE), (icx, icy + 3 * SCALE), (icx + 11 * SCALE, icy - 2 * SCALE)]
            draw.polygon(pts, outline=acc_rgba, width=w_stroke)
            draw.line([(icx - 7 * SCALE, icy + 1 * SCALE), (icx - 7 * SCALE, icy + 7 * SCALE), (icx + 7 * SCALE, icy + 7 * SCALE), (icx + 7 * SCALE, icy + 1 * SCALE)], fill=acc_rgba, width=w_stroke)
        elif row["icon"] == "mail":
            draw.rounded_rectangle([icx - 10 * SCALE, icy - 7 * SCALE, icx + 10 * SCALE, icy + 7 * SCALE], radius=2 * SCALE, outline=acc_rgba, width=w_stroke)
            draw.line([(icx - 9 * SCALE, icy - 5 * SCALE), (icx, icy + 1 * SCALE), (icx + 9 * SCALE, icy - 5 * SCALE)], fill=acc_rgba, width=w_stroke)
        elif row["icon"] == "bolt":
            pts = [(icx + 2 * SCALE, icy - 9 * SCALE), (icx - 7 * SCALE, icy + 1 * SCALE), (icx - 1 * SCALE, icy + 1 * SCALE), (icx - 3 * SCALE, icy + 9 * SCALE), (icx + 7 * SCALE, icy - 1 * SCALE), (icx + 1 * SCALE, icy - 1 * SCALE)]
            draw.polygon(pts, outline=acc_rgba, width=w_stroke)

        draw.text((rx + 62 * SCALE, ry + 11 * SCALE), row["label"], fill=acc_rgba, font=FONT_LABEL_2X)

        vx, vy = rx + 62 * SCALE, ry + 27 * SCALE
        draw.text((vx, vy), row["prefix"], fill=(236, 236, 236, 255), font=FONT_VALUE_2X)
        if row["highlight"]:
            bbox = draw.textbbox((0, 0), row["prefix"], font=FONT_VALUE_2X)
            pw_txt = bbox[2] - bbox[0]
            draw.text((vx + pw_txt, vy), row["highlight"], fill=acc_rgba, font=FONT_VALUE_BOLD_2X)

        if row["pill"]:
            px1, py1 = rx + 412 * SCALE, ry + 18 * SCALE
            px2, py2 = rx + 496 * SCALE, ry + 40 * SCALE
            draw.rounded_rectangle(
                [px1, py1, px2, py2],
                radius=6 * SCALE,
                fill=(11, 11, 11, 240),
                outline=(int(acc[0] * 0.45), int(acc[1] * 0.45), int(acc[2] * 0.45), 255),
                width=SCALE,
            )
            p_bbox = draw.textbbox((0, 0), row["pill"], font=FONT_PILL_2X)
            pt_w = p_bbox[2] - p_bbox[0]
            pt_h = p_bbox[3] - p_bbox[1]
            draw.text(
                (px1 + (84 * SCALE - pt_w) // 2, py1 + (22 * SCALE - pt_h) // 2 - 1 * SCALE),
                row["pill"],
                fill=acc_rgba,
                font=FONT_PILL_2X,
            )

    return img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


def build_border_overlay_2x():
    """Renders a sleek, clearly highlighted 1px neutral smoked-glass outline around the LARGE outer box."""
    img = Image.new("RGBA", (CW_2X, CH_2X), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Crisp 1px neutral smoked-glass outer outline (R == G == B)
    draw.rounded_rectangle(
        [2 * SCALE, 2 * SCALE, (CARD_W - 3) * SCALE, (CARD_H - 3) * SCALE],
        radius=14 * SCALE,
        fill=None,
        outline=(58, 58, 58, 255),
        width=int(1.3 * SCALE),
    )
    # Subtle top specular catchlight on the outer box border
    draw.line(
        [(16 * SCALE, 2 * SCALE), ((CARD_W - 16) * SCALE, 2 * SCALE)],
        fill=(82, 82, 82, 255),
        width=SCALE,
    )

    return img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


UI_FOREGROUND = build_ui_foreground_2x()
BORDER_OVERLAY = build_border_overlay_2x()

# Precompute vertical physical glass curvature profile for each Y line
Y_CURVE = [0.0] * CARD_H
for y in range(3, 47):
    rel = (y - 3) / 43.0
    Y_CURVE[y] = 2.5 * (1.0 - rel) ** 1.5
for ry_box in [60, 129, 198, 267]:
    for y in range(ry_box, ry_box + 58):
        rel = (y - ry_box) / 57.0
        Y_CURVE[y] = 3.0 * ((1.0 - rel) ** 1.7) + 1.0 * (rel ** 2.8)


def render_glass_and_rim(frame_idx, total_frames):
    """
    Renders a pure near-black neutral Dark Blur Glass interior (v = 9..24, R == G == B, ZERO blue bg!)
    plus a dynamic neutral Frosted Glass-Effect Outline (v = 30..92, R == G == B) on the 4 content boxes & outer box!
    """
    t = frame_idx / float(total_frames)
    phase = t * math.pi * 2.0

    GW, GH = CARD_W // 2, CARD_H // 2
    glass_small = Image.new("L", (GW, GH), 9)
    gs_px = glass_small.load()

    period = 640.0
    center_u1 = t * period
    center_u2 = ((t + 0.18) % 1.0) * period

    for sy in range(GH):
        y = sy * 2
        y_bevel = Y_CURVE[min(CARD_H - 1, y)]
        u_y = y * 0.57

        for sx in range(GW):
            x = sx * 2
            if 536 < x < (CARD_W - 10) and 48 < y < (CARD_H - 10):
                continue

            u = (x * 0.82 + u_y) % period

            d1 = abs(u - center_u1)
            if d1 > period * 0.5:
                d1 = period - d1

            d2 = abs(u - center_u2)
            if d2 > period * 0.5:
                d2 = period - d2

            # 1. Wide, ultra-blurred raised-cosine sliding wave (half-width 240px, subtle near-black range)
            if d1 < 240.0:
                c1 = 0.5 * (1.0 + math.cos(math.pi * d1 / 240.0))
                w1 = (c1 ** 1.4) * 9.5
            else:
                w1 = 0.0

            # 2. Secondary soft optical refraction wave (half-width 110px)
            if d2 < 110.0:
                c2 = 0.5 * (1.0 + math.cos(math.pi * d2 / 110.0))
                w2 = (c2 ** 1.6) * 3.8
            else:
                w2 = 0.0

            # 3. Gentle harmonic wave
            w3 = (0.5 + 0.5 * math.sin(phase - x * 0.007 + y * 0.01)) * 1.2

            lum = int(round(9.0 + y_bevel + w1 + w2 + w3))
            if lum < 9:
                lum = 9
            elif lum > 26:
                lum = 26
            gs_px[sx, sy] = lum

    # Upsample with BICUBIC + heavy GaussianBlur(12) for ultra-diffused, smoky near-black blur glass
    glass_l = glass_small.resize((CARD_W, CARD_H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(12))
    glass_rgba = Image.merge("RGBA", (glass_l, glass_l, glass_l, GLASS_MASK))

    # Dynamic Neutral Frosted Glass-Effect Outline on the 4 content boxes + outer box (v = 32..96, R == G == B)
    rim_l = glass_l.point(lambda v: min(98, max(30, int((v - 9) * 3.8 + 30))))
    rim_alpha = ImageChops.multiply(
        GLASS_RIM_MASK_1X,
        glass_l.point(lambda v: min(215, max(55, int((v - 9) * 9 + 55)))),
    )
    rim_rgba = Image.merge("RGBA", (rim_l, rim_l, rim_l, rim_alpha))

    return glass_rgba, rim_rgba


def build_exact_master_palette():
    """
    Constructs a mathematically exact 255-color palette:
      - Indices 1..135 (135 slots): Pure neutral grayscale (R == G == B):
          * Every single integer gray from 6 to 105 (100 lossless 1-step slots) -> ZERO banding on Near-Black Blur Glass & Outlines!
          * 35 gray slots from 108 to 255 -> crisp B&W ASCII portrait!
      - Indices 136..255 (120 slots): 15-step ultra-smooth anti-aliased ramps for all 8 UI accent colors
        blended against near-black (11, 11, 11) -> crystal-clear text, icons, pills, and glowing left small lines!
    """
    pal_entries = []

    # 1. Every single integer gray from 6 to 105 (100 slots) -> 100% lossless Near-Black Glass & Frosted Outlines!
    for v in range(6, 106):
        pal_entries.append((v, v, v))

    # 2. 35 gray slots from 108 to 255 for the B&W ASCII portrait
    for i in range(35):
        v = int(round(108.0 + (i / 34.0) * 147.0))
        pal_entries.append((v, v, v))

    GRAY_COUNT = len(pal_entries)  # 135 pure gray slots

    # 3. 15-step anti-aliased ramps for all 8 UI colors blended against near-black (11, 11, 11)
    ui_colors = [
        (255, 95, 86),    # Red window dot #FF5F56
        (255, 189, 46),   # Yellow window dot #FFBD2E
        (39, 201, 63),    # Green window dot #27C93F
        (0, 217, 255),    # Row 1 Electric Cyan-Blue #00D9FF
        (28, 214, 169),   # cyanBar midpoint teal
        (57, 211, 83),    # Row 2 Vibrant Green #39D353
        (14, 194, 232),   # Row 3 Bright Cyan-Blue #0EC2E8
        (235, 114, 106),  # Row 4 Warm Coral-Red #EB726A
    ]
    for ur, ug, ub in ui_colors:
        for step in range(1, 16):
            t_s = step / 15.0
            r = int(round(11 * (1.0 - t_s) + ur * t_s))
            g = int(round(11 * (1.0 - t_s) + ug * t_s))
            b = int(round(11 * (1.0 - t_s) + ub * t_s))
            pal_entries.append((r, g, b))

    while len(pal_entries) < 255:
        pal_entries.append((0, 0, 0))
    pal_entries = pal_entries[:255]

    # Fast O(1) lookup table for pure gray pixels (0..255) -> neutral gray palette index (1..135)
    gray_lut = [1] * 256
    for g_val in range(256):
        best_idx = 0
        best_dist = 999999
        for idx in range(GRAY_COUNT):
            pr, pg, pb = pal_entries[idx]
            d = abs(g_val - pr)
            if d < best_dist:
                best_dist = d
                best_idx = idx
        gray_lut[g_val] = best_idx + 1  # +1 because index 0 is transparent

    flat_pal = [0, 0, 0]
    for pr, pg, pb in pal_entries:
        flat_pal.extend([pr, pg, pb])

    return flat_pal, gray_lut, pal_entries


FLAT_PALETTE, GRAY_LUT, PAL_ENTRIES = build_exact_master_palette()

COLOR_CACHE = {}


def exact_palette_index(r, g, b):
    if r == g == b:
        return GRAY_LUT[r]
    key = (r << 16) | (g << 8) | b
    cached = COLOR_CACHE.get(key)
    if cached is not None:
        return cached
    best_idx = 1
    best_dist = 999999999
    for idx, (pr, pg, pb) in enumerate(PAL_ENTRIES):
        dr = r - pr
        dg = g - pg
        db = b - pb
        d = dr * dr + dg * dg + db * db
        if d < best_dist:
            best_dist = d
            best_idx = idx + 1
            if d == 0:
                break
    COLOR_CACHE[key] = best_idx
    return best_idx


def rgba_to_transparent_p(rgba_img):
    """
    Converts an RGBA frame to a transparent P-mode GIF frame:
      - All neutral gray pixels (Near-Black Blur Glass + Frosted Outlines + B&W Portrait) map in O(1) via GRAY_LUT[r] (100% lossless!)
      - Colored UI pixels (text, icons, pills, glowing left small lines, scan-line) map via exact 8-bit Euclidean distance!
    """
    p_img = Image.new("P", rgba_img.size, 0)
    p_img.putpalette(FLAT_PALETTE)

    rgba_px = rgba_img.load()
    p_px = p_img.load()

    for y in range(CARD_H):
        for x in range(CARD_W):
            r, g, b, a = rgba_px[x, y]
            if a < 95:
                p_px[x, y] = 0
            elif r == g == b:
                p_px[x, y] = GRAY_LUT[r]
            else:
                p_px[x, y] = exact_palette_index(r, g, b)

    p_img.info["transparency"] = 0
    return p_img


def render_combined_frame(frame_idx, total_frames):
    # 1. Slow-motion optical Near-Black Dark Blur Glass layer + dynamic Frosted Glass Rim (zero blue bg!)
    frame, rim_rgba = render_glass_and_rim(frame_idx, total_frames)

    # 2. Composite crisp 2x UI foreground (vibrant colored text, icons, pills, glowing left small lines)
    frame.alpha_composite(UI_FOREGROUND)
    # 3. Composite dynamic Frosted Glass-Effect Outlines on the 4 content boxes + outer box
    frame.alpha_composite(BORDER_OVERLAY)
    frame.alpha_composite(rim_rgba)
    draw = ImageDraw.Draw(frame)

    # 4. Animated small cyan-to-green scan-line bar directly under ABOUT ME (x=16..240, y=45..46)
    t_norm = frame_idx / float(total_frames)
    phase = t_norm * math.pi * 2.0
    scan_op = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(phase))
    wave_center_x = 128.0 + 96.0 * math.sin(phase)
    f_px = frame.load()
    for sx in range(16, 241):
        u_bar = (sx - 16.0) / 224.0
        tri = 1.0 - abs(2.0 * u_bar - 1.0)
        cr = int(0.0 * (1.0 - tri) + 57.0 * tri)
        cg = int(217.0 * (1.0 - tri) + 211.0 * tri)
        cb = int(255.0 * (1.0 - tri) + 83.0 * tri)
        dist_w = abs(sx - wave_center_x)
        local_boost = math.exp(-(dist_w * dist_w) / (2.0 * 42.0 * 42.0)) * 0.35
        eff_op = min(1.0, max(0.35, scan_op * 0.75 + local_boost))
        if sx < 24:
            eff_op *= (sx - 15.0) / 9.0
        elif sx > 232:
            eff_op *= (241.0 - sx) / 9.0
        for sy, row_w in ((45, 0.65), (46, 1.0)):
            a_bar = eff_op * row_w
            br, bg_c, bb, ba = f_px[sx, sy]
            nr = int(round(br * (1.0 - a_bar) + cr * a_bar))
            ng = int(round(bg_c * (1.0 - a_bar) + cg * a_bar))
            nb = int(round(bb * (1.0 - a_bar) + cb * a_bar))
            f_px[sx, sy] = (nr, ng, nb, 255)

    # 5. Animated slow-motion pulsing LIVE green dot & ring
    pulse = (math.sin(phase) + 1.0) * 0.5
    r_ring = int(3 + pulse * 5)
    ring_col = (int(11 + 46 * (1 - pulse)), int(11 + 200 * (1 - pulse)), int(11 + 72 * (1 - pulse)), 255)
    draw.ellipse([782 - r_ring, 25 - r_ring, 782 + r_ring, 25 + r_ring], outline=ring_col, width=1)
    draw.ellipse([782 - 3, 25 - 3, 782 + 3, 25 + 3], fill=(57, 211, 83, 255))

    # 6. Portrait placed strictly inside the box below the header (y=49..342) and flush right
    portrait_rgba = render_portrait_rgba(frame_idx, total_frames)
    p_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    p_layer.paste(portrait_rgba, (CARD_W - PW - 3, CARD_H - PH - 3), portrait_rgba)
    p_alpha = ImageChops.multiply(p_layer.split()[3], INNER_CLIP)
    p_layer.putalpha(p_alpha)

    frame.alpha_composite(p_layer)

    return frame


def main():
    TOTAL_FRAMES = 42
    FRAME_DURATION_MS = 70  # Ultra-smooth ~14.3 FPS (2.94s seamless cycle)
    print(f"Generating {TOTAL_FRAMES} Near-Black Blur Glass + Vibrant Colored Content frames ({CARD_W}x{CARD_H})...")
    t0 = time.time()

    frames_p = []
    for i in range(TOTAL_FRAMES):
        f_rgba = render_combined_frame(i, TOTAL_FRAMES)
        p_img = rgba_to_transparent_p(f_rgba)
        frames_p.append(p_img)
        if (i + 1) % 7 == 0 or i == TOTAL_FRAMES - 1:
            print(f"  Rendered {i + 1}/{TOTAL_FRAMES} frames...")

    frames_p[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames_p[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )
    gif_kb = os.path.getsize(OUT_GIF) / 1024.0
    print(f"Saved Near-Black Blur Glass unified {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

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

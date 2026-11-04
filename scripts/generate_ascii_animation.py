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

# Larger Portrait dimensions fitted strictly BELOW the header bar (y=48..341 -> height=293)
PW, PH = 296, 293

real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((32, 128, 534, 625)).resize((PW, PH), Image.Resampling.LANCZOS)
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

# Mask of the 4 glass boxes + header bar for the Dark Blur Glass effect
GLASS_MASK = Image.new("L", (CARD_W, CARD_H), 0)
gm_draw = ImageDraw.Draw(GLASS_MASK)
gm_draw.rounded_rectangle([3, 3, CARD_W - 4, 46], radius=13, fill=255)
gm_draw.rectangle([3, 32, CARD_W - 4, 46], fill=255)
for ry_box in [60, 129, 198, 267]:
    gm_draw.rounded_rectangle([16, ry_box, 16 + 512, ry_box + 58], radius=10, fill=255)

# Mask of the LARGE OUTER BOX outline for dynamic high-visibility specular highlight (NOT the inner content boxes)
OUTER_RIM_MASK = Image.new("L", (CW_2X, CH_2X), 0)
rm_draw = ImageDraw.Draw(OUTER_RIM_MASK)
rm_draw.rounded_rectangle(
    [2 * SCALE, 2 * SCALE, (CARD_W - 3) * SCALE, (CARD_H - 3) * SCALE],
    radius=14 * SCALE,
    fill=None,
    outline=255,
    width=int(2.5 * SCALE),
)
OUTER_RIM_MASK_1X = OUTER_RIM_MASK.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


def render_portrait_rgba(frame_idx, total_frames):
    glyph_mask = Image.new("L", (PW, PH), 0)
    draw_g = ImageDraw.Draw(glyph_mask)

    # Slow-motion scanline and gentle character breathing
    t = frame_idx / float(total_frames)
    sweep_r = t * p_rows
    slow_step = frame_idx // 2
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


ROWS_SPEC = [
    {
        "y": 60,
        "accent": (0, 217, 255),
        "icon": "code",
        "label": "CURRENTLY LEARNING",
        "prefix": "I'm currently learning ",
        "highlight": "MERN Stack",
        "pill": None,
    },
    {
        "y": 129,
        "accent": (57, 211, 83),
        "icon": "cap",
        "label": "EDUCATION & UNIVERSITY",
        "prefix": "I'm an ",
        "highlight": "Undergraduate at KDU",
        "pill": "BSc IT · LK",
    },
    {
        "y": 198,
        "accent": (88, 166, 255),
        "icon": "mail",
        "label": "HOW TO REACH ME",
        "prefix": "gayathrasamuditha45@gmail.com",
        "highlight": "",
        "pill": "Direct Mail",
    },
    {
        "y": 267,
        "accent": (255, 123, 114),
        "icon": "bolt",
        "label": "FUN FACT & ALIAS",
        "prefix": "Call me as ",
        "highlight": "Gayya",
        "pill": "@gayathra45",
    },
]


def build_ui_foreground_2x():
    """Renders crisp icons, text, pills, and base rims at 2x (zero blue background fill!)."""
    img = Image.new("RGBA", (CW_2X, CH_2X), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Top header divider & subtle frosted rim (pure neutral gray)
    draw.line([(3 * SCALE, 46 * SCALE), ((CARD_W - 4) * SCALE, 46 * SCALE)], fill=(44, 44, 44, 255), width=SCALE)
    draw.line([(16 * SCALE, 4 * SCALE), ((CARD_W - 16) * SCALE, 4 * SCALE)], fill=(64, 64, 64, 255), width=SCALE)

    # macOS Window Control Dots (Exact Red, Yellow, Green)
    for cx, col in [(22, (255, 95, 86, 255)), (40, (255, 189, 46, 255)), (58, (39, 201, 63, 255))]:
        r = int(5.5 * SCALE)
        draw.ellipse([cx * SCALE - r, 25 * SCALE - r, cx * SCALE + r, 25 * SCALE + r], fill=col)

    # Header Title
    draw.text((80 * SCALE, 15 * SCALE), "ABOUT ME", fill=(244, 244, 244, 255), font=FONT_TITLE_2X)

    # Right Header LIVE pill
    draw.rounded_rectangle(
        [768 * SCALE, 14 * SCALE, 822 * SCALE, 36 * SCALE],
        radius=11 * SCALE,
        fill=(15, 15, 15, 255),
        outline=(35, 134, 54, 255),
        width=SCALE,
    )
    draw.text((792 * SCALE, 19 * SCALE), "LIVE", fill=(57, 211, 83, 255), font=FONT_LIVE_2X)

    for row in ROWS_SPEC:
        rx, ry = 16 * SCALE, row["y"] * SCALE
        rw, rh = 512 * SCALE, 58 * SCALE
        acc = row["accent"]
        acc_rgba = (acc[0], acc[1], acc[2], 255)

        # Subtle dark glass border for inner content boxes (kept understated so the outer box is the main highlight)
        draw.rounded_rectangle(
            [rx, ry, rx + rw, ry + rh],
            radius=10 * SCALE,
            fill=None,
            outline=(36, 36, 36, 255),
            width=SCALE,
        )

        # Left glowing accent bar
        draw.rounded_rectangle(
            [rx, ry + 10 * SCALE, rx + int(3.5 * SCALE), ry + 48 * SCALE],
            radius=2 * SCALE,
            fill=acc_rgba,
        )

        # Icon box (pure neutral smoked obsidian #0F0F0F)
        ibx, iby = rx + 14 * SCALE, ry + 11 * SCALE
        ibs = 36 * SCALE
        draw.rounded_rectangle(
            [ibx, iby, ibx + ibs, iby + ibs],
            radius=8 * SCALE,
            fill=(15, 15, 15, 255),
            outline=(acc[0] // 2, acc[1] // 2, acc[2] // 2, 255),
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
                fill=(15, 15, 15, 255),
                outline=(acc[0] // 2, acc[1] // 2, acc[2] // 2, 255),
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
    """Renders a prominent, crisp highlighted outline around the LARGE outer box."""
    img = Image.new("RGBA", (CW_2X, CH_2X), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Soft outer ambient halo for depth
    draw.rounded_rectangle(
        [1 * SCALE, 1 * SCALE, (CARD_W - 2) * SCALE, (CARD_H - 2) * SCALE],
        radius=15 * SCALE,
        fill=None,
        outline=(75, 75, 75, 180),
        width=int(2.5 * SCALE),
    )

    # 2. Primary crisp highlighted outer box outline
    draw.rounded_rectangle(
        [2 * SCALE, 2 * SCALE, (CARD_W - 3) * SCALE, (CARD_H - 3) * SCALE],
        radius=14 * SCALE,
        fill=None,
        outline=(152, 152, 152, 255),
        width=int(2 * SCALE),
    )

    # 3. Extra-bright top & bottom specular edge highlights on the large outer box
    draw.line(
        [(16 * SCALE, 2 * SCALE), ((CARD_W - 16) * SCALE, 2 * SCALE)],
        fill=(215, 215, 215, 255),
        width=int(1.5 * SCALE),
    )
    draw.line(
        [(16 * SCALE, (CARD_H - 3) * SCALE), ((CARD_W - 16) * SCALE, (CARD_H - 3) * SCALE)],
        fill=(180, 180, 180, 255),
        width=SCALE,
    )

    return img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)


UI_FOREGROUND = build_ui_foreground_2x()
BORDER_OVERLAY = build_border_overlay_2x()

# Precompute vertical physical glass curvature profile for each Y line (top of each card is slightly brighter)
Y_CURVE = [0.0] * CARD_H
for y in range(3, 47):
    rel = (y - 3) / 43.0
    Y_CURVE[y] = 4.5 * (1.0 - rel) ** 1.6
for ry_box in [60, 129, 198, 267]:
    for y in range(ry_box, ry_box + 58):
        rel = (y - ry_box) / 57.0
        # Top inner bevel + subtle bottom bounce reflection
        Y_CURVE[y] = 5.0 * ((1.0 - rel) ** 1.8) + 1.8 * (rel ** 3.0)


def render_dark_blur_glass_and_rim(frame_idx, total_frames):
    """
    Renders a silky-smooth, slow-motion, realistic optical Dark Blur Glass backdrop
    plus a dynamic specular rim highlight around the LARGE OUTER BOX outline.
    Computed analytically per-pixel in pure neutral grayscale (R == G == B) for zero banding!
    """
    t = frame_idx / float(total_frames)
    phase = t * math.pi * 2.0

    # Render at 1/2 resolution (420x172) and bicubic-upsample to 840x345 for ultra-smooth optical glass diffusion
    GW, GH = CARD_W // 2, CARD_H // 2
    glass_small = Image.new("L", (GW, GH), 14)
    gs_px = glass_small.load()

    # Slow-motion continuous periodic light waves (wraps 100% seamlessly across the 36-frame loop)
    period = 680.0
    center_u1 = (t * period)  # Primary wide frosted glass wave
    center_u2 = ((t + 0.14) % 1.0) * period  # Secondary trailing double-pane specular caustic

    # Gentle harmonic breathing of ambient light behind the left icon column
    ambient_breath = 0.5 + 0.5 * math.sin(phase)

    for sy in range(GH):
        y = sy * 2
        y_bevel = Y_CURVE[min(CARD_H - 1, y)]
        u_y = y * 0.62
        dy_norm = (y - 172.0) / 180.0

        for sx in range(GW):
            x = sx * 2
            # Skip interior of portrait region except near the outer border (so the outer border still gets wave values!)
            if 536 < x < (CARD_W - 10) and 48 < y < (CARD_H - 10):
                continue

            u = (x * 0.78 + u_y) % period

            d1 = abs(u - center_u1)
            if d1 > period * 0.5:
                d1 = period - d1

            d2 = abs(u - center_u2)
            if d2 > period * 0.5:
                d2 = period - d2

            # 1. Primary wide Gaussian frosted glass sheen (sigma = 72px)
            w1 = math.exp(-(d1 * d1) / (2.0 * 72.0 * 72.0)) * 18.5

            # 2. Secondary crisp double-pane glass refraction streak (sigma = 22px)
            w2 = math.exp(-(d2 * d2) / (2.0 * 22.0 * 22.0)) * 9.5

            # 3. Soft ambient radial glow drifting slowly near the left glass cards
            dx_amb = (x - (140.0 + 75.0 * math.sin(phase + y * 0.008))) / 160.0
            w_amb = math.exp(-(dx_amb * dx_amb + dy_norm * dy_norm)) * (4.0 + 2.5 * ambient_breath)

            lum = int(round(13.5 + y_bevel + w1 + w2 + w_amb))
            if lum < 12:
                lum = 12
            elif lum > 58:
                lum = 58
            gs_px[sx, sy] = lum

    # Upsample with BICUBIC for sub-pixel silky smoothness
    glass_l = glass_small.resize((CARD_W, CARD_H), Image.Resampling.BICUBIC)
    glass_rgba = Image.merge("RGBA", (glass_l, glass_l, glass_l, GLASS_MASK))

    # Dynamic Specular Outer Border Highlight: gleams brightly up to (250, 250, 250) along the LARGE OUTER BOX outline
    outer_rim_l = glass_l.point(lambda v: min(252, max(155, int((v - 13) * 3.2 + 150))))
    outer_rim_alpha = ImageChops.multiply(OUTER_RIM_MASK_1X, glass_l.point(lambda v: min(255, max(0, int((v - 16) * 10)))))
    outer_rim_rgba = Image.merge("RGBA", (outer_rim_l, outer_rim_l, outer_rim_l, outer_rim_alpha))

    return glass_rgba, outer_rim_rgba


def build_exact_master_palette():
    """
    Constructs a mathematically exact 255-color palette:
      - Dedicated 1-step lossless grayscale slots for ALL Dark Blur Glass values (10..80) -> ZERO banding!
      - Full 2-step grayscale ramp up to 255 for the B&W ASCII portrait -> ZERO color cast!
      - Dedicated 12-step anti-aliased ramps for all 7 UI colors (Red/Yellow/Green window dots + 4 row accents)!
    """
    pal_entries = []

    # 1. Every single integer gray from 8 to 82 (75 slots) -> 100% lossless Dark Blur Glass!
    for v in range(8, 83):
        pal_entries.append((v, v, v))

    # 2. Every 2-step gray from 84 to 255 (86 slots) -> crisp B&W ASCII portrait!
    for v in range(84, 256, 2):
        pal_entries.append((v, v, v))
    pal_entries.append((255, 255, 255))

    # 3. Anti-aliased ramps for the 7 UI colors blended against dark smoked glass (15, 15, 15)
    ui_colors = [
        (255, 95, 86),    # Red window dot #FF5F56
        (255, 189, 46),   # Yellow window dot #FFBD2E
        (39, 201, 63),    # Green window dot #27C93F
        (0, 217, 255),    # Cyan row 1
        (57, 211, 83),    # Green row 2
        (88, 166, 255),   # Blue row 3
        (255, 123, 114),  # Coral row 4
    ]
    for ur, ug, ub in ui_colors:
        for step in range(1, 13):
            t_s = step / 12.0
            r = int(round(15 * (1.0 - t_s) + ur * t_s))
            g = int(round(15 * (1.0 - t_s) + ug * t_s))
            b = int(round(15 * (1.0 - t_s) + ub * t_s))
            pal_entries.append((r, g, b))

    # Pad to 255 colors
    while len(pal_entries) < 255:
        pal_entries.append((0, 0, 0))
    pal_entries = pal_entries[:255]

    # Build a fast O(1) lookup table for pure gray pixels (0..255) -> palette index (1..255)
    gray_lut = [1] * 256
    for g_val in range(256):
        best_idx = 0
        best_dist = 999999
        for idx, (pr, pg, pb) in enumerate(pal_entries):
            if pr == pg == pb:
                d = abs(g_val - pr)
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
        gray_lut[g_val] = best_idx + 1  # +1 because index 0 is transparent

    # Full 256-color flat palette with index 0 = (0, 0, 0) transparent
    flat_pal = [0, 0, 0]
    for pr, pg, pb in pal_entries:
        flat_pal.extend([pr, pg, pb])

    # Also create a PIL Image with the 255 colors for quantizing colored UI pixels
    pal_img = Image.new("P", (16, 16))
    raw_255_pal = []
    for pr, pg, pb in pal_entries:
        raw_255_pal.extend([pr, pg, pb])
    raw_255_pal.extend([0, 0, 0])
    pal_img.putpalette(raw_255_pal)

    return flat_pal, gray_lut, pal_img


FLAT_PALETTE, GRAY_LUT, PAL_QUANT_IMG = build_exact_master_palette()


def rgba_to_transparent_p(rgba_img):
    """
    Converts an RGBA frame to a transparent P-mode GIF frame using:
      - Direct O(1) lossless GRAY_LUT for all neutral gray pixels (Dark Blur Glass + B&W Portrait)
      - Exact palette quantization for colored UI accents
    Guarantees zero banding and zero color shift!
    """
    rgb = rgba_img.convert("RGB")
    q = rgb.quantize(palette=PAL_QUANT_IMG, dither=Image.Dither.NONE)

    p_img = Image.new("P", rgba_img.size, 0)
    p_img.putpalette(FLAT_PALETTE)

    q_px = q.load()
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
                p_px[x, y] = min(255, q_px[x, y] + 1)

    p_img.info["transparency"] = 0
    return p_img


def render_combined_frame(frame_idx, total_frames):
    # 1. Slow-motion optical Dark Blur Glass layer + dynamic outer box specular rim
    frame, outer_rim_rgba = render_dark_blur_glass_and_rim(frame_idx, total_frames)

    # 2. Composite crisp 2x UI foreground (borders, icons, text, pills)
    frame.alpha_composite(UI_FOREGROUND)
    draw = ImageDraw.Draw(frame)

    # 3. Animated slow-motion pulsing LIVE green dot & ring
    pulse = (math.sin((frame_idx / float(total_frames)) * math.pi * 2.0) + 1.0) * 0.5
    r_ring = int(3 + pulse * 5)
    ring_col = (int(15 + 42 * (1 - pulse)), int(15 + 196 * (1 - pulse)), int(15 + 68 * (1 - pulse)), 255)
    draw.ellipse([782 - r_ring, 25 - r_ring, 782 + r_ring, 25 + r_ring], outline=ring_col, width=1)
    draw.ellipse([782 - 3, 25 - 3, 782 + 3, 25 + 3], fill=(57, 211, 83, 255))

    # 4. Portrait placed strictly inside the box below the header (y=49..342) and flush right
    portrait_rgba = render_portrait_rgba(frame_idx, total_frames)
    p_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    p_layer.paste(portrait_rgba, (CARD_W - PW - 3, CARD_H - PH - 3), portrait_rgba)
    p_alpha = ImageChops.multiply(p_layer.split()[3], INNER_CLIP)
    p_layer.putalpha(p_alpha)

    frame.alpha_composite(p_layer)
    # 5. Prominent highlighted LARGE OUTER BOX outline + traveling specular reflection on top
    frame.alpha_composite(BORDER_OVERLAY)
    frame.alpha_composite(outer_rim_rgba)

    return frame


def main():
    TOTAL_FRAMES = 36
    FRAME_DURATION_MS = 90  # Slow-motion ~11.1 FPS (3.24s seamless cycle)
    print(f"Generating {TOTAL_FRAMES} Slow-Motion Dark Blur Glass + B&W ASCII frames ({CARD_W}x{CARD_H})...")
    t0 = time.time()

    frames_p = []
    for i in range(TOTAL_FRAMES):
        f_rgba = render_combined_frame(i, TOTAL_FRAMES)
        p_img = rgba_to_transparent_p(f_rgba)
        frames_p.append(p_img)
        if (i + 1) % 6 == 0 or i == TOTAL_FRAMES - 1:
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
    print(f"Saved Slow-Motion Dark Blur Glass unified {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

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

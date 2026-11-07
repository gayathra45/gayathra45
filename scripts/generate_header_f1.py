import os
import math
import base64
from PIL import Image, ImageDraw, ImageFilter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO_IMG = os.path.join(ROOT_DIR, "assets", "lego_f1_studio.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "header.gif")
OUT_SVG = os.path.join(ROOT_DIR, "header.svg")

# Load source 1376x768 photorealistic LEGO F1 studio render
base_im = Image.open(STUDIO_IMG).convert("RGB")
CROP_X0, CROP_Y0, CROP_X1, CROP_Y1 = 48, 148, 1328, 732
CARD_W, CARD_H = 840, 360

# Base cropped 840x360 studio image
base_card = base_im.crop((CROP_X0, CROP_Y0, CROP_X1, CROP_Y1)).resize(
    (CARD_W, CARD_H), Image.Resampling.LANCZOS
)
base_px = base_card.load()

# Exact wheel centers in 840x360 card space:
# Scale X = 840 / 1280 = 0.65625, Scale Y = 360 / 584 = 0.616438
SX = CARD_W / float(CROP_X1 - CROP_X0)
SY = CARD_H / float(CROP_Y1 - CROP_Y0)

WHEELS_CARD = [
    # (cx, cy, rx, ry, sign, is_refl)
    ((192.5 - CROP_X0) * SX, (395.5 - CROP_Y0) * SY, 42.0 * SX, 57.0 * SY, -1, False),  # Rear upper
    ((866.5 - CROP_X0) * SX, (437.5 - CROP_Y0) * SY, 58.0 * SX, 79.0 * SY, -1, False),  # Front upper
    ((196.0 - CROP_X0) * SX, (550.5 - CROP_Y0) * SY, 40.5 * SX, 53.0 * SY, +1, True),   # Rear reflection
    ((864.5 - CROP_X0) * SX, (620.5 - CROP_Y0) * SY, 56.0 * SX, 76.5 * SY, +1, True),   # Front reflection
]

# Pre-detect every colored Chrome ring pixel in base_card so ONLY the Chrome ring spins
# while preserving the exact 3D studio shading, specular highlights, and tire edges!
ring_pixels = []
for w_idx, (cx, cy, rx, ry, sign, is_refl) in enumerate(WHEELS_CARD):
    x0 = max(0, int(cx - rx * 1.18))
    x1 = min(CARD_W - 1, int(cx + rx * 1.18))
    y0 = max(0, int(cy - ry * 1.18))
    y1 = min(CARD_H - 1, int(cy + ry * 1.18))
    sat_thresh = 16 if is_refl else 28
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rx
            r_norm = math.hypot(dx, dy)
            if 0.48 <= r_norm <= 1.14:
                r, g, b = base_px[x, y]
                mx = max(r, g, b)
                mn = min(r, g, b)
                sat = mx - mn
                if sat >= sat_thresh and mx >= 28:
                    theta = math.atan2(dy, dx)
                    # Normalized chroma strength (0..1) and studio lighting intensity (mx)
                    chroma_ratio = sat / float(mx)
                    ring_pixels.append((x, y, theta, mx, mn, chroma_ratio, sign))


# Smooth 4-color Google Chrome wheel ring color wheel (Red -> Blue -> Green -> Yellow)
# Matching the exact orientation in the studio photo:
# Top-Right (-pi/2..0): Red, Right-Bottom (0..pi/2): Green/Blue, Bottom-Left (pi/2..pi): Green/Yellow, Top-Left (-pi..-pi/2): Blue/Yellow
CHROME_STOPS = [
    (0.00, (235, 52, 46)),   # Red
    (0.25, (42, 182, 76)),   # Green
    (0.50, (245, 188, 18)),  # Yellow
    (0.75, (38, 128, 235)),  # Blue
    (1.00, (235, 52, 46)),   # Red wrap
]


def sample_chrome_rgb(phase_01):
    p = phase_01 % 1.0
    for i in range(len(CHROME_STOPS) - 1):
        p0, c0 = CHROME_STOPS[i]
        p1, c1 = CHROME_STOPS[i + 1]
        if p0 <= p <= p1:
            u = (p - p0) / (p1 - p0)
            # Smoothstep blend at segment transitions for anti-aliased realism
            u = u * u * (3.0 - 2.0 * u)
            return (
                c0[0] + (c1[0] - c0[0]) * u,
                c0[1] + (c1[1] - c0[1]) * u,
                c0[2] + (c1[2] - c0[2]) * u,
            )
    return CHROME_STOPS[0][1]


def load_font(candidates, size):
    from PIL import ImageFont
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


MONO_BOLD = load_font([
    "C:/Windows/Fonts/consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
], 11)
SANS_BOLD = load_font([
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
], 12)

N_FRAMES = 24
frames = []

for f in range(N_FRAMES):
    t = f / float(N_FRAMES)
    card = base_card.copy()
    c_px = card.load()

    # 1. Rotate the 4-color Chrome wheel rings while preserving 100% of the 3D studio shading & tire edges
    for x, y, theta, mx, mn, chroma_ratio, sign in ring_pixels:
        base_phase = (theta / (2.0 * math.pi)) % 1.0
        rot_phase = (base_phase - sign * t) % 1.0
        cr, cg, cb = sample_chrome_rgb(rot_phase)
        c_max = max(cr, cg, cb)
        # Scale by original pixel's exact 3D studio brightness (mx) and saturation ratio
        nr = int(mn + (cr / c_max) * (mx - mn))
        ng = int(mn + (cg / c_max) * (mx - mn))
        nb = int(mn + (cb / c_max) * (mx - mn))
        c_px[x, y] = (min(255, nr), min(255, ng), min(255, nb))

    # 2. Cinematic Studio Anamorphic Light Sweep gliding across the LEGO Technic bodywork
    sweep_x = int(-120 + (CARD_W + 240) * t)
    for y in range(38, CARD_H - 6):
        for x in range(20, CARD_W - 20):
            r, g, b = c_px[x, y]
            lum = max(r, g, b)
            if lum > 24:
                dist = abs((x + (y - 180) * 0.25) - sweep_x)
                if dist < 90:
                    boost = ((1.0 - dist / 90.0) ** 2) * 0.28
                    c_px[x, y] = (
                        min(255, int(r * (1.0 + boost) + 24 * boost)),
                        min(255, int(g * (1.0 + boost) + 18 * boost)),
                        min(255, int(b * (1.0 + boost) + 12 * boost)),
                    )

    # 3. Subtle Wind-Tunnel Slipstream Filaments & Minimalist Top Bar
    ui = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    udraw = ImageDraw.Draw(ui)

    # Delicate wind-tunnel aero streams
    aero_streams = [
        (78, 95, 0.0, (255, 145, 45)),
        (128, 85, 0.35, (90, 175, 245)),
        (188, 110, 0.68, (180, 200, 220)),
    ]
    for sy, slen, phase, col in aero_streams:
        prog = (t + phase) % 1.0
        sx = int(CARD_W - 80 - prog * (CARD_W - 160))
        fade = math.sin(prog * math.pi)
        al = int(55 * fade)
        if al > 8:
            udraw.line([(sx, sy), (sx + slen, sy)], fill=(col[0], col[1], col[2], al), width=1)

    # Top-left pulsing papaya indicator dot + minimal role text (No name, clean cinematic look)
    dot_a = int(155 + 100 * math.sin(2.0 * math.pi * t))
    udraw.ellipse([22, 18, 28, 24], fill=(255, 128, 0, dot_a))
    udraw.text((36, 14), "FULL-STACK DEVELOPER  ·  IT UNDERGRADUATE", fill=(212, 218, 226, 215), font=SANS_BOLD)

    # Top-right understated spec tag
    udraw.text((642, 15), "MERN  ·  SYSTEMS  ·  KDU", fill=(132, 156, 178, 195), font=MONO_BOLD)

    # Subtle outer rounded border matching the ABOUT ME card below
    udraw.rounded_rectangle(
        [1, 1, CARD_W - 2, CARD_H - 2],
        radius=14,
        outline=(44, 46, 52, 255),
        width=1,
    )

    card_rgba = card.convert("RGBA")
    card_rgba.alpha_composite(ui)

    corner_mask = Image.new("L", (CARD_W, CARD_H), 0)
    cdraw = ImageDraw.Draw(corner_mask)
    cdraw.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=14, fill=255)

    final_frame = Image.new("RGB", (CARD_W, CARD_H), (13, 17, 23))
    final_frame.paste(card_rgba.convert("RGB"), (0, 0), corner_mask)
    frames.append(final_frame)

# Save preview frame for inspection
frames[6].save(os.path.join(ROOT_DIR, "assets", "preview_f1_frame.png"))

# Quantize with a shared global palette so animated GIF has zero flicker
master_strip = Image.new("RGB", (CARD_W, CARD_H * min(6, len(frames))))
for idx, fr in enumerate(frames[:6]):
    master_strip.paste(fr, (0, idx * CARD_H))
palette_img = master_strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

pal_frames = [
    fr.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)
    for fr in frames
]

pal_frames[0].save(
    OUT_GIF,
    save_all=True,
    append_images=pal_frames[1:],
    duration=55,
    loop=0,
    optimize=False,
)

with open(OUT_GIF, "rb") as f_gif:
    b64_gif = base64.b64encode(f_gif.read()).decode("ascii")

svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {CARD_H}" width="100%" height="100%" role="img" aria-label="LEGO Technic McLaren F1 Developer Header">
  <image width="{CARD_W}" height="{CARD_H}" href="data:image/gif;base64,{b64_gif}" />
</svg>
'''
with open(OUT_SVG, "w", encoding="utf-8") as f_svg:
    f_svg.write(svg_content)

print(f"Generated {OUT_GIF} ({os.path.getsize(OUT_GIF)//1024} KB) and {OUT_SVG}")

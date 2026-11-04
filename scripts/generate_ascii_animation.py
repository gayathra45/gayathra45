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

# Load real photo and apply tight cinematic bust crop (centers face + Sri Lanka flag patch)
real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((12, 118, 552, 790)).resize((460, 572), Image.Resampling.LANCZOS)
W, H = crop_rgb.size
px_raw = crop_rgb.load()

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
            FONT = ImageFont.truetype(fp, 11)
            break
        except Exception:
            pass
if not FONT:
    FONT = ImageFont.load_default()

# 1. Connected flood-fill background removal (100% transparent background, zero interior holes)
visited = [[False] * W for _ in range(H)]
q = deque()
for x in range(W):
    q.append((x, 0))
    visited[0][x] = True
for y in range(H - 80):
    q.append((0, y))
    q.append((W - 1, y))
    visited[y][0] = True
    visited[y][W - 1] = True

while q:
    cx, cy = q.popleft()
    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
        if 0 <= nx < W and 0 <= ny < H and not visited[ny][nx]:
            r, g, b = px_raw[nx, ny]
            if max(r, g, b) < 24:
                visited[ny][nx] = True
                q.append((nx, ny))

for sy in range(180, 290):
    for sx in range(120, 380):
        r, g, b = px_raw[sx, sy]
        if max(r, g, b) < 10 and not visited[sy][sx] and (sx < 175 or sx > 315):
            q.append((sx, sy))
            visited[sy][sx] = True
            while q:
                cx, cy = q.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and 0 <= ny < H and not visited[ny][nx]:
                        rr, gg, bb = px_raw[nx, ny]
                        if max(rr, gg, bb) < 20 and (nx < 185 or nx > 305):
                            visited[ny][nx] = True
                            q.append((nx, ny))

alpha = Image.new("L", (W, H), 255)
a_px = alpha.load()
for y in range(H):
    for x in range(W):
        if visited[y][x]:
            a_px[x, y] = 0
alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
a_px = alpha.load()

# 2. Natural Cinematic Color & Contrast Grading
cine_rgb = crop_rgb.filter(ImageFilter.UnsharpMask(radius=10, percent=115, threshold=3))
cine_rgb = ImageEnhance.Contrast(cine_rgb).enhance(1.12)
cine_rgb = ImageEnhance.Color(cine_rgb).enhance(1.10)
cine_l = cine_rgb.convert("L")

CW, CH = 7, 11
cols = W // CW
rows = H // CH
l_px = cine_l.load()
f_px = cine_rgb.load()

RAMP = " .,-:;+=*#%$&@MW"


def rgba_to_transparent_p(rgba_img, master_palette_img=None):
    rgb = rgba_img.convert("RGB")
    if master_palette_img is not None:
        q = rgb.quantize(palette=master_palette_img, dither=Image.Dither.NONE)
    else:
        q = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    pal = q.getpalette()[: 255 * 3]
    # Shift palette by +1 so index 0 is reserved for 100% transparency
    new_pal = [0, 0, 0] + pal
    p_img = Image.new("P", rgba_img.size, 0)
    p_img.putpalette(new_pal)

    q_px = q.load()
    rgba_px = rgba_img.load()
    p_px = p_img.load()
    for y in range(H):
        for x in range(W):
            if rgba_px[x, y][3] < 95:
                p_px[x, y] = 0
            else:
                p_px[x, y] = min(255, q_px[x, y] + 1)

    p_img.info["transparency"] = 0
    return p_img, q


def render_frame(frame_idx):
    glyph_mask = Image.new("L", (W, H), 0)
    draw_g = ImageDraw.Draw(glyph_mask)

    sweep_r = (frame_idx * 2.0) % rows
    flag_wave_c = 168 + int((frame_idx * 4) % 110)

    for r in range(rows):
        y = r * CH
        type_c = (frame_idx * 3 + r * 7) % cols
        dist_sweep = min(abs(r - sweep_r), abs(r - (sweep_r - rows)), abs(r - (sweep_r + rows)))
        sweep_boost = max(0.0, 1.0 - dist_sweep / 3.8)

        for c in range(cols):
            x = c * CW
            cx = min(W - 1, x + CW // 2)
            cy = min(H - 1, y + CH // 2)
            if a_px[cx, cy] < 95:
                continue
            lum = l_px[cx, cy]
            in_flag = 168 <= cx <= 266 and 374 <= cy <= 440
            if lum < 12 and not in_flag:
                continue

            base_idx = int((lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 9 + frame_idx) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            if in_flag:
                ch = "MW@#$%*+"[(c + r + frame_idx) % 8]
                val = 235 if abs(cx - flag_wave_c) > 9 else 255
            else:
                val = min(245, int(lum * 1.25 + 50))

            if sweep_boost > 0.15 and lum > 22:
                val = min(255, int(val + 75 * sweep_boost))
                if sweep_boost > 0.55:
                    ch = "MW@#$%"[(c + frame_idx) % 6]
            elif abs(c - type_c) <= 1 and (r % 2 == 0) and lum > 32:
                val = 255
                ch = "$" if lum > 110 else "@"

            draw_g.text((x, y - 1), ch, fill=val, font=FONT)

    g_px = glyph_mask.load()
    out_rgba = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o_px = out_rgba.load()

    for y in range(H):
        for x in range(W):
            if a_px[x, y] < 95:
                o_px[x, y] = (0, 0, 0, 0)
                continue
            r_v, g_v, b_v = f_px[x, y]
            gv = g_px[x, y]
            in_flag = 168 <= x <= 266 and 374 <= y <= 440
            in_eyes_smile = (165 <= x <= 310 and 120 <= y <= 165) or (195 <= x <= 285 and 182 <= y <= 220)

            if gv > 25:
                t_g = gv / 255.0
                boost = 0.45 if in_eyes_smile else (0.85 if in_flag else 0.72)
                nr = min(255, int(r_v * (1.0 + t_g * boost * 0.45) + t_g * boost * 75))
                ng = min(255, int(g_v * (1.0 + t_g * boost * 0.45) + t_g * boost * 78))
                nb = min(255, int(b_v * (1.0 + t_g * boost * 0.45) + t_g * boost * 82))
                o_px[x, y] = (nr, ng, nb, 255)
            else:
                recess = 0.78 if in_eyes_smile else (0.52 if in_flag else 0.56)
                o_px[x, y] = (int(r_v * recess), int(g_v * recess), int(b_v * recess), 255)

    return out_rgba


def main():
    TOTAL_FRAMES = 28
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} transparent-BG realistic ASCII frames ({W}x{H})...")
    t0 = time.time()

    frames_p = []
    master_pal = None
    for i in range(TOTAL_FRAMES):
        f_rgba = render_frame(i)
        p_img, q_ref = rgba_to_transparent_p(f_rgba, master_pal)
        if master_pal is None:
            master_pal = q_ref
        frames_p.append(p_img)
        if (i + 1) % 7 == 0 or i == TOTAL_FRAMES - 1:
            print(f"  Rendered {i + 1}/{TOTAL_FRAMES} frames...")

    frames_p[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames_p[1:],
        duration=int(1000 / FPS),
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )
    gif_kb = os.path.getsize(OUT_GIF) / 1024.0
    print(f"Saved transparent {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

    with open(OUT_GIF, "rb") as f:
        b64_gif = base64.b64encode(f.read()).decode("ascii")

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Animated ASCII Portrait">
  <image width="{W}" height="{H}" href="data:image/gif;base64,{b64_gif}"/>
</svg>'''

    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Saved synchronized transparent {OUT_SVG}")


if __name__ == "__main__":
    main()

import os
import time
import base64
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")

# Load real photo and apply tight bust crop so the subject & center Sri Lanka flag fill the frame
real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((16, 126, 548, 716)).resize((500, 554), Image.Resampling.LANCZOS)
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
for y in range(H - 90):
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

for sy in range(180, 310):
    for sx in range(120, 410):
        r, g, b = px_raw[sx, sy]
        if max(r, g, b) < 10 and not visited[sy][sx] and (sx < 185 or sx > 335):
            q.append((sx, sy))
            visited[sy][sx] = True
            while q:
                cx, cy = q.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and 0 <= ny < H and not visited[ny][nx]:
                        rr, gg, bb = px_raw[nx, ny]
                        if max(rr, gg, bb) < 20 and (nx < 195 or nx > 325):
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

# 2. High-Contrast Cinematic Black & White (Monochrome)
cine_l = crop_rgb.convert("L")
cine_l = cine_l.filter(ImageFilter.UnsharpMask(radius=12, percent=130, threshold=2))
cine_l = cine_l.filter(ImageFilter.UnsharpMask(radius=1.8, percent=145, threshold=1))
cine_l = ImageEnhance.Contrast(cine_l).enhance(1.22)

# Enhance contrast inside the center Sri Lanka flag patch (x: 184..287, y: 406..476)
# so the gold lion, sword, border, and stripes pop sharply against the maroon field in B&W
l_px = cine_l.load()
for fy in range(406, 476):
    for fx in range(184, 287):
        r_v, g_v, b_v = px_raw[fx, fy]
        if r_v > 140 and g_v > 95:  # Gold lion, border & orange/green stripes
            l_px[fx, fy] = min(255, int(l_px[fx, fy] * 1.25 + 35))
        elif r_v > 75 and g_v < 55:  # Dark maroon field behind the lion
            l_px[fx, fy] = max(28, int(l_px[fx, fy] * 0.65))

CW, CH = 7, 11
cols = W // CW
rows = H // CH
RAMP = " .,-:;+=*#%$&@MW"

# Exact 255-shade grayscale palette with index 0 reserved for 100% transparency
BW_PALETTE = [0, 0, 0]
for i in range(1, 256):
    BW_PALETTE.extend([i, i, i])


def render_bw_frame(frame_idx):
    glyph_mask = Image.new("L", (W, H), 0)
    draw_g = ImageDraw.Draw(glyph_mask)

    sweep_r = (frame_idx * 2.0) % rows
    flag_wave_c = 184 + int((frame_idx * 4) % 110)

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
            in_flag = 184 <= cx <= 287 and 406 <= cy <= 476
            if lum < 12 and not in_flag:
                continue

            base_idx = int((lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 9 + frame_idx) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            if in_flag:
                if lum > 110:
                    ch = "MW@#$%*"[(c + r + frame_idx) % 7]
                    val = 245 if abs(cx - flag_wave_c) > 9 else 255
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

            draw_g.text((x, y - 1), ch, fill=val, font=FONT)

    g_px = glyph_mask.load()
    p_img = Image.new("P", (W, H), 0)
    p_img.putpalette(BW_PALETTE)
    p_px = p_img.load()

    for y in range(H):
        for x in range(W):
            if a_px[x, y] < 95:
                p_px[x, y] = 0  # 100% transparent background
                continue
            lum = l_px[x, y]
            gv = g_px[x, y]
            in_flag = 184 <= x <= 287 and 406 <= y <= 476
            in_eyes_smile = (175 <= x <= 335 and 120 <= y <= 175) or (205 <= x <= 305 and 190 <= y <= 235)

            if gv > 25:
                t_g = gv / 255.0
                boost = 0.45 if in_eyes_smile else (0.85 if in_flag else 0.72)
                bw = min(255, int(lum * (1.0 + t_g * boost * 0.45) + t_g * boost * 78))
            else:
                recess = 0.78 if in_eyes_smile else (0.48 if in_flag else 0.54)
                bw = int(lum * recess)

            p_px[x, y] = max(1, min(255, bw))

    p_img.info["transparency"] = 0
    return p_img


def main():
    TOTAL_FRAMES = 28
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} B&W transparent-BG ASCII frames ({W}x{H})...")
    t0 = time.time()

    frames_p = []
    for i in range(TOTAL_FRAMES):
        frames_p.append(render_bw_frame(i))
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
    print(f"Saved B&W transparent {OUT_GIF} ({gif_kb:.1f} KB) in {time.time() - t0:.1f}s")

    with open(OUT_GIF, "rb") as f:
        b64_gif = base64.b64encode(f.read()).decode("ascii")

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Animated ASCII Portrait">
  <image width="{W}" height="{H}" href="data:image/gif;base64,{b64_gif}"/>
</svg>'''

    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Saved synchronized B&W transparent {OUT_SVG}")


if __name__ == "__main__":
    main()

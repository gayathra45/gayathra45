import os
import time
import base64
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")
OUT_ABOUT_SVG = os.path.join(ROOT_DIR, "about_me.svg")

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
l_px = cine_l.load()
for fy in range(406, 476):
    for fx in range(184, 287):
        r_v, g_v, b_v = px_raw[fx, fy]
        if r_v > 140 and g_v > 95:
            l_px[fx, fy] = min(255, int(l_px[fx, fy] * 1.25 + 35))
        elif r_v > 75 and g_v < 55:
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
                p_px[x, y] = 0
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


def build_combined_about_svg(b64_gif):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 840 325" width="100%" height="100%" role="img" aria-label="About Me - Gayathra Samuditha">
  <defs>
    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00D9FF" stop-opacity="0.75"/>
      <stop offset="50%" stop-color="#30363d" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#39D353" stop-opacity="0.70"/>
    </linearGradient>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#161b22"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>
    <linearGradient id="itemBg" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#1c2128"/>
      <stop offset="100%" stop-color="#13171e"/>
    </linearGradient>
    <linearGradient id="portraitBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#131820"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>
    <linearGradient id="cyanBar" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D9FF"/>
      <stop offset="50%" stop-color="#39D353"/>
      <stop offset="100%" stop-color="#00D9FF"/>
    </linearGradient>
    <radialGradient id="portraitGlow" cx="50%" cy="45%" r="50%">
      <stop offset="0%" stop-color="#00D9FF" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <clipPath id="portraitClip">
      <rect x="536" y="56" width="286" height="252" rx="10"/>
    </clipPath>
  </defs>

  <style>
    .title {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      font-weight: 700;
      font-size: 15.5px;
      fill: #f0f6fc;
      letter-spacing: 0.9px;
    }}
    .term-path {{
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 11.5px;
      fill: #8b949e;
    }}
    .label {{
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 9.8px;
      font-weight: 700;
      letter-spacing: 1.2px;
    }}
    .value {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      font-size: 14.5px;
      font-weight: 600;
      fill: #e6edf3;
    }}
    .highlight-cyan {{ fill: #00D9FF; font-weight: 700; }}
    .highlight-green {{ fill: #39D353; font-weight: 700; }}
    .highlight-pink {{ fill: #ff7b72; font-weight: 700; }}
    .cursor {{
      fill: #00D9FF;
      animation: blink 1s step-end infinite;
    }}
    .pulse-dot {{
      fill: #39D353;
      animation: pulse 2s ease-in-out infinite;
    }}
    .pulse-ring {{
      stroke: #39D353;
      fill: none;
      transform-origin: 786px 25px;
      animation: ring 2s ease-out infinite;
    }}
    .scan-line {{
      animation: scan 3.5s ease-in-out infinite;
    }}
    @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.45; }} }}
    @keyframes ring {{ 0% {{ r: 3.5px; opacity: 0.9; }} 100% {{ r: 10px; opacity: 0; }} }}
    @keyframes scan {{ 0%, 100% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} }}
  </style>

  <!-- Unified Full-Width Glassmorphic Card Frame -->
  <rect x="2" y="2" width="836" height="321" rx="14" fill="url(#cardBg)" stroke="url(#borderGrad)" stroke-width="1.5"/>

  <!-- Top Terminal Window Header Bar -->
  <path d="M 3 16 Q 3 3 16 3 L 824 3 Q 837 3 837 16 L 837 46 L 3 46 Z" fill="#161b22"/>
  <line x1="3" y1="46" x2="837" y2="46" stroke="#30363d" stroke-width="1"/>
  <line class="scan-line" x1="16" y1="46" x2="340" y2="46" stroke="url(#cyanBar)" stroke-width="2"/>

  <!-- macOS / Terminal Window Dots -->
  <circle cx="22" cy="25" r="5.5" fill="#ff5f56"/>
  <circle cx="40" cy="25" r="5.5" fill="#ffbd2e"/>
  <circle cx="58" cy="25" r="5.5" fill="#27c93f"/>

  <!-- Header Title & Path -->
  <text x="80" y="30" class="title">ABOUT ME</text>
  <text x="174" y="29" class="term-path">~/gayathra45/about.sh</text>
  <rect x="322" y="18" width="7" height="13" class="cursor"/>

  <!-- ASCII HUD Tag & Live Status Pill -->
  <text x="655" y="29" class="term-path" font-size="10.5">ASCII_PORTRAIT ::</text>
  <rect x="772" y="14" width="52" height="22" rx="11" fill="#0d1117" stroke="#238636" stroke-width="1"/>
  <circle cx="786" cy="25" r="3.5" class="pulse-ring" stroke-width="1.2"/>
  <circle cx="786" cy="25" r="3.5" class="pulse-dot"/>
  <text x="795" y="29" font-family="'Fira Code', monospace" font-size="9.5" font-weight="700" fill="#39D353">LIVE</text>

  <!-- ================= LEFT PANEL: 4 MODERN INFO ROWS ================= -->

  <!-- ROW 1: CURRENTLY LEARNING (MERN STACK) -->
  <g transform="translate(16, 58)">
    <rect x="0" y="0" width="504" height="56" rx="10" fill="url(#itemBg)" stroke="#21262d" stroke-width="1"/>
    <rect x="0" y="9" width="3.5" height="38" rx="1.75" fill="#00D9FF" filter="url(#glow)"/>
    <rect x="14" y="10" width="36" height="36" rx="8" fill="#0d1117" stroke="#00D9FF" stroke-opacity="0.45" stroke-width="1"/>
    <path d="M 27 23 L 22 28 L 27 33 M 37 23 L 42 28 L 37 33 M 34 21 L 30 35" fill="none" stroke="#00D9FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="62" y="21" class="label" fill="#00D9FF">CURRENTLY LEARNING</text>
    <text x="62" y="41" class="value">I'm currently learning <tspan class="highlight-cyan">MERN Stack</tspan></text>
  </g>

  <!-- ROW 2: EDUCATION (KDU) -->
  <g transform="translate(16, 122)">
    <rect x="0" y="0" width="504" height="56" rx="10" fill="url(#itemBg)" stroke="#21262d" stroke-width="1"/>
    <rect x="0" y="9" width="3.5" height="38" rx="1.75" fill="#39D353" filter="url(#glow)"/>
    <rect x="14" y="10" width="36" height="36" rx="8" fill="#0d1117" stroke="#39D353" stroke-opacity="0.45" stroke-width="1"/>
    <path d="M 32 20 L 21 25.5 L 32 31 L 43 25.5 Z M 25 28.5 V 34.5 C 25 36.5 39 36.5 39 34.5 V 28.5" fill="none" stroke="#39D353" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="62" y="21" class="label" fill="#39D353">EDUCATION &amp; UNIVERSITY</text>
    <text x="62" y="41" class="value">I'm an <tspan class="highlight-green">Undergraduate at KDU</tspan></text>
    <rect x="408" y="17" width="84" height="22" rx="6" fill="#0d1117" stroke="#39D353" stroke-opacity="0.35"/>
    <text x="450" y="32" font-family="'Fira Code', monospace" font-size="10" font-weight="600" fill="#39D353" text-anchor="middle">BSc IT · LK</text>
  </g>

  <!-- ROW 3: HOW TO REACH ME -->
  <g transform="translate(16, 186)">
    <rect x="0" y="0" width="504" height="56" rx="10" fill="url(#itemBg)" stroke="#21262d" stroke-width="1"/>
    <rect x="0" y="9" width="3.5" height="38" rx="1.75" fill="#58a6ff" filter="url(#glow)"/>
    <rect x="14" y="10" width="36" height="36" rx="8" fill="#0d1117" stroke="#58a6ff" stroke-opacity="0.45" stroke-width="1"/>
    <rect x="22" y="21" width="20" height="14" rx="2.5" fill="none" stroke="#58a6ff" stroke-width="1.8"/>
    <path d="M 23 22.5 L 32 29 L 41 22.5" fill="none" stroke="#58a6ff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="62" y="21" class="label" fill="#58a6ff">HOW TO REACH ME</text>
    <text x="62" y="41" class="value" font-size="13.5">gayathrasamuditha45@gmail.com</text>
    <rect x="408" y="17" width="84" height="22" rx="6" fill="#0d1117" stroke="#58a6ff" stroke-opacity="0.35"/>
    <text x="450" y="32" font-family="'Fira Code', monospace" font-size="10" font-weight="600" fill="#58a6ff" text-anchor="middle">Direct Mail</text>
  </g>

  <!-- ROW 4: FUN FACT -->
  <g transform="translate(16, 250)">
    <rect x="0" y="0" width="504" height="56" rx="10" fill="url(#itemBg)" stroke="#21262d" stroke-width="1"/>
    <rect x="0" y="9" width="3.5" height="38" rx="1.75" fill="#ff7b72" filter="url(#glow)"/>
    <rect x="14" y="10" width="36" height="36" rx="8" fill="#0d1117" stroke="#ff7b72" stroke-opacity="0.45" stroke-width="1"/>
    <polygon points="34,19 25,29 31,29 29,37 39,27 33,27" fill="none" stroke="#ff7b72" stroke-width="1.8" stroke-linejoin="round"/>
    <text x="62" y="21" class="label" fill="#ff7b72">FUN FACT &amp; ALIAS</text>
    <text x="62" y="41" class="value">Call me as <tspan class="highlight-pink">Gayya</tspan></text>
    <rect x="408" y="17" width="84" height="22" rx="6" fill="#0d1117" stroke="#ff7b72" stroke-opacity="0.35"/>
    <text x="450" y="32" font-family="'Fira Code', monospace" font-size="10" font-weight="600" fill="#ff7b72" text-anchor="middle">@gayathra45</text>
  </g>

  <!-- ================= RIGHT PANEL: EMBEDDED LIVE ASCII PORTRAIT BAY ================= -->
  <rect x="534" y="58" width="290" height="248" rx="10" fill="url(#portraitBg)" stroke="#21262d" stroke-width="1"/>
  <circle cx="679" cy="182" r="120" fill="url(#portraitGlow)"/>

  <!-- HUD Corner Accents inside Portrait Bay -->
  <path d="M 542 74 V 64 H 552" fill="none" stroke="#00D9FF" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M 816 74 V 64 H 806" fill="none" stroke="#00D9FF" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M 542 290 V 300 H 552" fill="none" stroke="#39D353" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M 816 290 V 300 H 806" fill="none" stroke="#39D353" stroke-width="1.5" stroke-linecap="round"/>

  <!-- Embedded Transparent-BG Real-Time B&W ASCII Portrait Animation -->
  <g clip-path="url(#portraitClip)">
    <image x="556" y="54" width="246" height="254" preserveAspectRatio="xMidYMax meet" href="data:image/gif;base64,{b64_gif}"/>
  </g>
</svg>'''


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

    combined_svg = build_combined_about_svg(b64_gif)
    with open(OUT_ABOUT_SVG, "w", encoding="utf-8") as f:
        f.write(combined_svg)
    print(f"Saved combined full-width {OUT_ABOUT_SVG} with embedded live ASCII portrait!")


if __name__ == "__main__":
    main()

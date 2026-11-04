import os
import math
import time
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")

# Load the real photo and crop empty top space (y=85..967 -> 561x882)
real_rgb = Image.open(REAL_PHOTO).convert("RGB")
real_rgb = real_rgb.crop((0, 85, real_rgb.width, real_rgb.height))
W, H = real_rgb.size

# Studio high-contrast grayscale conversion preserving 100% of real facial & gear details
real_l = real_rgb.convert("L")
real_l = ImageEnhance.Contrast(real_l).enhance(1.34)
real_l = ImageEnhance.Sharpness(real_l).enhance(1.95)


def scurve(p):
    if p < 14:
        return 0
    x = (p - 14) / 241.0
    return min(255, int(round((x ** 0.85) * 255)))


studio_l = real_l.point(scurve)

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
            FONT = ImageFont.truetype(fp, 12)
            break
        except Exception:
            pass
if not FONT:
    FONT = ImageFont.load_default()

# Precompute base tonal layer & contour masks
base_portrait = studio_l.point(lambda p: int(p * 0.80))
# Extra contrast depth on forehead & hair crown so white ASCII glyphs pop boldly
head_depth_mask = Image.new("L", (W, H), 0)
h_draw = ImageDraw.Draw(head_depth_mask)
h_draw.ellipse([185, 18, 370, 95], fill=130)     # Hair crown highlight zone
h_draw.ellipse([180, 115, 380, 195], fill=145)   # Forehead ASCII zone
head_depth_mask = head_depth_mask.filter(ImageFilter.GaussianBlur(10))
darker_head = studio_l.point(lambda p: int(p * 0.42))
base_portrait = Image.composite(darker_head, base_portrait, head_depth_mask)

# Sub-pixel contour clip mask so characters never bleed outside hair, glasses, camo, or rifle edges
clip_mask = studio_l.point(lambda p: min(255, int(p * 1.55)) if p > 15 else 0)

# Lifelike focal protection mask (eyes behind glasses, smile/teeth, Sri Lanka flag patch, shoulder badge, watch)
focal_mask = Image.new("L", (W, H), 0)
fd = ImageDraw.Draw(focal_mask)
fd.ellipse([185, 196, 375, 265], fill=225)                # Eyes & glasses frames
fd.ellipse([225, 282, 340, 346], fill=230)                # Smile & teeth
fd.rounded_rectangle([208, 470, 324, 550], radius=6, fill=250)  # Sri Lanka flag patch
fd.polygon([(485, 465), (560, 420), (560, 580), (485, 555)], fill=215)  # Right shoulder patch
focal_mask = focal_mask.filter(ImageFilter.GaussianBlur(8))

CW, CH = 8, 13
cols = W // CW
rows = H // CH
st_px = studio_l.load()

# High-contrast ASCII density ramp matching the portrait lighting
RAMP = " .,:;=+*#%$@MW"


def render_frame(frame_idx, total_frames):
    glyph_fg = Image.new("L", (W, H), 0)
    draw_fg = ImageDraw.Draw(glyph_fg)

    # Dual smooth vertical scan waves + horizontal real-time typing cursors
    scan_r1 = (frame_idx * 3) % rows
    scan_r2 = (frame_idx * 3 + rows // 2) % rows

    for r in range(rows):
        y = r * CH
        type_col = (frame_idx * 3 + r * 9) % cols
        on_scan = min(abs(r - scan_r1), abs(r - scan_r2)) <= 1

        for c in range(cols):
            x = c * CW
            cx = min(W - 1, x + CW // 2)
            cy = min(H - 1, y + CH // 2)
            lum = st_px[cx, cy]

            # Hair crown top ASCII strings (y < 95) trigger at lower luminance so crown ASCII is visible
            min_lum = 15 if (18 <= y <= 95 and 180 <= x <= 375) else 24
            if lum < min_lum:
                continue

            # Map pixel luminance to ASCII density ramp + live key oscillation
            eff_lum = min(255, int(lum * 1.45)) if y < 195 else lum
            base_idx = int((eff_lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 11 + frame_idx) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            # In bright forehead & camo highlight zones, emphasize signature M/W/@/#/$ keys
            if eff_lum > 165:
                ch = "MW@#$%"[(c + r + frame_idx) % 6]

            br = min(255, int(eff_lum * 1.38 + 42))

            if on_scan and lum > 45:
                br = 255
                ch = "@#MW$"[(c + frame_idx) % 5]
            elif abs(c - type_col) <= 1 and (r % 2 == 0) and lum > 50:
                br = 255
                ch = "$" if eff_lum > 135 else "@"

            draw_fg.text((x, y - 1), ch, fill=br, font=FONT)

    # Clip glyphs cleanly to sub-pixel portrait contours
    clipped_fg = ImageChops.multiply(glyph_fg, clip_mask)

    # 1px dark keystroke halo around each glyph so bright ASCII keys pop in 3D relief on bright areas
    halo = clipped_fg.filter(ImageFilter.MaxFilter(3)).point(lambda p: 255 - int(p * 0.62))
    etched_base = ImageChops.multiply(base_portrait, halo)

    # Combine etched portrait base + bright ASCII glyphs, then restore lifelike focal features
    combined = ImageChops.lighter(etched_base, clipped_fg)
    final_l = Image.composite(studio_l, combined, focal_mask)
    return final_l


def main():
    TOTAL_FRAMES = 30
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} frames of realistic ASCII portrait animation ({W}x{H})...")
    t0 = time.time()

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

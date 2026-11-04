import os
import math
import time
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PHOTO = os.path.join(ROOT_DIR, "assets", "real_photo.jpg")
OUT_GIF = os.path.join(ROOT_DIR, "ascii_portrait.gif")
OUT_SVG = os.path.join(ROOT_DIR, "ascii_portrait.svg")

# Load real photo and apply tight cinematic bust crop (centers face + Sri Lanka flag patch)
real_rgb = Image.open(REAL_PHOTO).convert("RGB")
crop_rgb = real_rgb.crop((12, 118, 552, 790)).resize((460, 572), Image.Resampling.LANCZOS)
W, H = crop_rgb.size

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
            FONT = ImageFont.truetype(fp, 10)
            break
        except Exception:
            pass
if not FONT:
    FONT = ImageFont.load_default()

# Cinematic tonal conversion (multi-scale unsharp mask for 3D depth & crisp detail)
gray = crop_rgb.convert("L")
cinematic_l = gray.filter(ImageFilter.UnsharpMask(radius=18, percent=145, threshold=2))
cinematic_l = cinematic_l.filter(ImageFilter.UnsharpMask(radius=2.0, percent=170, threshold=1))
cinematic_l = ImageEnhance.Contrast(cinematic_l).enhance(1.28)

# Soft vignette so edges blend seamlessly into GitHub's #0d1117 dark background
vig = Image.new("L", (W, H), 0)
vdraw = ImageDraw.Draw(vig)
vdraw.ellipse([-40, -20, W + 40, H + 60], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(35))


def cine_curve(p):
    if p < 16:
        return 0
    x = (p - 16) / 239.0
    return min(255, int(round((x ** 0.88) * 255)))


cinematic_l = cinematic_l.point(cine_curve)
cinematic_l = ImageChops.multiply(cinematic_l, vig)

# Boost contrast inside the center Sri Lanka flag patch (x: 168..266, y: 374..440)
# using red+green channels so the gold lion, stripes, border, and maroon field all animate richly
rgb_px = crop_rgb.load()
c_px = cinematic_l.load()
for fy in range(374, 441):
    for fx in range(168, 267):
        r_v, g_v, b_v = rgb_px[fx, fy]
        # Gold/orange/green stripes & lion pop brightly; maroon field gets clean midtone floor
        flag_lum = max(c_px[fx, fy], int(r_v * 0.55 + g_v * 0.45))
        if r_v > 75 and g_v < 50:  # Maroon field of Sri Lanka flag
            flag_lum = max(flag_lum, 62)
        c_px[fx, fy] = min(255, flag_lum)

base_portrait = cinematic_l.point(lambda p: int(p * 0.66))
sub_clip = cinematic_l.point(lambda p: min(255, int(p * 1.65)) if p > 12 else 0)

# Soften dark halo etching over eyes & smile so eyes/teeth stay lifelike while still displaying live ASCII
soft_eye_mask = Image.new("L", (W, H), 255)
sdraw = ImageDraw.Draw(soft_eye_mask)
sdraw.ellipse([160, 118, 315, 168], fill=110)  # Eyes behind glasses
sdraw.ellipse([192, 182, 285, 222], fill=120)  # Smile/teeth
soft_eye_mask = soft_eye_mask.filter(ImageFilter.GaussianBlur(6))

CW, CH = 6, 9
cols = W // CW
rows = H // CH

RAMP = " .,-:;+=*#%$&@MW"


def render_frame(frame_idx, total_frames):
    glyph_fg = Image.new("L", (W, H), 0)
    draw_fg = ImageDraw.Draw(glyph_fg)

    # Smooth cinematic light-sweep scanline + active Flag & Face key streams
    sweep_r = (frame_idx * 2.1) % rows
    flag_wave_c = 168 + int(((frame_idx * 4) % 110))

    for r in range(rows):
        y = r * CH
        type_c = (frame_idx * 3 + r * 7) % cols
        dist_sweep = min(abs(r - sweep_r), abs(r - (sweep_r - rows)), abs(r - (sweep_r + rows)))
        sweep_boost = max(0.0, 1.0 - dist_sweep / 4.5)

        for c in range(cols):
            x = c * CW
            cx = min(W - 1, x + CW // 2)
            cy = min(H - 1, y + CH // 2)
            lum = c_px[cx, cy]
            if lum < 12:
                continue

            in_flag = 168 <= cx <= 266 and 374 <= cy <= 440

            # Full-picture live ASCII key oscillation across 100% of face, hair, flag & tactical gear
            base_idx = int((lum / 255.0) * (len(RAMP) - 1))
            osc = ((c * 5 + r * 9 + frame_idx) % 3) - 1
            idx = max(1, min(len(RAMP) - 1, base_idx + osc))
            ch = RAMP[idx]

            if in_flag:
                if lum > 135:
                    ch = "MW@#$%"[(c + r + frame_idx) % 6]
                    br = 255
                elif lum > 80:
                    ch = "@#$%*+="[(c + r + frame_idx) % 7]
                    br = min(255, int(lum * 1.45 + 50))
                else:
                    ch = ":;+=*#"[(c + r + frame_idx) % 6]
                    br = min(230, int(lum * 1.55 + 45))
                # Horizontal wave across the Sri Lanka flag patch
                if abs(cx - flag_wave_c) <= 8:
                    br = 255
                    if lum > 90:
                        ch = "@" if (c + frame_idx) % 2 == 0 else "#"
            else:
                br = min(255, int(lum * 1.38 + 38))

            if sweep_boost > 0.1 and lum > 28:
                br = min(255, int(br + 65 * sweep_boost))
                if sweep_boost > 0.6 and lum > 80:
                    ch = "MW@#$%"[(c + frame_idx) % 6]
            elif abs(c - type_c) <= 1 and (r % 2 == 0) and lum > 42:
                br = min(255, br + 55)

            draw_fg.text((x, y - 1), ch, fill=br, font=FONT)

    # Sub-pixel contour clipping
    clipped_fg = ImageChops.multiply(glyph_fg, sub_clip)

    # 1px dark keystroke etching around every character for 3D relief
    raw_halo = clipped_fg.filter(ImageFilter.MaxFilter(3))
    mod_halo = ImageChops.multiply(raw_halo, soft_eye_mask)
    halo = mod_halo.point(lambda p: 255 - int(p * 0.56))
    etched_base = ImageChops.multiply(base_portrait, halo)

    combined_l = ImageChops.lighter(etched_base, clipped_fg)

    # Cinematic silver-platinum color grading on #0d1117 GitHub dark background
    r_lut = [13 if i <= 4 else min(255, int(13 + 232 * ((i / 255.0) ** 1.04))) for i in range(256)]
    g_lut = [17 if i <= 4 else min(255, int(17 + 235 * ((i / 255.0) ** 0.98))) for i in range(256)]
    b_lut = [23 if i <= 4 else min(255, int(23 + 232 * ((i / 255.0) ** 0.92))) for i in range(256)]

    out_rgb = Image.merge(
        "RGB",
        (combined_l.point(r_lut), combined_l.point(g_lut), combined_l.point(b_lut)),
    )
    return out_rgb


def main():
    TOTAL_FRAMES = 30
    FPS = 12
    print(f"Generating {TOTAL_FRAMES} frames of cinematic full-portrait ASCII animation ({W}x{H})...")
    t0 = time.time()

    frames = []
    for i in range(TOTAL_FRAMES):
        f_rgb = render_frame(i, TOTAL_FRAMES)
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

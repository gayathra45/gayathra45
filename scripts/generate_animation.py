import os, sys, re, math, time, random
from PIL import Image, ImageDraw, ImageFont

W, H = 804, 310
SCALE = 2
W_2X, H_2X = W * SCALE, H * SCALE
BG_COLOR = (13, 17, 23) # #0d1117 (GitHub Dark Mode)

# Building Face Colors
LEVEL_COLORS = {
    0: {"f": "#21262d", "t": "#30363d", "s": "#161b22"},
    1: {"f": "#9be9a8", "t": "#bef1c6", "s": "#79b683"},
    2: {"f": "#40c463", "t": "#83d99a", "s": "#32994d"},
    3: {"f": "#30a14e", "t": "#78c28c", "s": "#257e3d"},
    4: {"f": "#216e39", "t": "#6fa17e", "s": "#1a562c"},
}

# Modern architectural dark slate ground tiles (replaces harsh plain white pixels)
GROUND_SLATES = [
    {"f": (32, 38, 46),  "t": (46, 54, 64),  "s": (22, 26, 32)},
    {"f": (36, 42, 52),  "t": (50, 58, 70),  "s": (25, 30, 38)},
    {"f": (28, 34, 42),  "t": (40, 48, 58),  "s": (19, 23, 29)},
    {"f": (40, 46, 56),  "t": (54, 62, 74),  "s": (28, 33, 41)},
    {"f": (34, 40, 48),  "t": (48, 56, 66),  "s": (23, 27, 34)},
]

WINDOW_GREENS = [
    (14, 68, 41),    # #0E4429
    (0, 109, 50),    # #006D32
    (38, 166, 65),   # #26A641
    (57, 211, 83),   # #39D353
    (126, 231, 135), # Neon highlight
]

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Fonts
font_candidates = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]
FONT = None
FONT_BOLD = None
FONT_SMALL = None
for f_path in font_candidates:
    if os.path.exists(f_path):
        try:
            if not FONT:
                FONT = ImageFont.truetype(f_path, 13 * SCALE)
                FONT_SMALL = ImageFont.truetype(f_path, 11 * SCALE)
            if "b" in os.path.basename(f_path).lower() or "bold" in os.path.basename(f_path).lower():
                FONT_BOLD = ImageFont.truetype(f_path, 13 * SCALE)
        except Exception:
            pass

if not FONT:
    FONT = ImageFont.load_default()
if not FONT_BOLD:
    FONT_BOLD = FONT
if not FONT_SMALL:
    FONT_SMALL = FONT

# Load original boxes from scripts/skyline_data.json or fallback
data_json_path = os.path.join(os.path.dirname(__file__), 'skyline_data.json')
boxes = []
if os.path.exists(data_json_path):
    import json
    with open(data_json_path, 'r', encoding='utf-8') as f:
        boxes = json.load(f)
else:
    with open('skyline.svg', 'r', encoding='utf-8') as f:
        svg_text = f.read()
    pattern = r'<g transform="translate\((\d+) (\d+)\)"><g class="[^"]*"[^>]*><polygon class="l(\d) f" points="0,([-\d\.]+) 11,[-\d\.]+ 11,0 0,0"/>[\s\S]*?<title>(.*?): (\d+)</title>'
    raw_boxes = re.findall(pattern, svg_text)
    for idx, b in enumerate(raw_boxes):
        bx, by = int(b[0]), int(b[1])
        h = -float(b[3])
        boxes.append({
            'idx': idx,
            'x': bx,
            'y': by,
            'lv': int(b[2]),
            'h': h,
            'date': b[4],
            'count': int(b[5]),
        })

BW = 11
OX = 5
OY = 4

# Select two tactical target towers:
# Target 1: Mid-west cluster tower (at x=358, y=246, height 80.2)
# Target 2: Center-east skyscraper (at x=526, y=246, height 105.0)
target1_idx = None
target2_idx = None

for idx, b in enumerate(boxes):
    if b['x'] == 358 and b['y'] == 246:
        target1_idx = idx
    elif b['x'] == 526 and b['y'] == 246:
        target2_idx = idx

if target1_idx is None:
    target1_idx = 80
if target2_idx is None:
    target2_idx = 141

t1_orig_h = boxes[target1_idx]['h']
t2_orig_h = boxes[target2_idx]['h']
t1_pos = (boxes[target1_idx]['x'], boxes[target1_idx]['y'])
t2_pos = (boxes[target2_idx]['x'], boxes[target2_idx]['y'])

total_contributions = sum(b['count'] for b in boxes)
print(f"Loaded {len(boxes)} buildings.")
print(f"Target 1: {t1_pos}, height={t1_orig_h:.1f}")
print(f"Target 2: {t2_pos}, height={t2_orig_h:.1f}")

def draw_realistic_apache(draw, x, y, tilt_deg=0, rotor_angle=0, muzzle_flash=False, missile_fire=False, scale=SCALE):
    rad = math.radians(tilt_deg)
    cos_t, sin_t = math.cos(rad), math.sin(rad)
    cx, cy = 42, 17
    
    def pt(px, py):
        mx = 84 - px
        dx, dy = mx - cx, py - cy
        rx = dx * cos_t - dy * sin_t
        ry = dx * sin_t + dy * cos_t
        return ((x + cx + rx) * scale, (y + cy + ry) * scale)
    
    # Realistic Gunmetal & Carbon Military Shading
    c_shadow = (14, 18, 22)
    c_hull_dark = (36, 42, 50)
    c_hull_mid = (54, 62, 72)
    c_hull_light = (82, 92, 104)
    c_canopy = (10, 56, 32)
    c_hud_glow = (57, 211, 83)
    c_hud_bright = (126, 231, 135)
    c_pilot = (20, 24, 28)
    
    # 1. Tail Boom & Vertical Fin
    draw.polygon([pt(38, 16), pt(74, 14), pt(78, 10), pt(81, 10), pt(77, 18), pt(38, 20)], fill=c_hull_mid, outline=c_shadow)
    draw.polygon([pt(72, 16), pt(77, 3), pt(82, 3), pt(79, 18), pt(75, 18)], fill=c_hull_light, outline=c_shadow)
    draw.polygon([pt(66, 17), pt(74, 16), pt(75, 18), pt(65, 19)], fill=c_hull_dark)
    
    # Tail rotor (spinning on vertical fin)
    tr_cx, tr_cy = pt(80, 7)
    tr_len = 8 * scale
    for off in [0, math.pi / 2]:
        a = rotor_angle * 4.0 + off
        draw.line([
            (tr_cx + tr_len * math.cos(a), tr_cy + tr_len * math.sin(a)),
            (tr_cx - tr_len * math.cos(a), tr_cy - tr_len * math.sin(a))
        ], fill=(210, 225, 235), width=max(1, int(1.4 * scale)))
    
    # 2. Fuselage Main Body & Cheek Avionics Sponsons
    draw.polygon([
        pt(13, 19), pt(23, 12), pt(44, 12), pt(48, 18),
        pt(42, 25), pt(17, 25), pt(12, 22)
    ], fill=c_hull_mid, outline=c_shadow)
    
    draw.polygon([pt(26, 18), pt(42, 18), pt(44, 23), pt(24, 23)], fill=c_hull_dark, outline=c_hull_light)
    draw.polygon([pt(27, 11), pt(43, 11), pt(46, 16), pt(28, 16)], fill=c_shadow, outline=c_hull_light)
    draw.ellipse([pt(45, 13)[0] - 2*scale, pt(45, 13)[1] - 2*scale, pt(45, 13)[0] + 2*scale, pt(45, 13)[1] + 2*scale], fill=(10, 10, 10))
    
    # 3. Tandem Stepped Cockpit Glass & Pilot Silhouettes
    draw.polygon([pt(14, 18), pt(18, 14), pt(26, 14), pt(24, 19), pt(15, 19)], fill=c_canopy, outline=c_hud_glow)
    draw.polygon([pt(25, 17), pt(27, 13), pt(35, 13), pt(34, 18), pt(26, 18)], fill=c_canopy, outline=c_hud_glow)
    draw.ellipse([pt(20, 17)[0] - 1.5*scale, pt(20, 17)[1] - 1.5*scale, pt(20, 17)[0] + 1.5*scale, pt(20, 17)[1] + 1.5*scale], fill=c_pilot)
    draw.ellipse([pt(30, 16)[0] - 1.5*scale, pt(30, 16)[1] - 1.5*scale, pt(30, 16)[0] + 1.5*scale, pt(30, 16)[1] + 1.5*scale], fill=c_pilot)
    draw.line([pt(17, 15), pt(24, 15)], fill=c_hud_bright, width=max(1, int(scale)))
    draw.line([pt(27, 14), pt(33, 14)], fill=c_hud_bright, width=max(1, int(scale)))
    
    # 4. TADS/PNVS Nose FLIR Ball Turret
    t_center = pt(9, 19)
    t_r = 3.2 * scale
    draw.ellipse([t_center[0] - t_r, t_center[1] - t_r, t_center[0] + t_r, t_center[1] + t_r], fill=c_shadow, outline=c_hud_glow)
    draw.ellipse([t_center[0] - t_r*0.4, t_center[1] - t_r*0.4, t_center[0] + t_r*0.4, t_center[1] + t_r*0.4], fill=c_hud_bright)
    
    # 5. Articulated 30mm M230 Chain Gun
    g_start = pt(18, 25)
    g_end = pt(6, 30)
    draw.line([g_start, g_end], fill=c_shadow, width=int(2.8 * scale))
    draw.line([pt(12, 27), g_end], fill=c_hull_light, width=int(1.6 * scale))
    
    # Muzzle Flash
    if muzzle_flash:
        fx, fy = g_end
        f_size = 11 * scale
        flash_pts = [
            (fx, fy),
            (fx + f_size, fy + f_size * 0.4),
            (fx + f_size * 0.4, fy + f_size * 0.6),
            (fx + f_size * 1.4, fy + f_size * 0.8),
            (fx + f_size * 0.5, fy + f_size),
            (fx + f_size * 0.9, fy + f_size * 1.5),
            (fx, fy + f_size * 0.5)
        ]
        draw.polygon(flash_pts, fill=(57, 211, 83))
        draw.ellipse([fx - 4*scale, fy - 4*scale, fx + 6*scale, fy + 6*scale], fill=(255, 255, 255))
    
    # 6. Stub Wings & Hydra 70 / Hellfire Weapon Pylons
    draw.polygon([pt(25, 20), pt(35, 20), pt(36, 23), pt(24, 23)], fill=c_hull_light)
    r1, r2 = pt(25, 23), pt(33, 26)
    draw.rectangle([min(r1[0], r2[0]), min(r1[1], r2[1]), max(r1[0], r2[0]), max(r1[1], r2[1])], fill=c_shadow, outline=c_hud_glow)
    
    if missile_fire:
        mx_f, my_f = pt(24, 24)
        draw.ellipse([mx_f - 6*scale, my_f - 4*scale, mx_f + 8*scale, my_f + 6*scale], fill=(255, 180, 50))
        draw.ellipse([mx_f - 3*scale, my_f - 2*scale, mx_f + 5*scale, my_f + 3*scale], fill=(255, 255, 255))
    
    # 7. Landing Gear
    draw.line([pt(24, 24), pt(21, 29)], fill=c_shadow, width=int(2.0 * scale))
    w_c = pt(21, 29)
    draw.ellipse([w_c[0] - 2.2*scale, w_c[1] - 2.2*scale, w_c[0] + 2.2*scale, w_c[1] + 2.2*scale], fill=(12, 12, 14), outline=c_hull_mid)
    tg_c = pt(72, 19)
    draw.ellipse([tg_c[0] - 1.2*scale, tg_c[1] - 1.2*scale, tg_c[0] + 1.2*scale, tg_c[1] + 1.2*scale], fill=(12, 12, 14))
    
    # 8. Main Rotor Mast & Longbow Radome Dome
    draw.line([pt(33, 12), pt(33, 5)], fill=c_shadow, width=int(2.4 * scale))
    rad_c = pt(33, 5)
    draw.ellipse([rad_c[0] - 6.5*scale, rad_c[1] - 3.2*scale, rad_c[0] + 6.5*scale, rad_c[1] + 3.2*scale], fill=c_hull_mid, outline=c_hull_light)
    
    # Spinning 4-Blade Main Rotor
    hub_c = pt(33, 6)
    draw.ellipse([hub_c[0] - 46*scale, hub_c[1] - 4.5*scale, hub_c[0] + 46*scale, hub_c[1] + 4.5*scale], outline=(200, 220, 235, 70), width=int(scale))
    b_len = 44 * scale
    for b_off in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
        angle = rotor_angle + b_off
        bx = hub_c[0] + b_len * math.cos(angle)
        by = hub_c[1] + b_len * 0.16 * math.sin(angle)
        draw.line([hub_c, (bx, by)], fill=(205, 215, 225), width=int(2.2 * scale))
        draw.line([(bx - 3.5*scale * math.cos(angle), by - 3.5*scale * 0.16 * math.sin(angle)), (bx, by)], fill=(57, 211, 83), width=int(2.2 * scale))

def render_enhanced_frame(t):
    img_2x = Image.new('RGB', (W_2X, H_2X), BG_COLOR)
    draw = ImageDraw.Draw(img_2x)
    
    # Target 1 height & damage calculation
    t1_h = t1_orig_h
    t1_tilt = 0.0
    if 4.8 <= t < 5.8:
        t1_shake = math.sin((t - 4.8) * 50) * 3.5 * (1.0 - (t - 4.8) / 1.0)
    elif 5.8 <= t < 6.8:
        p1 = (t - 5.8) / 1.0
        t1_h = max(2.0, t1_orig_h * (1.0 - p1 * p1))
        t1_tilt = p1 * 5.0 * (1.0 - p1)
    elif 6.8 <= t < 10.4:
        t1_h = 2.0
    elif 10.4 <= t < 12.2:
        p_rb1 = (t - 10.4) / 1.8
        t1_h = 2.0 + (t1_orig_h - 2.0) * min(1.0, (1.0 - math.pow(1.0 - min(1.0, p_rb1 / 0.85), 3)))
    
    # Target 2 height & damage calculation
    t2_h = t2_orig_h
    t2_tilt = 0.0
    if 6.9 <= t < 7.9:
        t2_shake = math.sin((t - 6.9) * 50) * 3.5 * (1.0 - (t - 6.9) / 1.0)
    elif 7.9 <= t < 8.9:
        p2 = (t - 7.9) / 1.0
        t2_h = max(2.0, t2_orig_h * (1.0 - p2 * p2))
        t2_tilt = p2 * 5.0 * (1.0 - p2)
    elif 8.9 <= t < 11.2:
        t2_h = 2.0
    elif 11.2 <= t < 12.8:
        p_rb2 = (t - 11.2) / 1.6
        t2_h = 2.0 + (t2_orig_h - 2.0) * min(1.0, (1.0 - math.pow(1.0 - min(1.0, p_rb2 / 0.85), 3)))

    # Realistic Ground Earthquake Seismic Wave Ripple
    def get_ground_earthquake(bx, by):
        dy_quake = 0.0
        if 4.8 <= t < 7.0:
            dt1 = t - 4.8
            dist1 = math.hypot(bx - t1_pos[0], by - t1_pos[1])
            wave_front1 = dt1 * 90.0
            if abs(dist1 - wave_front1) < 40.0:
                atten = max(0.0, 1.0 - dt1 / 2.2) * max(0.0, 1.0 - abs(dist1 - wave_front1) / 40.0)
                dy_quake += math.sin((dist1 - wave_front1) * 0.25) * 4.0 * atten
        if 6.9 <= t < 9.2:
            dt2 = t - 6.9
            dist2 = math.hypot(bx - t2_pos[0], by - t2_pos[1])
            wave_front2 = dt2 * 90.0
            if abs(dist2 - wave_front2) < 40.0:
                atten2 = max(0.0, 1.0 - dt2 / 2.3) * max(0.0, 1.0 - abs(dist2 - wave_front2) / 40.0)
                dy_quake += math.sin((dist2 - wave_front2) * 0.25) * 4.5 * atten2
        return dy_quake

    # Draw Buildings back to front
    for idx, b in enumerate(boxes):
        bx = b['x']
        by = b['y']
        lv = b['lv']
        h = b['h']
        
        eq_dy = get_ground_earthquake(bx, by)
        by += eq_dy
        
        tilt_x = 0.0
        rebuild_glow = False
        if idx == target1_idx:
            h = t1_h
            tilt_x = t1_tilt
            if 4.8 <= t < 5.8:
                bx += math.sin((t - 4.8) * 45) * 2.5
            if 10.4 <= t < 12.2:
                rebuild_glow = True
        elif idx == target2_idx:
            h = t2_h
            tilt_x = t2_tilt
            if 6.9 <= t < 7.9:
                bx += math.sin((t - 6.9) * 45) * 2.5
            if 11.2 <= t < 12.8:
                rebuild_glow = True
        
        if lv == 0:
            s_idx = (int(b['x']) * 13 + int(b['y']) * 7) % len(GROUND_SLATES)
            s_pal = GROUND_SLATES[s_idx]
            f_col = s_pal["f"]
            t_col = s_pal["t"]
            s_col = s_pal["s"]
            if eq_dy != 0.0 and abs(eq_dy) > 1.2:
                f_col = (min(255, f_col[0] + 30), min(255, f_col[1] + 50), min(255, f_col[2] + 40))
        else:
            cols = LEVEL_COLORS[lv]
            f_col = hex_to_rgb(cols["f"])
            t_col = hex_to_rgb(cols["t"])
            s_col = hex_to_rgb(cols["s"])
            
            if rebuild_glow:
                f_col = (max(f_col[0], 25), min(255, f_col[1] + 70), max(f_col[2], 55))
                t_col = (max(t_col[0], 60), min(255, t_col[1] + 90), max(t_col[2], 90))
                s_col = (max(s_col[0], 20), min(255, s_col[1] + 50), max(s_col[2], 45))
        
        sx = bx * SCALE
        sy = by * SCALE
        sh = h * SCALE
        sBW = BW * SCALE
        sOX = OX * SCALE
        sOY = OY * SCALE
        tox = tilt_x * SCALE
        
        front_pts = [(sx + tox, sy - sh), (sx + sBW + tox, sy - sh), (sx + sBW, sy), (sx, sy)]
        top_pts = [(sx + tox, sy - sh), (sx + sBW + tox, sy - sh), (sx + sBW + sOX + tox, sy - sh - sOY), (sx + sOX + tox, sy - sh - sOY)]
        side_pts = [(sx + sBW + tox, sy - sh), (sx + sBW + sOX + tox, sy - sh - sOY), (sx + sBW + sOX, sy - sOY), (sx + sBW, sy)]
        
        draw.polygon(front_pts, fill=f_col)
        draw.polygon(top_pts, fill=t_col)
        draw.polygon(side_pts, fill=s_col)
        
        # Windows
        if h >= 22 and lv >= 1:
            show_win = True
            reboot_floor_limit = 999
            if idx == target1_idx:
                if 4.8 <= t < 11.5:
                    show_win = False
                elif 11.5 <= t < 12.3:
                    reboot_floor_limit = int(((t - 11.5) / 0.8) * 12)
            elif idx == target2_idx:
                if 6.9 <= t < 12.0:
                    show_win = False
                elif 12.0 <= t < 12.8:
                    reboot_floor_limit = int(((t - 12.0) / 0.8) * 14)
            
            if show_win:
                num_floors = int((h - 8) // 8)
                for floor in range(max(1, num_floors)):
                    floor_y = sy - sh + (8 + floor * 8) * SCALE
                    if floor_y >= sy - 4 * SCALE:
                        break
                    if (num_floors - floor) > reboot_floor_limit:
                        continue
                    
                    w_seed = (int(b['x']) * 31 + int(b['y']) * 17 + floor * 13)
                    if w_seed % 3 == 0:
                        color_idx = (w_seed + int(t * 1.5)) % len(WINDOW_GREENS)
                        w_col = WINDOW_GREENS[color_idx]
                        draw.rectangle([sx + 3 * SCALE + tox, floor_y, sx + 7 * SCALE + tox, floor_y + 3 * SCALE], fill=w_col)
                        sw_x = sx + sBW + 1 * SCALE + tox
                        sw_y = floor_y - 1 * SCALE
                        draw.polygon([
                            (sw_x, sw_y),
                            (sw_x + 2 * SCALE, sw_y - 1.5 * SCALE),
                            (sw_x + 2 * SCALE, sw_y + 2 * SCALE),
                            (sw_x, sw_y + 3.5 * SCALE)
                        ], fill=WINDOW_GREENS[max(0, color_idx - 1)])

    # Debris chunks & volumetric smoke particles for Target 1 & 2
    for (t_exp, exp_pos, orig_height) in [(4.8, t1_pos, t1_orig_h), (6.9, t2_pos, t2_orig_h)]:
        if t_exp <= t < t_exp + 1.8:
            dt_e = t - t_exp
            cex = (exp_pos[0] + BW / 2) * SCALE
            cey = (exp_pos[1] - orig_height * 0.6) * SCALE
            
            if dt_e < 0.4:
                fb_p = dt_e / 0.4
                fb_r = (22 * (1.0 - fb_p) + 8) * SCALE
                draw.ellipse([cex - fb_r, cey - fb_r, cex + fb_r, cey + fb_r], fill=(255, 140, 20))
                draw.ellipse([cex - fb_r*0.7, cey - fb_r*0.7, cex + fb_r*0.7, cey + fb_r*0.7], fill=(255, 220, 80))
                draw.ellipse([cex - fb_r*0.35, cey - fb_r*0.35, cex + fb_r*0.35, cey + fb_r*0.35], fill=(255, 255, 255))
                draw.ellipse([cex - fb_r*1.8, cey - fb_r*1.8, cex + fb_r*1.8, cey + fb_r*1.8], outline=(57, 211, 83), width=int(2*SCALE))
            
            for p_i in range(16):
                ang = (p_i / 16.0) * math.pi * 2 + 0.2
                spd = 22.0 + (p_i % 4) * 8.0
                px = cex + math.cos(ang) * spd * dt_e * SCALE
                py = cey + math.sin(ang) * spd * dt_e * 0.7 * SCALE + (0.5 * 90.0 * dt_e * dt_e * SCALE)
                sz = max(1, int((3.5 - dt_e * 1.6) * SCALE))
                c_chunk = (48, 56, 66) if p_i % 2 == 0 else (38, 166, 65)
                draw.rectangle([px, py, px + sz, py + sz], fill=c_chunk)
            
            dust_alpha = max(0.0, 1.0 - dt_e / 1.8)
            for d_i in range(6):
                dx_p = cex + (d_i - 2.5) * 9 * SCALE
                dy_p = exp_pos[1] * SCALE - (4 + dt_e * 10) * SCALE
                rad_d = (7 + dt_e * 16 + d_i * 2) * SCALE
                c_dust = (int(45 * dust_alpha), int(55 * dust_alpha), int(65 * dust_alpha))
                draw.ellipse([dx_p - rad_d, dy_p - rad_d * 0.4, dx_p + rad_d, dy_p + rad_d * 0.4], outline=c_dust, width=int(1.5 * SCALE))

    # Rebuilding Holographic Matrix Scaffolding (t: 10.4 to 12.8)
    for (t_rb, pos_rb, h_curr, h_max) in [(10.4, t1_pos, t1_h, t1_orig_h), (11.2, t2_pos, t2_h, t2_orig_h)]:
        if t_rb <= t < t_rb + 1.8:
            scan_y = (pos_rb[1] - h_curr) * SCALE
            draw.line([(pos_rb[0] - 14) * SCALE, scan_y, (pos_rb[0] + BW + OX + 14) * SCALE, scan_y], fill=(57, 211, 83), width=int(2 * SCALE))
            draw.line([(pos_rb[0] - 6) * SCALE, scan_y - 2*SCALE, (pos_rb[0] + BW + OX + 6) * SCALE, scan_y - 2*SCALE], fill=(126, 231, 135), width=int(SCALE))
            for m_i in range(6):
                mx_p = (pos_rb[0] + (m_i * 3)) * SCALE
                my_p = scan_y + ((m_i * 5) % 15) * SCALE
                draw.rectangle([mx_p, my_p, mx_p + 1.5*SCALE, my_p + 1.5*SCALE], fill=(57, 211, 83))

    # Apache Flight Dynamics & Weapons Systems
    heli_vis = True
    hx, hy = -200, 90
    tilt = 0.0
    gun_firing = False
    missile_launch = False
    rotor_angle = t * 38.0
    
    if t < 2.0:
        heli_vis = False
    elif 2.0 <= t < 4.4:
        p = (t - 2.0) / 2.4
        hx = -90 + 360 * (1.0 - math.pow(1.0 - p, 2))
        hy = 85 + math.sin(p * math.pi) * 8
        tilt = -6.0 * (1.0 - p)
    elif 4.4 <= t < 4.8:
        hx = 270 + math.sin(t * 30) * 1.0
        hy = 88
        tilt = -3.0
        missile_launch = True
    elif 4.8 <= t < 6.4:
        p_move = (t - 4.8) / 1.6
        hx = 270 + 130 * p_move
        hy = 88 + math.sin(p_move * math.pi) * 6
        tilt = math.sin(t * 4.0) * 2.0
    elif 6.4 <= t < 6.8:
        hx = 400 + math.sin(t * 50) * 1.0
        hy = 94
        tilt = -2.5
        gun_firing = True
        missile_launch = True
    elif 6.8 <= t < 8.2:
        hx = 400 + math.sin(t * 3.0) * 2.5
        hy = 94 + math.sin(t * 2.5) * 1.5
        tilt = -1.0
    elif 8.2 <= t < 10.4:
        p_dep = (t - 8.2) / 2.2
        hx = 400 + 530 * (p_dep * p_dep)
        hy = 94 - 40 * p_dep
        tilt = -9.0
    else:
        heli_vis = False

    # Guided Missile Flight & Smoke Trails!
    if 4.4 <= t < 4.8:
        mp1 = (t - 4.4) / 0.4
        m1_start = ((hx + 75) * SCALE, (hy + 22) * SCALE)
        m1_target = ((t1_pos[0] + BW/2) * SCALE, (t1_pos[1] - t1_orig_h * 0.7) * SCALE)
        mx_now = m1_start[0] + (m1_target[0] - m1_start[0]) * mp1
        my_now = m1_start[1] + (m1_target[1] - m1_start[1]) * mp1
        smoke_len = 20 * SCALE
        dx = m1_target[0] - m1_start[0]
        dy = m1_target[1] - m1_start[1]
        dist = math.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        draw.line([(mx_now - ux * smoke_len, my_now - uy * smoke_len), (mx_now, my_now)], fill=(255, 180, 50), width=int(2.8 * SCALE))
        draw.line([(mx_now - ux * smoke_len * 0.5, my_now - uy * smoke_len * 0.5), (mx_now, my_now)], fill=(255, 255, 255), width=int(1.5 * SCALE))
        draw.ellipse([mx_now - 2*SCALE, my_now - 2*SCALE, mx_now + 2*SCALE, my_now + 2*SCALE], fill=(57, 211, 83))

    if 6.5 <= t < 6.9:
        mp2 = (t - 6.5) / 0.4
        m2_start = ((hx + 75) * SCALE, (hy + 22) * SCALE)
        m2_target = ((t2_pos[0] + BW/2) * SCALE, (t2_pos[1] - t2_orig_h * 0.7) * SCALE)
        mx2_now = m2_start[0] + (m2_target[0] - m2_start[0]) * mp2
        my2_now = m2_start[1] + (m2_target[1] - m2_start[1]) * mp2
        smoke_len = 22 * SCALE
        dx2 = m2_target[0] - m2_start[0]
        dy2 = m2_target[1] - m2_start[1]
        dist2 = math.hypot(dx2, dy2)
        ux2, uy2 = dx2 / dist2, dy2 / dist2
        draw.line([(mx2_now - ux2 * smoke_len, my2_now - uy2 * smoke_len), (mx2_now, my2_now)], fill=(255, 180, 50), width=int(2.8 * SCALE))
        draw.line([(mx2_now - ux2 * smoke_len * 0.5, my2_now - uy2 * smoke_len * 0.5), (mx2_now, my2_now)], fill=(255, 255, 255), width=int(1.5 * SCALE))
        draw.ellipse([mx2_now - 2*SCALE, my2_now - 2*SCALE, mx2_now + 2*SCALE, my2_now + 2*SCALE], fill=(57, 211, 83))

    if heli_vis:
        draw_realistic_apache(draw, hx, hy, tilt_deg=tilt, rotor_angle=rotor_angle, muzzle_flash=gun_firing, missile_fire=missile_launch, scale=SCALE)

    # MODERN GLASSMORPHIC "BEST DAY" HUD BADGE WITH ANIMATED RADAR BEACON
    best_x = (774 + BW / 2 + OX / 2) * SCALE
    best_y = (238 - 140 - OY) * SCALE
    
    beacon_pulse = (math.sin(t * 6.0) + 1.0) * 0.5
    r_ping = (4.0 + beacon_pulse * 12.0) * SCALE
    pink_alpha = int(255 * (1.0 - beacon_pulse))
    draw.ellipse([best_x - r_ping, best_y - r_ping, best_x + r_ping, best_y + r_ping], outline=(255, 93, 115, pink_alpha), width=int(1.2 * SCALE))
    draw.ellipse([best_x - 3.5*SCALE, best_y - 3.5*SCALE, best_x + 3.5*SCALE, best_y + 3.5*SCALE], fill=(255, 93, 115))
    draw.ellipse([best_x - 1.5*SCALE, best_y - 1.5*SCALE, best_x + 1.5*SCALE, best_y + 1.5*SCALE], fill=(255, 255, 255))
    
    card_x = (W - 225) * SCALE
    card_y = 18 * SCALE
    draw.line([(best_x, best_y), (best_x, card_y + 20*SCALE), (card_x + 200*SCALE, card_y + 20*SCALE)], fill=(255, 93, 115), width=int(1.5 * SCALE))
    draw.ellipse([(best_x - 2*SCALE), (card_y + 20*SCALE - 2*SCALE), (best_x + 2*SCALE), (card_y + 20*SCALE + 2*SCALE)], fill=(255, 93, 115))
    
    badge_w = 200 * SCALE
    badge_h = 36 * SCALE
    badge_rect = [card_x, card_y, card_x + badge_w, card_y + badge_h]
    draw.rounded_rectangle(badge_rect, radius=6*SCALE, fill=(22, 27, 34), outline=(255, 93, 115), width=int(1.2*SCALE))
    
    # Left pill with gold star
    draw.rounded_rectangle([card_x + 6*SCALE, card_y + 6*SCALE, card_x + 50*SCALE, card_y + 30*SCALE], radius=4*SCALE, fill=(255, 93, 115))
    # Draw geometric star
    st_cx = card_x + 14 * SCALE
    st_cy = card_y + 18 * SCALE
    draw.polygon([
        (st_cx, st_cy - 4*SCALE), (st_cx + 1.2*SCALE, st_cy - 1.2*SCALE),
        (st_cx + 4*SCALE, st_cy - 1.2*SCALE), (st_cx + 1.8*SCALE, st_cy + 1.0*SCALE),
        (st_cx + 2.6*SCALE, st_cy + 4*SCALE), (st_cx, st_cy + 2.0*SCALE),
        (st_cx - 2.6*SCALE, st_cy + 4*SCALE), (st_cx - 1.8*SCALE, st_cy + 1.0*SCALE),
        (st_cx - 4*SCALE, st_cy - 1.2*SCALE), (st_cx - 1.2*SCALE, st_cy - 1.2*SCALE)
    ], fill=(255, 230, 100))
    draw.text((card_x + 22*SCALE, card_y + 11*SCALE), "64", fill=(255, 255, 255), font=FONT_BOLD)
    
    draw.text((card_x + 58*SCALE, card_y + 6*SCALE), "BEST DAY RECORD", fill=(126, 231, 135), font=FONT_SMALL)
    draw.text((card_x + 58*SCALE, card_y + 19*SCALE), "Nov 1, 2026 · Peak Activity", fill=(230, 237, 243), font=FONT_SMALL)

    # Footer diamond icon + contribution count
    dia_x = 22 * SCALE
    dia_y = (H - 16) * SCALE
    draw.polygon([(dia_x, dia_y - 4*SCALE), (dia_x + 4*SCALE, dia_y), (dia_x, dia_y + 4*SCALE), (dia_x - 4*SCALE, dia_y)], fill=(57, 211, 83))
    foot_label = f"{total_contributions} CONTRIBUTIONS IN THE LAST YEAR"
    draw.text((32 * SCALE, (H - 23) * SCALE), foot_label, fill=(139, 148, 158), font=FONT)

    final_img = img_2x.resize((W, H), Image.Resampling.LANCZOS)
    return final_img

def build_animated_svg():
    # Updates skyline.svg with the same modern slate base and cyber badge
    FONT_STACK = "'Fira Code',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    shapes = ""
    for idx, b in enumerate(boxes):
        bx, by = b['x'], b['y']
        lv = b['lv']
        h = b['h']
        date = b['date']
        cnt = b['count']
        
        # Slate palette for level 0
        if lv == 0:
            s_idx = (bx * 13 + by * 7) % len(GROUND_SLATES)
            s_pal = GROUND_SLATES[s_idx]
            f_hex = f"#{s_pal['f'][0]:02x}{s_pal['f'][1]:02x}{s_pal['f'][2]:02x}"
            t_hex = f"#{s_pal['t'][0]:02x}{s_pal['t'][1]:02x}{s_pal['t'][2]:02x}"
            s_hex = f"#{s_pal['s'][0]:02x}{s_pal['s'][1]:02x}{s_pal['s'][2]:02x}"
            shapes += f'<g transform="translate({bx} {by})"><g class="b">'
            shapes += f'<polygon points="0,{-h} {BW},{-h} {BW},0 0,0" fill="{f_hex}"/>'
            shapes += f'<polygon points="0,{-h} {BW},{-h} {BW + OX},{-h - OY} {OX},{-h - OY}" fill="{t_hex}"/>'
            shapes += f'<polygon points="{BW},{-h} {BW + OX},{-h - OY} {BW + OX},{-OY} {BW},0" fill="{s_hex}"/>'
            shapes += f'<title>{date}: {cnt}</title></g></g>'
        elif (bx == t1_pos[0] and by == t1_pos[1]) or (bx == t2_pos[0] and by == t2_pos[1]):
            # Target tower
            shapes += f'<g transform="translate({bx} {by})"><g class="target-tower">'
            shapes += f'<polygon class="l{lv} f" points="0,{-h} {BW},{-h} {BW},0 0,0"/>'
            shapes += f'<polygon class="l{lv} t" points="0,{-h} {BW},{-h} {BW + OX},{-h - OY} {OX},{-h - OY}"/>'
            shapes += f'<polygon class="l{lv} s" points="{BW},{-h} {BW + OX},{-h - OY} {BW + OX},{-OY} {BW},0"/>'
            num_floors = int((h - 8) // 8)
            for floor in range(max(1, num_floors)):
                floor_y = -h + 8 + floor * 8
                col_hex = ["#0e4429", "#006d32", "#26a641", "#39d353"][floor % 4]
                shapes += f'<rect class="target-win" x="3" y="{floor_y}" width="4" height="3" fill="{col_hex}"/>'
            shapes += f'<title>{date}: {cnt}</title></g></g>'
        else:
            shapes += f'<g transform="translate({bx} {by})"><g class="b">'
            shapes += f'<polygon class="l{lv} f" points="0,{-h} {BW},{-h} {BW},0 0,0"/>'
            shapes += f'<polygon class="l{lv} t" points="0,{-h} {BW},{-h} {BW + OX},{-h - OY} {OX},{-h - OY}"/>'
            shapes += f'<polygon class="l{lv} s" points="{BW},{-h} {BW + OX},{-h - OY} {BW + OX},{-OY} {BW},0"/>'
            if h >= 22 and lv >= 1:
                w_seed = bx * 31 + by * 17
                if w_seed % 3 == 0:
                    num_floors = int((h - 8) // 8)
                    for floor in range(max(1, num_floors)):
                        floor_y = -h + 8 + floor * 8
                        col_hex = ["#0e4429", "#006d32", "#26a641", "#39d353"][(w_seed + floor) % 4]
                        shapes += f'<rect class="win" x="3" y="{floor_y}" width="4" height="3" fill="{col_hex}"/>'
            shapes += f'<title>{date}: {cnt}</title></g></g>'

    # Modern Best Day HUD Badge in SVG
    best_x = 774 + BW / 2 + OX / 2
    best_y = 238 - 140 - OY
    card_x = W - 225
    card_y = 18
    
    badge_svg = f'''
    <!-- Best Day HUD Badge -->
    <g class="best-day-badge">
      <circle class="beacon-pulse" cx="{best_x}" cy="{best_y}" r="4" fill="none" stroke="#ff5d73" stroke-width="1.2"/>
      <circle cx="{best_x}" cy="{best_y}" r="3.5" fill="#ff5d73"/>
      <circle cx="{best_x}" cy="{best_y}" r="1.5" fill="#ffffff"/>
      <path d="M{best_x} {best_y} V{card_y + 20} L{card_x + 200} {card_y + 20}" fill="none" stroke="#ff5d73" stroke-width="1.5"/>
      <circle cx="{best_x}" cy="{card_y + 20}" r="2" fill="#ff5d73"/>
      <!-- Glassmorphic Card -->
      <rect x="{card_x}" y="{card_y}" width="200" height="36" rx="6" fill="#161b22" stroke="#ff5d73" stroke-width="1.2"/>
      <rect x="{card_x + 6}" y="{card_y + 6}" width="44" height="24" rx="4" fill="#ff5d73"/>
      <text x="{card_x + 28}" y="{card_y + 22}" text-anchor="middle" font-weight="700" font-size="12px" fill="#ffffff">★ 64</text>
      <text x="{card_x + 58}" y="{card_y + 17}" font-size="10px" font-weight="600" fill="#7ee787">BEST DAY RECORD</text>
      <text x="{card_x + 58}" y="{card_y + 29}" font-size="9px" fill="#e6edf3">Nov 1, 2026 · Peak Activity</text>
    </g>
    <polygon points="18,{H - 14} 22,{H - 18} 26,{H - 14} 22,{H - 10}" fill="#39d353"/>
    <text class="foot" x="32" y="{H - 10}" fill="#8b949e" font-size="11px">{total_contributions} CONTRIBUTIONS IN THE LAST YEAR</text>
    '''

    # Apache vector group in SVG
    apache_svg = f'''
    <g class="apache-squadron">
      <g class="apache-airframe">
        <g class="main-rotor-grp" transform="translate(47, 7)">
          <ellipse cx="0" cy="0" rx="44" ry="3.5" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
          <line class="rotor-spin" x1="-42" y1="0" x2="42" y2="0" stroke="#d0d7de" stroke-width="2"/>
          <line class="rotor-spin" x1="0" y1="-2" x2="0" y2="2" stroke="#d0d7de" stroke-width="2"/>
          <ellipse cx="0" cy="-2" rx="6" ry="3" fill="#30363d" stroke="#58a6ff" stroke-width="0.5"/>
        </g>
        <polygon points="42,16 8,14 4,10 2,10 6,18 42,20" fill="#30363d" stroke="#161b22" stroke-width="0.8"/>
        <polygon points="10,16 5,4 1,4 4,18 8,18" fill="#484f58" stroke="#161b22" stroke-width="0.8"/>
        <g class="tail-rotor-grp" transform="translate(3, 7)">
          <line class="tail-spin" x1="-8" y1="0" x2="8" y2="0" stroke="#d0d7de" stroke-width="1.5"/>
          <line class="tail-spin" x1="0" y1="-8" x2="0" y2="8" stroke="#d0d7de" stroke-width="1.5"/>
        </g>
        <polygon points="66,18 56,12 36,12 34,19 40,24 62,24 67,21" fill="#30363d" stroke="#21262d" stroke-width="1"/>
        <polygon points="52,11 37,11 35,17 52,17" fill="#161b22" stroke="#484f58" stroke-width="0.8"/>
        <polygon points="65,18 61,14 54,14 56,19 64,19" fill="#0e4429" stroke="#39d353" stroke-width="0.8"/>
        <polygon points="55,17 53,13 46,13 47,18 54,18" fill="#0e4429" stroke="#39d353" stroke-width="0.8"/>
        <circle cx="70" cy="18" r="3" fill="#161b22" stroke="#39d353" stroke-width="0.8"/>
        <circle cx="70" cy="18" r="1.2" fill="#39d353"/>
        <line x1="62" y1="24" x2="73" y2="28" stroke="#161b22" stroke-width="2.5" stroke-linecap="round"/>
        <polygon class="muzzle-burst" points="73,28 82,31 77,33 85,35 77,37 80,41 73,32" fill="#39d353"/>
        <polygon points="54,19 46,19 45,22 55,22" fill="#484f58"/>
        <rect x="47" y="22" width="7" height="3" fill="#161b22" stroke="#39d353" stroke-width="0.6"/>
        <line x1="56" y1="23" x2="59" y2="28" stroke="#161b22" stroke-width="1.8"/>
        <circle cx="59" cy="28" r="2" fill="#0d1117" stroke="#484f58" stroke-width="0.8"/>
      </g>
    </g>
    '''

    css = f'''
    :root {{ --txt: #e6edf3; }}
    text {{ font-family: {FONT_STACK}; fill: var(--txt); }}
    .l1.f {{ fill: #9be9a8; }} .l1.t {{ fill: #bef1c6; }} .l1.s {{ fill: #79b683; }}
    .l2.f {{ fill: #40c463; }} .l2.t {{ fill: #83d99a; }} .l2.s {{ fill: #32994d; }}
    .l3.f {{ fill: #30a14e; }} .l3.t {{ fill: #78c28c; }} .l3.s {{ fill: #257e3d; }}
    .l4.f {{ fill: #216e39; }} .l4.t {{ fill: #6fa17e; }} .l4.s {{ fill: #1a562c; }}
    
    .win {{ animation: win-breathe 3s ease-in-out infinite; }}
    @keyframes win-breathe {{ 0%, 100% {{ opacity: 0.8; }} 50% {{ opacity: 1; filter: drop-shadow(0 0 2px #39d353); }} }}
    
    .beacon-pulse {{ animation: beacon-ring 2s ease-out infinite; }}
    @keyframes beacon-ring {{ 0% {{ r: 3.5px; opacity: 1; }} 100% {{ r: 16px; opacity: 0; }} }}
    
    .apache-squadron {{
      animation: apache-flight 14s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      transform-origin: 42px 17px;
    }}
    @keyframes apache-flight {{
      0% {{ transform: translate(-100px, 85px) rotate(0deg); opacity: 0; }}
      14% {{ opacity: 1; }}
      30% {{ transform: translate(320px, 88px) rotate(-4deg); opacity: 1; }}
      45% {{ transform: translate(400px, 94px) rotate(-2deg); }}
      60% {{ transform: translate(400px, 94px) rotate(0deg); }}
      68% {{ transform: translate(420px, 94px) rotate(-8deg); opacity: 1; }}
      76% {{ transform: translate(920px, 50px) rotate(-9deg); opacity: 1; }}
      77%, 100% {{ transform: translate(920px, 50px); opacity: 0; }}
    }}
    
    .rotor-spin {{ transform-origin: 0 0; animation: r-spin 0.1s linear infinite; }}
    @keyframes r-spin {{ to {{ transform: rotate(360deg); }} }}
    
    .tail-spin {{ transform-origin: 0 0; animation: r-spin 0.05s linear infinite; }}
    
    .target-tower {{
      transform-origin: 0 0;
      animation: tower-cycle 14s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    @keyframes tower-cycle {{
      0%, 44% {{ transform: translate(0, 0) scaleY(1); }}
      45% {{ transform: translate(-2px, 0) scaleY(1); }}
      46% {{ transform: translate(2px, 0) scaleY(1); }}
      47% {{ transform: translate(-1px, 0) scaleY(1); }}
      52% {{ transform: translate(0, 0) scaleY(0.5); }}
      56%, 74% {{ transform: translate(0, 0) scaleY(0.02); }}
      75% {{ transform: translate(0, 0) scaleY(0.05); filter: drop-shadow(0 0 6px #39d353); }}
      85% {{ transform: translate(0, 0) scaleY(1.04); }}
      88%, 100% {{ transform: translate(0, 0) scaleY(1); filter: none; }}
    }}
    
    .target-win {{
      animation: target-win-seq 14s ease infinite;
    }}
    @keyframes target-win-seq {{
      0%, 44% {{ opacity: 1; }}
      45%, 84% {{ opacity: 0; }}
      85%, 100% {{ opacity: 1; }}
    }}
    '''

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution skyline: {total_contributions} contributions in the last year">
    <style>
    {css}
    </style>
    <rect width="{W}" height="{H}" fill="#0d1117"/>
    {shapes}
    {badge_svg}
    {apache_svg}
    </svg>'''
    
    with open('skyline.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("skyline.svg updated successfully!")

# 1. Update skyline.svg
build_animated_svg()

# 2. Render full 140 frames for skyline.gif
TOTAL_DURATION = 14.0 # seconds
FPS = 10
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)
DT = TOTAL_DURATION / TOTAL_FRAMES

print(f"Generating {TOTAL_FRAMES} frames at {FPS} FPS (total duration: {TOTAL_DURATION}s)...")
start_time = time.time()
frames = []

for i in range(TOTAL_FRAMES):
    t_val = i * DT
    f_img = render_enhanced_frame(t_val)
    q_img = f_img.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    frames.append(q_img)
    if (i + 1) % 20 == 0 or i == TOTAL_FRAMES - 1:
        print(f"Rendered {i+1}/{TOTAL_FRAMES} frames ({((i+1)/TOTAL_FRAMES)*100:.1f}%)")

print(f"Render completed in {time.time() - start_time:.1f}s. Saving skyline.gif...")
frames[0].save(
    "skyline.gif",
    save_all=True,
    append_images=frames[1:],
    duration=int(1000 / FPS),
    loop=0,
    optimize=False
)

gif_size = os.path.getsize("skyline.gif")
print(f"skyline.gif generated successfully! Size: {gif_size / 1024:.1f} KB")

# 3. Synchronize skyline.svg with the exact same animation
import base64
with open("skyline.gif", "rb") as f:
    gif_bytes = f.read()
b64_gif = base64.b64encode(gif_bytes).decode('ascii')

synced_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="GitHub contribution skyline: {total_contributions} contributions in the last year">
  <image width="{W}" height="{H}" href="data:image/gif;base64,{b64_gif}"/>
</svg>'''

with open("skyline.svg", "w", encoding="utf-8") as f:
    f.write(synced_svg)

print(f"skyline.svg synchronized! Both skyline.gif and skyline.svg are now 100% identical.")

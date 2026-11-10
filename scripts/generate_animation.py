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

# Select three tactical target towers across the skyline:
def pick_sector_target(target_x, x_min, x_max, fallback_idx):
    for idx, b in enumerate(boxes):
        if b.get('x') == target_x and (idx == fallback_idx or b.get('h', 0) > 15):
            return idx
    candidates = [b for b in boxes if x_min <= b.get('x', 0) <= x_max and b.get('h', 0) > 20]
    if candidates:
        best = max(candidates, key=lambda b: (b.get('h', 0), -abs(b.get('x', 0) - target_x)))
        return best['idx']
    if boxes:
        return min(boxes, key=lambda b: abs(b.get('x', 0) - target_x))['idx']
    return fallback_idx

target1_idx = pick_sector_target(358, 320, 410, 129)
target2_idx = pick_sector_target(464, 420, 500, 346)
target3_idx = pick_sector_target(526, 500, 600, 141)

t1_orig_h = boxes[target1_idx]['h']
t2_orig_h = boxes[target2_idx]['h']
t3_orig_h = boxes[target3_idx]['h']
t1_pos = (boxes[target1_idx]['x'], boxes[target1_idx]['y'])
t2_pos = (boxes[target2_idx]['x'], boxes[target2_idx]['y'])
t3_pos = (boxes[target3_idx]['x'], boxes[target3_idx]['y'])

total_contributions = sum(b.get('count', 0) for b in boxes)
best_box = max(boxes, key=lambda b: b.get('count', 0)) if boxes else None
best_count = best_box['count'] if best_box else 0
best_x = int(best_box['x'] + BW / 2 + OX / 2) if best_box else (774 + BW / 2 + OX / 2)
best_y = int(best_box['y'] - best_box['h'] - OY) if best_box else (238 - 140 - OY)

if best_box and best_box.get('date'):
    try:
        from datetime import datetime
        dt = datetime.strptime(best_box['date'], "%Y-%m-%d")
        best_date_str = dt.strftime("%b %d, %Y")
    except Exception:
        best_date_str = str(best_box['date'])
else:
    best_date_str = "Peak Activity"

latest_year = max(b['date'][:4] for b in boxes if b.get('date')) if boxes else '2026'

print(f"Loaded {len(boxes)} buildings. Total contributions: {total_contributions:,} in {latest_year}")
print(f"Best Day: {best_date_str} with {best_count} contributions at ({best_x}, {best_y})")
print(f"Target 1: {t1_pos}, height={t1_orig_h:.1f}")
print(f"Target 2: {t2_pos}, height={t2_orig_h:.1f}")
print(f"Target 3: {t3_pos}, height={t3_orig_h:.1f}")

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
    
    # 3 Tactical Targets across the skyline:
    # Target 1: (358, 246), h=80.2  -> strike at t=4.2s, collapse 4.2-5.2s, rebuild 8.8-10.4s
    # Target 2: (464, 262), h=89.2  -> strike at t=6.0s, collapse 6.0-7.0s, rebuild 9.8-11.4s
    # Target 3: (526, 246), h=105.0 -> strike at t=7.6s, collapse 7.6-8.6s, rebuild 10.8-12.4s

    t1_h = t1_orig_h
    t1_tilt = 0.0
    if 4.2 <= t < 5.2:
        p1 = (t - 4.2) / 1.0
        t1_h = max(2.0, t1_orig_h * (1.0 - p1 * p1))
        t1_tilt = p1 * 4.0 * (1.0 - p1)
    elif 5.2 <= t < 8.8:
        t1_h = 2.0
    elif 8.8 <= t < 10.4:
        p_rb1 = (t - 8.8) / 1.6
        t1_h = 2.0 + (t1_orig_h - 2.0) * min(1.0, 1.0 - math.pow(1.0 - min(1.0, p_rb1 / 0.85), 3))

    t2_h = t2_orig_h
    t2_tilt = 0.0
    if 6.0 <= t < 7.0:
        p2 = (t - 6.0) / 1.0
        t2_h = max(2.0, t2_orig_h * (1.0 - p2 * p2))
        t2_tilt = p2 * 4.0 * (1.0 - p2)
    elif 7.0 <= t < 9.8:
        t2_h = 2.0
    elif 9.8 <= t < 11.4:
        p_rb2 = (t - 9.8) / 1.6
        t2_h = 2.0 + (t2_orig_h - 2.0) * min(1.0, 1.0 - math.pow(1.0 - min(1.0, p_rb2 / 0.85), 3))

    t3_h = t3_orig_h
    t3_tilt = 0.0
    if 7.6 <= t < 8.6:
        p3 = (t - 7.6) / 1.0
        t3_h = max(2.0, t3_orig_h * (1.0 - p3 * p3))
        t3_tilt = p3 * 4.0 * (1.0 - p3)
    elif 8.6 <= t < 10.8:
        t3_h = 2.0
    elif 10.8 <= t < 12.4:
        p_rb3 = (t - 10.8) / 1.6
        t3_h = 2.0 + (t3_orig_h - 2.0) * min(1.0, 1.0 - math.pow(1.0 - min(1.0, p_rb3 / 0.85), 3))

    # Realistic Ground Earthquake Seismic Wave Ripple (originating from each impact)
    def get_ground_earthquake(bx, by):
        dy_quake = 0.0
        for (t_hit, pos) in [(4.2, t1_pos), (6.0, t2_pos), (7.6, t3_pos)]:
            if t_hit <= t < t_hit + 1.8:
                dt = t - t_hit
                dist = math.hypot(bx - pos[0], by - pos[1])
                wave_front = dt * 85.0
                if abs(dist - wave_front) < 35.0:
                    atten = max(0.0, 1.0 - dt / 1.8) * max(0.0, 1.0 - abs(dist - wave_front) / 35.0)
                    dy_quake += math.sin((dist - wave_front) * 0.28) * 3.8 * atten
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
            if 4.0 <= t < 4.4:
                bx += math.sin((t - 4.0) * 50) * 2.2
            if 8.8 <= t < 10.4:
                rebuild_glow = True
        elif idx == target2_idx:
            h = t2_h
            tilt_x = t2_tilt
            if 5.8 <= t < 6.2:
                bx += math.sin((t - 5.8) * 50) * 2.2
            if 9.8 <= t < 11.4:
                rebuild_glow = True
        elif idx == target3_idx:
            h = t3_h
            tilt_x = t3_tilt
            if 7.4 <= t < 7.8:
                bx += math.sin((t - 7.4) * 50) * 2.2
            if 10.8 <= t < 12.4:
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
        
        # Windows with ascending re-illumination
        if h >= 22 and lv >= 1:
            show_win = True
            reboot_floor_limit = 999
            if idx == target1_idx:
                if 4.2 <= t < 9.6:
                    show_win = False
                elif 9.6 <= t < 10.6:
                    reboot_floor_limit = int(((t - 9.6) / 1.0) * 12)
            elif idx == target2_idx:
                if 6.0 <= t < 10.6:
                    show_win = False
                elif 10.6 <= t < 11.6:
                    reboot_floor_limit = int(((t - 10.6) / 1.0) * 14)
            elif idx == target3_idx:
                if 7.6 <= t < 11.6:
                    show_win = False
                elif 11.6 <= t < 12.6:
                    reboot_floor_limit = int(((t - 11.6) / 1.0) * 16)
            
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

    # Explosions & Debris chunks for Target 1, 2, and 3 (Clean volumetric blast, NO black wireframe circles!)
    for (t_exp, exp_pos, orig_height) in [(4.2, t1_pos, t1_orig_h), (6.0, t2_pos, t2_orig_h), (7.6, t3_pos, t3_orig_h)]:
        if t_exp <= t < t_exp + 1.2:
            dt_e = t - t_exp
            cex = (exp_pos[0] + BW / 2) * SCALE
            cey = (exp_pos[1] - orig_height * 0.55) * SCALE
            
            # 1. Radiant Fireball (white -> yellow -> orange)
            if dt_e < 0.35:
                fb_p = dt_e / 0.35
                fb_r = (24 * (1.0 - fb_p) + 8) * SCALE
                draw.ellipse([cex - fb_r, cey - fb_r, cex + fb_r, cey + fb_r], fill=(255, 120, 20))
                draw.ellipse([cex - fb_r*0.7, cey - fb_r*0.7, cex + fb_r*0.7, cey + fb_r*0.7], fill=(255, 210, 60))
                draw.ellipse([cex - fb_r*0.35, cey - fb_r*0.35, cex + fb_r*0.35, cey + fb_r*0.35], fill=(255, 255, 255))
            
            # 2. Tumbling Voxel Debris Fragments
            for p_i in range(14):
                ang = (p_i / 14.0) * math.pi * 2 + 0.15
                spd = 20.0 + (p_i % 4) * 7.0
                px = cex + math.cos(ang) * spd * dt_e * SCALE
                py = cey + math.sin(ang) * spd * dt_e * 0.7 * SCALE + (0.5 * 85.0 * dt_e * dt_e * SCALE)
                sz = max(1, int((3.2 - dt_e * 1.8) * SCALE))
                c_chunk = (42, 50, 58) if p_i % 2 == 0 else (38, 166, 65)
                draw.rectangle([px, py, px + sz, py + sz], fill=c_chunk)

    # Clean Isometric Holographic Rebuilding Matrix (NO flat lines sticking out!)
    for (t_rb, pos_rb, h_curr, h_max) in [(8.8, t1_pos, t1_h, t1_orig_h), (9.8, t2_pos, t2_h, t2_orig_h), (10.8, t3_pos, t3_h, t3_orig_h)]:
        if t_rb <= t < t_rb + 1.6 and h_curr < h_max - 2.0:
            rx = pos_rb[0] * SCALE
            ry = pos_rb[1] * SCALE
            rh = h_curr * SCALE
            rBW = BW * SCALE
            rOX = OX * SCALE
            rOY = OY * SCALE
            
            # Exact isometric top diamond cap
            cap_pts = [
                (rx, ry - rh),
                (rx + rBW, ry - rh),
                (rx + rBW + rOX, ry - rh - rOY),
                (rx + rOX, ry - rh - rOY)
            ]
            draw.polygon(cap_pts, outline=(126, 231, 135), width=int(1.5 * SCALE))
            draw.line([(rx, ry - rh), (rx + rBW + rOX, ry - rh - rOY)], fill=(180, 255, 200), width=int(SCALE))
            
            # Vertical cyber guide-lines on the 3 building edges
            draw.line([(rx, ry), (rx, ry - rh)], fill=(57, 211, 83), width=int(1.2 * SCALE))
            draw.line([(rx + rBW, ry), (rx + rBW, ry - rh)], fill=(126, 231, 135), width=int(1.2 * SCALE))
            draw.line([(rx + rBW + rOX, ry - rOY), (rx + rBW + rOX, ry - rh - rOY)], fill=(57, 211, 83), width=int(1.2 * SCALE))
            
            # Upward cyber voxel reconstruction particles (strictly inside building footprint)
            for m_i in range(4):
                sp_x = rx + ((m_i * 6 + int(t * 18)) % int(rBW + rOX - 2 * SCALE))
                sp_y = (ry - rh) - ((m_i * 7 + int(t * 22)) % int(14 * SCALE))
                sp_sz = int(1.4 * SCALE)
                draw.rectangle([sp_x, sp_y, sp_x + sp_sz, sp_y + sp_sz], fill=(126, 231, 135))

    # Slower, majestic tactical flight movement
    heli_vis = True
    hx, hy = -200, 84
    tilt = 0.0
    gun_target = None
    gun_firing = False
    active_rockets = []
    rotor_angle = t * 38.0
    
    if t < 1.0:
        heli_vis = False
    elif 1.0 <= t < 3.8:
        p_in = (t - 1.0) / 2.8
        hx = -90 + 300 * (1.0 - math.pow(1.0 - p_in, 2))
        hy = 82 + math.sin(p_in * math.pi) * 6
        tilt = -4.5 * (1.0 - p_in * 0.5)
    elif 3.8 <= t < 4.4:
        hx = 210 + math.sin(t * 20) * 0.8
        hy = 84
        tilt = -2.5
    elif 4.4 <= t < 5.6:
        p_m1 = (t - 4.4) / 1.2
        hx = 210 + 100 * p_m1
        hy = 84 + math.sin(p_m1 * math.pi) * 4
        tilt = -3.0
    elif 5.6 <= t < 6.2:
        hx = 310 + math.sin(t * 20) * 0.8
        hy = 87
        tilt = -2.0
    elif 6.2 <= t < 7.2:
        p_m2 = (t - 6.2) / 1.0
        hx = 310 + 80 * p_m2
        hy = 87 + math.sin(p_m2 * math.pi) * 3
        tilt = -2.5
    elif 7.2 <= t < 7.8:
        hx = 390 + math.sin(t * 20) * 0.8
        hy = 90
        tilt = -2.0
    elif 7.8 <= t < 8.8:
        hx = 390 + math.sin(t * 3.0) * 2.0
        hy = 90 + math.sin(t * 2.5) * 1.5
        tilt = -1.0
    elif 8.8 <= t < 12.8:
        p_dep = (t - 8.8) / 4.0
        hx = 390 + 520 * (0.6 * p_dep + 0.4 * p_dep * p_dep)
        hy = 90 - 30 * p_dep
        tilt = -5.5
    else:
        heli_vis = False

    # Weapons Engagement: Chain Gun Tracers & Rocket Salvos
    # Strike 1: Target 1
    if 3.5 <= t < 4.0:
        gun_firing = True
        gun_target = (t1_pos[0] + BW/2, t1_pos[1] - t1_orig_h * 0.7)
    if 3.8 <= t < 4.2:
        active_rockets.append({
            'start': (hx + 65, hy + 22),
            'target': (t1_pos[0] + BW/2, t1_pos[1] - t1_orig_h * 0.7),
            'p': (t - 3.8) / 0.4
        })

    # Strike 2: Target 2
    if 5.3 <= t < 5.8:
        gun_firing = True
        gun_target = (t2_pos[0] + BW/2, t2_pos[1] - t2_orig_h * 0.7)
    if 5.6 <= t < 6.0:
        active_rockets.append({
            'start': (hx + 65, hy + 22),
            'target': (t2_pos[0] + BW/2, t2_pos[1] - t2_orig_h * 0.7),
            'p': (t - 5.6) / 0.4
        })

    # Strike 3: Target 3
    if 6.9 <= t < 7.4:
        gun_firing = True
        gun_target = (t3_pos[0] + BW/2, t3_pos[1] - t3_orig_h * 0.7)
    if 7.2 <= t < 7.6:
        active_rockets.append({
            'start': (hx + 65, hy + 22),
            'target': (t3_pos[0] + BW/2, t3_pos[1] - t3_orig_h * 0.7),
            'p': (t - 7.2) / 0.4
        })

    # Render 30mm Tracer Bullet Streams
    if gun_firing and gun_target and heli_vis:
        rad_h = math.radians(tilt)
        cos_h, sin_h = math.cos(rad_h), math.sin(rad_h)
        gx_off = (84 - 6 - 42) * cos_h - (30 - 17) * sin_h
        gy_off = (84 - 6 - 42) * sin_h + (30 - 17) * cos_h
        gun_tip_x = (hx + 42 + gx_off) * SCALE
        gun_tip_y = (hy + 17 + gy_off) * SCALE
        gt_x = gun_target[0] * SCALE
        gt_y = gun_target[1] * SCALE
        
        # 3 glowing tracer streaks flying along ballistic vector
        dx_g = gt_x - gun_tip_x
        dy_g = gt_y - gun_tip_y
        dist_g = math.hypot(dx_g, dy_g)
        if dist_g > 1:
            ugx, ugy = dx_g / dist_g, dy_g / dist_g
            for tr_i in range(3):
                tr_prog = ((t * 18.0 + tr_i * 0.33) % 1.0)
                tr_x = gun_tip_x + dx_g * tr_prog
                tr_y = gun_tip_y + dy_g * tr_prog
                tr_len = 16 * SCALE
                draw.line([(tr_x - ugx * tr_len, tr_y - ugy * tr_len), (tr_x, tr_y)], fill=(57, 211, 83), width=int(2.2 * SCALE))
                draw.line([(tr_x - ugx * tr_len * 0.5, tr_y - ugy * tr_len * 0.5), (tr_x, tr_y)], fill=(255, 255, 255), width=int(1.2 * SCALE))
            # Facade impact sparks
            draw.ellipse([gt_x - 3*SCALE, gt_y - 3*SCALE, gt_x + 3*SCALE, gt_y + 3*SCALE], fill=(126, 231, 135))

    # Render Guided Rockets with Expanding Billowing Smoke
    for rkt in active_rockets:
        mp = rkt['p']
        r_start = (rkt['start'][0] * SCALE, rkt['start'][1] * SCALE)
        r_tgt = (rkt['target'][0] * SCALE, rkt['target'][1] * SCALE)
        rx_now = r_start[0] + (r_tgt[0] - r_start[0]) * mp
        ry_now = r_start[1] + (r_tgt[1] - r_start[1]) * mp
        
        dx_r = r_tgt[0] - r_start[0]
        dy_r = r_tgt[1] - r_start[1]
        dist_r = math.hypot(dx_r, dy_r)
        if dist_r > 1:
            urx, ury = dx_r / dist_r, dy_r / dist_r
            # Expanding multi-layer smoke trail
            for s_i in range(7):
                sm_x = rx_now - urx * (s_i * 4.0 * SCALE)
                sm_y = ry_now - ury * (s_i * 4.0 * SCALE)
                sm_r = (2.2 + s_i * 0.9) * SCALE
                if s_i < 2:
                    c_smoke = (255, 210, 80)
                elif s_i < 4:
                    c_smoke = (160, 170, 180)
                else:
                    c_smoke = (70, 80, 90)
                draw.ellipse([sm_x - sm_r, sm_y - sm_r * 0.6, sm_x + sm_r, sm_y + sm_r * 0.6], fill=c_smoke)
            
            # Rocket needle body + fins
            draw.line([(rx_now - urx * 7 * SCALE, ry_now - ury * 7 * SCALE), (rx_now, ry_now)], fill=(45, 52, 60), width=int(2.4 * SCALE))
            draw.ellipse([rx_now - 2*SCALE, ry_now - 2*SCALE, rx_now + 2*SCALE, ry_now + 2*SCALE], fill=(57, 211, 83))
            # Rocket motor flame
            draw.ellipse([rx_now - urx*8*SCALE - SCALE, ry_now - ury*8*SCALE - SCALE, rx_now - urx*8*SCALE + SCALE, ry_now - ury*8*SCALE + SCALE], fill=(255, 255, 255))

    if heli_vis:
        draw_realistic_apache(draw, hx, hy, tilt_deg=tilt, rotor_angle=rotor_angle, muzzle_flash=gun_firing, missile_fire=(len(active_rockets) > 0), scale=SCALE)

    # MODERN GLASSMORPHIC "BEST DAY" HUD BADGE WITH ANIMATED RADAR BEACON
    b_x = best_x * SCALE
    b_y = best_y * SCALE
    
    beacon_pulse = (math.sin(t * 6.0) + 1.0) * 0.5
    r_ping = (4.0 + beacon_pulse * 12.0) * SCALE
    pink_alpha = int(255 * (1.0 - beacon_pulse))
    draw.ellipse([b_x - r_ping, b_y - r_ping, b_x + r_ping, b_y + r_ping], outline=(255, 93, 115, pink_alpha), width=int(1.2 * SCALE))
    draw.ellipse([b_x - 3.5*SCALE, b_y - 3.5*SCALE, b_x + 3.5*SCALE, b_y + 3.5*SCALE], fill=(255, 93, 115))
    draw.ellipse([b_x - 1.5*SCALE, b_y - 1.5*SCALE, b_x + 1.5*SCALE, b_y + 1.5*SCALE], fill=(255, 255, 255))
    
    line1 = "BEST DAY RECORD"
    line2 = f"{best_date_str} · Peak Activity"
    
    bbox1 = draw.textbbox((0, 0), line1, font=FONT_SMALL)
    bbox2 = draw.textbbox((0, 0), line2, font=FONT_SMALL)
    text_w = max(bbox1[2] - bbox1[0], bbox2[2] - bbox2[0])
    
    cnt_str = str(best_count)
    bbox_cnt = draw.textbbox((0, 0), cnt_str, font=FONT_BOLD)
    cnt_w = bbox_cnt[2] - bbox_cnt[0]
    pill_w = max(46 * SCALE, int(24 * SCALE + cnt_w + 10 * SCALE))

    # Ample margins so text never clips or crashes into borders
    badge_w = int(pill_w + 14 * SCALE + text_w + 22 * SCALE)
    badge_h = int(36 * SCALE)
    card_x = int(b_x - 18 * SCALE - badge_w)
    if card_x < 10 * SCALE:
        card_x = int(b_x + 18 * SCALE)
    card_y = int(18 * SCALE)
    
    # Leader line connecting cleanly to card edge
    lead_connect_x = card_x + badge_w if card_x < b_x else card_x
    draw.line([(b_x, b_y), (b_x, card_y + badge_h // 2), (lead_connect_x, card_y + badge_h // 2)], fill=(255, 93, 115), width=int(1.5 * SCALE))
    draw.ellipse([(b_x - 2*SCALE), (card_y + badge_h // 2 - 2*SCALE), (b_x + 2*SCALE), (card_y + badge_h // 2 + 2*SCALE)], fill=(255, 93, 115))
    
    badge_rect = [card_x, card_y, card_x + badge_w, card_y + badge_h]
    draw.rounded_rectangle(badge_rect, radius=6*SCALE, fill=(22, 27, 34), outline=(255, 93, 115), width=int(1.2*SCALE))
    
    # Left pill with gold star
    draw.rounded_rectangle([card_x + 6*SCALE, card_y + 6*SCALE, card_x + 6*SCALE + pill_w, card_y + badge_h - 6*SCALE], radius=4*SCALE, fill=(255, 93, 115))
    # Draw geometric star
    st_cx = card_x + 14 * SCALE
    st_cy = card_y + badge_h // 2
    draw.polygon([
        (st_cx, st_cy - 4*SCALE), (st_cx + 1.2*SCALE, st_cy - 1.2*SCALE),
        (st_cx + 4*SCALE, st_cy - 1.2*SCALE), (st_cx + 1.8*SCALE, st_cy + 1.0*SCALE),
        (st_cx + 2.6*SCALE, st_cy + 4*SCALE), (st_cx, st_cy + 2.0*SCALE),
        (st_cx - 2.6*SCALE, st_cy + 4*SCALE), (st_cx - 1.8*SCALE, st_cy + 1.0*SCALE),
        (st_cx - 4*SCALE, st_cy - 1.2*SCALE), (st_cx - 1.2*SCALE, st_cy - 1.2*SCALE)
    ], fill=(255, 230, 100))
    draw.text((card_x + 22*SCALE, card_y + 11*SCALE), cnt_str, fill=(255, 255, 255), font=FONT_BOLD)
    
    text_x = card_x + 6*SCALE + pill_w + 8*SCALE
    draw.text((text_x, card_y + 6*SCALE), line1, fill=(126, 231, 135), font=FONT_SMALL)
    draw.text((text_x, card_y + 19*SCALE), line2, fill=(230, 237, 243), font=FONT_SMALL)

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
        elif (bx == t1_pos[0] and by == t1_pos[1]) or (bx == t2_pos[0] and by == t2_pos[1]) or (bx == t3_pos[0] and by == t3_pos[1]):
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

    # Modern Best Day HUD Badge in SVG (248px width ensures ample clearance)
    badge_w = 248
    card_x = int(best_x - 18 - badge_w)
    if card_x < 10:
        card_x = int(best_x + 18)
    card_y = 18
    
    lead_connect_x = card_x + badge_w if card_x < best_x else card_x
    badge_svg = f'''
    <!-- Best Day HUD Badge -->
    <g class="best-day-badge">
      <circle class="beacon-pulse" cx="{best_x}" cy="{best_y}" r="4" fill="none" stroke="#ff5d73" stroke-width="1.2"/>
      <circle cx="{best_x}" cy="{best_y}" r="3.5" fill="#ff5d73"/>
      <circle cx="{best_x}" cy="{best_y}" r="1.5" fill="#ffffff"/>
      <path d="M{best_x} {best_y} V{card_y + 18} L{lead_connect_x} {card_y + 18}" fill="none" stroke="#ff5d73" stroke-width="1.5"/>
      <circle cx="{best_x}" cy="{card_y + 18}" r="2" fill="#ff5d73"/>
      <!-- Glassmorphic Card -->
      <rect x="{card_x}" y="{card_y}" width="{badge_w}" height="36" rx="6" fill="#161b22" stroke="#ff5d73" stroke-width="1.2"/>
      <rect x="{card_x + 6}" y="{card_y + 6}" width="44" height="24" rx="4" fill="#ff5d73"/>
      <text x="{card_x + 28}" y="{card_y + 22}" text-anchor="middle" font-weight="700" font-size="12px" fill="#ffffff">★ {best_count}</text>
      <text x="{card_x + 58}" y="{card_y + 17}" font-size="10px" font-weight="600" fill="#7ee787">BEST DAY RECORD</text>
      <text x="{card_x + 58}" y="{card_y + 29}" font-size="9px" fill="#e6edf3">{best_date_str} · Peak Activity</text>
    </g>
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

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution skyline: {total_contributions} contributions in {latest_year}">
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

# 2. Render optimized frames for fast-loading skyline.gif
TOTAL_DURATION = 14.0 # seconds
FPS = 8
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)
DT = TOTAL_DURATION / TOTAL_FRAMES

print(f"Generating {TOTAL_FRAMES} frames at {FPS} FPS (total duration: {TOTAL_DURATION}s)...")
start_time = time.time()
rgb_frames = []

for i in range(TOTAL_FRAMES):
    t_val = i * DT
    f_img = render_enhanced_frame(t_val)
    rgb_frames.append(f_img)
    if (i + 1) % 20 == 0 or i == TOTAL_FRAMES - 1:
        print(f"Rendered {i+1}/{TOTAL_FRAMES} frames ({((i+1)/TOTAL_FRAMES)*100:.1f}%)")

# Build a single global master palette from an explosion + helicopter action frame (t=4.25s)
ref_frame = render_enhanced_frame(4.25)
master_pal_img = ref_frame.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

# Quantize all frames with Dither.NONE so static buildings have 100% identical pixels across frames
frames = [
    f.quantize(palette=master_pal_img, dither=Image.Dither.NONE)
    for f in rgb_frames
]

print(f"Render completed in {time.time() - start_time:.1f}s. Saving optimized skyline.gif...")
frames[0].save(
    "skyline.gif",
    save_all=True,
    append_images=frames[1:],
    duration=int(1000 / FPS),
    loop=0,
    optimize=True
)

gif_size = os.path.getsize("skyline.gif")
print(f"skyline.gif generated successfully! Size: {gif_size / 1024:.1f} KB")


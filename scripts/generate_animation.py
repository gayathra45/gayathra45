import os, sys, re, math, time
from PIL import Image, ImageDraw, ImageFont

W, H = 804, 310
SCALE = 2
W_2X, H_2X = W * SCALE, H * SCALE
BG_COLOR = (13, 17, 23) # #0d1117 (GitHub Dark theme)

LEVEL_COLORS = {
    0: {"f": "#ebedf0", "t": "#f2f3f5", "s": "#b7b9bb"},
    1: {"f": "#9be9a8", "t": "#bef1c6", "s": "#79b683"},
    2: {"f": "#40c463", "t": "#83d99a", "s": "#32994d"},
    3: {"f": "#30a14e", "t": "#78c28c", "s": "#257e3d"},
    4: {"f": "#216e39", "t": "#6fa17e", "s": "#1a562c"},
}

WINDOW_GREENS = [
    (14, 68, 41),    # #0E4429
    (0, 109, 50),    # #006D32
    (38, 166, 65),   # #26A641
    (57, 211, 83),   # #39D353
    (126, 231, 135), # Neon accent
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
for f_path in font_candidates:
    if os.path.exists(f_path):
        try:
            if not FONT:
                FONT = ImageFont.truetype(f_path, 15 * SCALE)
            if "b" in os.path.basename(f_path).lower() or "bold" in os.path.basename(f_path).lower():
                FONT_BOLD = ImageFont.truetype(f_path, 15 * SCALE)
        except Exception:
            pass

if not FONT:
    FONT = ImageFont.load_default()
if not FONT_BOLD:
    FONT_BOLD = FONT

# Load boxes from skyline.svg (or preserve raw shapes)
svg_path = 'skyline.svg'
with open(svg_path, 'r', encoding='utf-8') as f:
    svg_text = f.read()

pattern = r'<g transform="translate\((\d+) (\d+)\)"><g class="[^"]*"[^>]*><polygon class="l(\d) f" points="0,([-\d\.]+) 11,[-\d\.]+ 11,0 0,0"/>[\s\S]*?<title>(.*?): (\d+)</title>'
raw_boxes = re.findall(pattern, svg_text)

BW = 11
OX = 5
OY = 4

boxes = []
target_idx = -1
for idx, b in enumerate(raw_boxes):
    bx, by = int(b[0]), int(b[1])
    h = -float(b[3])
    if bx == 526 and by == 246:
        target_idx = idx
    boxes.append({
        'x': bx,
        'y': by,
        'lv': int(b[2]),
        'h': h,
        'date': b[4],
        'count': int(b[5]),
    })

if target_idx == -1:
    target_idx = len(boxes) // 2

orig_target_h = boxes[target_idx]['h']
total_contributions = sum(b['count'] for b in boxes)

print(f"Loaded {len(boxes)} buildings. Target tower: idx={target_idx}, pos=({boxes[target_idx]['x']}, {boxes[target_idx]['y']}), h={orig_target_h:.1f}")

def draw_apache_right(draw, x, y, tilt_deg=0, rotor_angle=0, muzzle_flash=False, scale=SCALE):
    rad = math.radians(tilt_deg)
    cos_t, sin_t = math.cos(rad), math.sin(rad)
    cx, cy = 40, 16
    
    def pt(px, py):
        mx = 80 - px
        dx, dy = mx - cx, py - cy
        rx = dx * cos_t - dy * sin_t
        ry = dx * sin_t + dy * cos_t
        return ((x + cx + rx) * scale, (y + cy + ry) * scale)
    
    c_dark = (18, 22, 28)
    c_armor = (52, 60, 70)
    c_highlight = (95, 105, 118)
    c_glass = (57, 211, 83)
    c_glass_bg = (14, 68, 41)
    
    # 1. Tail boom & empennage
    draw.polygon([pt(38, 16), pt(72, 14), pt(76, 10), pt(78, 10), pt(74, 18), pt(38, 20)], fill=c_armor, outline=c_dark)
    draw.polygon([pt(70, 16), pt(75, 4), pt(79, 4), pt(76, 18), pt(72, 18)], fill=c_highlight, outline=c_dark)
    draw.polygon([pt(64, 17), pt(72, 16), pt(73, 18), pt(63, 19)], fill=c_armor)
    
    # Tail rotor (spinning)
    tr_cx, tr_cy = pt(77, 7)
    tr_len = 8 * scale
    for off in [0, math.pi / 2]:
        a = rotor_angle * 3.5 + off
        draw.line([
            (tr_cx + tr_len * math.cos(a), tr_cy + tr_len * math.sin(a)),
            (tr_cx - tr_len * math.cos(a), tr_cy - tr_len * math.sin(a))
        ], fill=(210, 220, 230), width=max(1, int(1.2 * scale)))
    
    # 2. Main Fuselage core
    draw.polygon([pt(14, 18), pt(24, 12), pt(44, 12), pt(46, 19), pt(40, 24), pt(18, 24), pt(13, 21)], fill=c_armor, outline=c_dark)
    draw.polygon([pt(28, 11), pt(43, 11), pt(45, 17), pt(28, 17)], fill=c_dark, outline=c_highlight)
    
    # 3. Tandem Cockpit Canopies (stepped)
    draw.polygon([pt(15, 18), pt(19, 14), pt(26, 14), pt(24, 19), pt(16, 19)], fill=c_glass_bg, outline=c_glass)
    draw.polygon([pt(25, 17), pt(27, 13), pt(34, 13), pt(33, 18), pt(26, 18)], fill=c_glass_bg, outline=c_glass)
    draw.line([pt(18, 15), pt(24, 15)], fill=(126, 231, 135), width=max(1, int(scale)))
    draw.line([pt(27, 14), pt(32, 14)], fill=(126, 231, 135), width=max(1, int(scale)))
    
    # 4. TADS/PNVS Nose turret ball
    t_center = pt(10, 18)
    t_r = 3 * scale
    draw.ellipse([t_center[0] - t_r, t_center[1] - t_r, t_center[0] + t_r, t_center[1] + t_r], fill=c_dark, outline=c_glass)
    draw.ellipse([t_center[0] - t_r*0.4, t_center[1] - t_r*0.4, t_center[0] + t_r*0.4, t_center[1] + t_r*0.4], fill=c_glass)
    
    # 5. 30mm Chin Gun
    g_start = pt(18, 24)
    g_end = pt(7, 28)
    draw.line([g_start, g_end], fill=c_dark, width=int(2.5 * scale))
    draw.line([pt(13, 26), g_end], fill=c_highlight, width=int(1.5 * scale))
    
    # Muzzle flash
    if muzzle_flash:
        fx, fy = g_end
        f_size = 9 * scale
        flash_pts = [
            (fx, fy),
            (fx + f_size, fy + f_size * 0.4),
            (fx + f_size * 0.4, fy + f_size * 0.6),
            (fx + f_size * 1.3, fy + f_size * 0.8),
            (fx + f_size * 0.5, fy + f_size),
            (fx + f_size * 0.8, fy + f_size * 1.4),
            (fx, fy + f_size * 0.5)
        ]
        draw.polygon(flash_pts, fill=(57, 211, 83))
        draw.ellipse([fx - 3*scale, fy - 3*scale, fx + 5*scale, fy + 5*scale], fill=(255, 255, 255))
    
    # 6. Stub Wings & Weapons
    draw.polygon([pt(26, 19), pt(34, 19), pt(35, 22), pt(25, 22)], fill=c_highlight)
    r1, r2 = pt(26, 22), pt(33, 25)
    draw.rectangle([min(r1[0], r2[0]), min(r1[1], r2[1]), max(r1[0], r2[0]), max(r1[1], r2[1])], fill=c_dark, outline=c_glass)
    
    # 7. Landing gear
    draw.line([pt(24, 23), pt(21, 28)], fill=c_dark, width=int(1.8 * scale))
    w_c = pt(21, 28)
    draw.ellipse([w_c[0] - 2*scale, w_c[1] - 2*scale, w_c[0] + 2*scale, w_c[1] + 2*scale], fill=(10, 10, 10), outline=c_armor)
    tg_c = pt(71, 19)
    draw.ellipse([tg_c[0] - 1.2*scale, tg_c[1] - 1.2*scale, tg_c[0] + 1.2*scale, tg_c[1] + 1.2*scale], fill=(10, 10, 10))
    
    # 8. Main Rotor Mast & Longbow Radome
    draw.line([pt(33, 12), pt(33, 6)], fill=c_dark, width=int(2.2 * scale))
    rad_c = pt(33, 5)
    draw.ellipse([rad_c[0] - 6*scale, rad_c[1] - 3*scale, rad_c[0] + 6*scale, rad_c[1] + 3*scale], fill=c_armor, outline=c_highlight)
    
    # Main Rotor Blades
    hub_c = pt(33, 7)
    draw.ellipse([hub_c[0] - 44*scale, hub_c[1] - 4*scale, hub_c[0] + 44*scale, hub_c[1] + 4*scale], outline=(200, 220, 230, 80), width=int(scale))
    b_len = 42 * scale
    for b_off in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
        angle = rotor_angle + b_off
        bx = hub_c[0] + b_len * math.cos(angle)
        by = hub_c[1] + b_len * 0.16 * math.sin(angle)
        draw.line([hub_c, (bx, by)], fill=(195, 205, 215), width=int(2 * scale))
        draw.line([(bx - 3*scale * math.cos(angle), by - 3*scale * 0.16 * math.sin(angle)), (bx, by)], fill=(57, 211, 83), width=int(2 * scale))

def generate_frame(t):
    img_2x = Image.new('RGB', (W_2X, H_2X), BG_COLOR)
    draw = ImageDraw.Draw(img_2x)
    
    current_target_h = orig_target_h
    shake_dx, shake_dy = 0, 0
    adj_shake_dx = 0
    rebuilding_glow = False
    tilt_collapse_dx = 0
    
    # Phase timing breakdown (Total 14.0s):
    # Phase 1: 0.0 - 2.0s  Normal City
    # Phase 2: 2.0 - 4.6s  Helicopter Arrival & Flight
    # Phase 3: 4.6 - 5.5s  Target Acquisition & Hover (Laser designator sweep)
    # Phase 4: 5.5 - 6.6s  Firing Sequence (3 bursts)
    # Phase 5: 6.2 - 7.5s  Impact & Building Shake
    # Phase 6: 7.5 - 8.6s  Destruction (Structure tilts and collapses, dust, debris)
    # Phase 7: 8.6 - 10.6s Helicopter Departure
    # Phase 8: 10.6 - 12.6s Automatic Rebuilding (Ground hologram, rising structure, sequential window lights)
    # Phase 9: 12.6 - 14.0s Reset & Rest (City pristine)
    
    if 6.2 <= t < 7.5:
        shake_intensity = 3.2 * (1.0 - (t - 6.2) / 1.3)
        shake_dx = math.sin(t * 45) * shake_intensity
        shake_dy = math.cos(t * 38) * shake_intensity * 0.6
        adj_shake_dx = math.sin(t * 32) * shake_intensity * 0.4
    elif 7.5 <= t < 8.6:
        p = (t - 7.5) / 1.1
        current_target_h = max(2.0, orig_target_h * (1.0 - p * p))
        shake_dx = (math.sin(t * 50) * 1.5) * (1.0 - p)
        tilt_collapse_dx = (p * 4.0) * (1.0 - p)
    elif 8.6 <= t < 10.6:
        current_target_h = 2.0
    elif 10.6 <= t < 12.6:
        p = (t - 10.6) / 2.0
        if p < 0.85:
            current_target_h = 2.0 + (orig_target_h - 2.0) * (1.0 - math.pow(1.0 - (p / 0.85), 3))
        else:
            current_target_h = orig_target_h
        rebuilding_glow = True
    
    # Draw skyline boxes
    for idx, b in enumerate(boxes):
        x = b['x']
        y = b['y']
        lv = b['lv']
        h = b['h']
        
        top_offset_x = 0
        if idx == target_idx:
            x += shake_dx
            y += shake_dy
            h = current_target_h
            top_offset_x = tilt_collapse_dx
        elif abs(b['x'] - 526) <= 15 and abs(b['y'] - 246) <= 15 and (6.2 <= t < 7.5):
            x += adj_shake_dx
        
        cols = LEVEL_COLORS[lv]
        f_col = hex_to_rgb(cols["f"])
        t_col = hex_to_rgb(cols["t"])
        s_col = hex_to_rgb(cols["s"])
        
        if idx == target_idx and rebuilding_glow:
            f_col = (max(f_col[0], 20), min(255, f_col[1] + 60), max(f_col[2], 50))
            t_col = (max(t_col[0], 50), min(255, t_col[1] + 80), max(t_col[2], 80))
            s_col = (max(s_col[0], 15), min(255, s_col[1] + 45), max(s_col[2], 40))
        
        sx = x * SCALE
        sy = y * SCALE
        sh = h * SCALE
        sBW = BW * SCALE
        sOX = OX * SCALE
        sOY = OY * SCALE
        tox = top_offset_x * SCALE
        
        front_pts = [(sx + tox, sy - sh), (sx + sBW + tox, sy - sh), (sx + sBW, sy), (sx, sy)]
        top_pts = [(sx + tox, sy - sh), (sx + sBW + tox, sy - sh), (sx + sBW + sOX + tox, sy - sh - sOY), (sx + sOX + tox, sy - sh - sOY)]
        side_pts = [(sx + sBW + tox, sy - sh), (sx + sBW + sOX + tox, sy - sh - sOY), (sx + sBW + sOX, sy - sOY), (sx + sBW, sy)]
        
        draw.polygon(front_pts, fill=f_col)
        draw.polygon(top_pts, fill=t_col)
        draw.polygon(side_pts, fill=s_col)
        
        # Windows
        if h >= 24 and lv >= 1:
            show_windows = True
            reboot_max_floor = 999
            if idx == target_idx:
                if 6.2 <= t < 12.0:
                    show_windows = False
                elif 12.0 <= t < 12.8:
                    show_windows = True
                    p_reboot = (t - 12.0) / 0.8
                    reboot_max_floor = int(p_reboot * 14)
            
            if show_windows:
                num_floors = int((h - 8) // 8)
                for floor in range(max(1, num_floors)):
                    floor_y = sy - sh + (8 + floor * 8) * SCALE
                    if floor_y >= sy - 4 * SCALE:
                        break
                    
                    if idx == target_idx and (num_floors - floor) > reboot_max_floor:
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

    # Debris particles during collapse (t: 7.2 to 8.8)
    if 7.2 <= t < 8.8:
        dt = t - 7.2
        cex = (526 + BW / 2) * SCALE
        cey = (246 - orig_target_h * 0.6) * SCALE
        num_particles = 18
        for p_i in range(num_particles):
            angle = (p_i / num_particles) * math.pi * 2 + 0.3
            speed = 20.0 + (p_i % 5) * 9.0
            px = cex + math.cos(angle) * speed * dt * SCALE + (math.sin(p_i) * 6 * SCALE)
            py = cey + math.sin(angle) * speed * dt * 0.7 * SCALE + (0.5 * 85.0 * dt * dt * SCALE)
            p_size = (3 - int(dt * 1.5)) * SCALE
            if p_size > 0:
                p_col = WINDOW_GREENS[p_i % len(WINDOW_GREENS)] if p_i % 2 == 0 else (52, 60, 70)
                draw.rectangle([px, py, px + p_size, py + p_size], fill=p_col)

    # Dust cloud puffs during collapse (t: 7.5 to 8.8)
    if 7.5 <= t < 8.8:
        dt_dust = t - 7.5
        dust_alpha = max(0.0, 1.0 - dt_dust / 1.3)
        dust_cx = 526 * SCALE
        dust_cy = 246 * SCALE
        for d_i in range(5):
            d_x = dust_cx + (d_i - 2) * 10 * SCALE
            d_y = dust_cy - 4 * SCALE
            d_rad = (6 + dt_dust * 14 + d_i * 2) * SCALE
            d_col = (int(50 * dust_alpha), int(60 * dust_alpha), int(70 * dust_alpha))
            draw.ellipse([d_x - d_rad, d_y - d_rad * 0.4, d_x + d_rad, d_y + d_rad * 0.4], outline=d_col, width=int(1.5 * SCALE))

    # Rebuilding holographic grid lines (t: 10.6 to 12.3)
    if 10.6 <= t < 12.3:
        rb_t = t - 10.6
        scan_y = (246 - current_target_h) * SCALE
        draw.line([(526 - 12) * SCALE, scan_y, (526 + BW + OX + 12) * SCALE, scan_y], fill=(57, 211, 83), width=int(1.8 * SCALE))
        draw.line([(526 - 6) * SCALE, scan_y - 3*SCALE, (526 + BW + OX + 6) * SCALE, scan_y - 3*SCALE], fill=(126, 231, 135), width=int(SCALE))
        g_rad = (8 + math.sin(rb_t * 8) * 4) * SCALE
        draw.ellipse([(526 + BW/2) * SCALE - g_rad, 246 * SCALE - g_rad*0.3, (526 + BW/2) * SCALE + g_rad, 246 * SCALE + g_rad*0.3], outline=(57, 211, 83), width=int(SCALE))

    # Apache Helicopter Kinematics:
    heli_visible = True
    hx, hy = -200, 95
    tilt = 0.0
    is_firing = False
    rotor_ang = t * 35.0
    
    if t < 2.0:
        heli_visible = False
    elif 2.0 <= t < 4.6:
        p = (t - 2.0) / 2.6
        hx = -90 + 480 * (1.0 - math.pow(1.0 - p, 2))
        hy = 85 + math.sin(p * math.pi) * 8
        tilt = -6.0 * (1.0 - p)
    elif 4.6 <= t < 5.5:
        hx = 390 + math.sin(t * 4.0) * 2.0
        hy = 95 + math.sin(t * 3.0) * 1.5
        tilt = math.sin(t * 3.5) * 1.5
        laser_start = ((hx + 75) * SCALE, (hy + 18) * SCALE)
        laser_target = ((526 + BW/2) * SCALE, (246 - orig_target_h * 0.7) * SCALE)
        draw.line([laser_start, laser_target], fill=(57, 211, 83), width=int(SCALE))
        draw.ellipse([laser_target[0] - 4*SCALE, laser_target[1] - 4*SCALE, laser_target[0] + 4*SCALE, laser_target[1] + 4*SCALE], outline=(57, 211, 83), width=int(SCALE))
    elif 5.5 <= t < 6.6:
        hx = 390 + math.sin(t * 50) * 0.8
        hy = 95 + math.cos(t * 45) * 0.8
        tilt = -2.0 + math.sin(t * 35) * 1.8
        if (5.6 <= t < 5.75) or (5.9 <= t < 6.05) or (6.2 <= t < 6.35):
            is_firing = True
    elif 6.6 <= t < 8.6:
        hx = 390 + math.sin(t * 3.0) * 2.5
        hy = 95 + math.sin(t * 2.5) * 1.5
        tilt = -1.0
    elif 8.6 <= t < 10.6:
        p = (t - 8.6) / 2.0
        hx = 390 + 540 * (p * p)
        hy = 95 - 35 * p
        tilt = -8.0
    else:
        heli_visible = False

    # Projectiles
    if 5.6 <= t < 6.6:
        target_pt = ((526 + BW/2) * SCALE, (246 - orig_target_h * 0.7) * SCALE)
        gun_tip = ((hx + 75) * SCALE, (hy + 22) * SCALE)
        for shot_start in [5.6, 5.9, 6.2]:
            if shot_start <= t < shot_start + 0.35:
                proj_p = (t - shot_start) / 0.35
                proj_x = gun_tip[0] + (target_pt[0] - gun_tip[0]) * proj_p
                proj_y = gun_tip[1] + (target_pt[1] - gun_tip[1]) * proj_p
                streak_len = 16 * SCALE
                dx = (target_pt[0] - gun_tip[0])
                dy = (target_pt[1] - gun_tip[1])
                dist = math.hypot(dx, dy)
                ux, uy = dx / dist, dy / dist
                tail_x = proj_x - ux * streak_len
                tail_y = proj_y - uy * streak_len
                draw.line([(tail_x, tail_y), (proj_x, proj_y)], fill=(57, 211, 83), width=int(2.5 * SCALE))
                draw.line([(tail_x + ux*streak_len*0.4, tail_y + uy*streak_len*0.4), (proj_x, proj_y)], fill=(255, 255, 255), width=int(1.2 * SCALE))

    # Impact Flash
    for impact_time in [5.95, 6.25, 6.55]:
        if impact_time <= t < impact_time + 0.2:
            it = (t - impact_time) / 0.2
            imp_x = (526 + BW/2) * SCALE
            imp_y = (246 - orig_target_h * 0.7) * SCALE
            f_r = (14 * (1.0 - it) + 6) * SCALE
            draw.ellipse([imp_x - f_r, imp_y - f_r, imp_x + f_r, imp_y + f_r], fill=(255, 255, 255))
            draw.ellipse([imp_x - f_r*1.5, imp_y - f_r*1.5, imp_x + f_r*1.5, imp_y + f_r*1.5], outline=(57, 211, 83), width=int(2*SCALE))
            for sp_i in range(8):
                sp_ang = (sp_i / 8.0) * math.pi * 2
                sp_len = f_r * 2.2
                draw.line([(imp_x, imp_y), (imp_x + math.cos(sp_ang) * sp_len, imp_y + math.sin(sp_ang) * sp_len)], fill=(126, 231, 135), width=int(SCALE))

    if heli_visible:
        draw_apache_right(draw, hx, hy, tilt_deg=tilt, rotor_angle=rotor_ang, muzzle_flash=is_firing, scale=SCALE)

    # Leader Line & Best Day text
    best_x = (774 + BW / 2 + OX / 2) * SCALE
    best_y = (238 - 140 - OY) * SCALE
    top_y = 30 * SCALE
    hx_lead = best_x - 22 * SCALE
    pink = hex_to_rgb("#ff5d73")
    draw.ellipse([best_x - 3.5*SCALE, best_y - 3.5*SCALE, best_x + 3.5*SCALE, best_y + 3.5*SCALE], fill=pink)
    draw.line([(best_x, best_y), (best_x, top_y), (hx_lead, top_y)], fill=pink, width=int(1.8 * SCALE))
    
    best_label = "Best day · 64 · Nov 1, 2026"
    draw.text((hx_lead - 6 * SCALE, top_y - 8 * SCALE), best_label, fill=(230, 237, 243), font=FONT_BOLD, anchor="rt")
    
    foot_label = f"{total_contributions} contributions in the last year"
    draw.text((16 * SCALE, (H - 24) * SCALE), foot_label, fill=(139, 148, 158), font=FONT)

    final_img = img_2x.resize((W, H), Image.Resampling.LANCZOS)
    return final_img

def build_animated_svg(target_x=526, target_y=246):
    # Generates an advanced pure vector SVG with matching CSS keyframes for browser vector rendering
    FONT_STACK = "'Fira Code',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    
    # Generate building shapes from raw_boxes
    shapes = ""
    for idx, b in enumerate(raw_boxes):
        bx, by = int(b[0]), int(b[1])
        lv = int(b[2])
        h = -float(b[3])
        date = b[4]
        cnt = int(b[5])
        
        # Check if target building
        if bx == target_x and by == target_y:
            # Wrap in target animated group
            shapes += f'<g transform="translate({bx} {by})"><g class="target-tower">'
            shapes += f'<polygon class="l{lv} f" points="0,{-h} {BW},{-h} {BW},0 0,0"/>'
            shapes += f'<polygon class="l{lv} t" points="0,{-h} {BW},{-h} {BW + OX},{-h - OY} {OX},{-h - OY}"/>'
            shapes += f'<polygon class="l{lv} s" points="{BW},{-h} {BW + OX},{-h - OY} {BW + OX},{-OY} {BW},0"/>'
            
            # Windows on target
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
            
            # Static/pulsing windows on tall buildings
            if h >= 24 and lv >= 1:
                w_seed = bx * 31 + by * 17
                if w_seed % 3 == 0:
                    num_floors = int((h - 8) // 8)
                    for floor in range(max(1, num_floors)):
                        floor_y = -h + 8 + floor * 8
                        col_hex = ["#0e4429", "#006d32", "#26a641", "#39d353"][(w_seed + floor) % 4]
                        shapes += f'<rect class="win" x="3" y="{floor_y}" width="4" height="3" fill="{col_hex}"/>'
            
            shapes += f'<title>{date}: {cnt}</title></g></g>'

    # Leader line
    best_x = 774 + BW / 2 + OX / 2
    best_y = 238 - 140 - OY
    top_y = 30
    hx_lead = best_x - 22
    len_leader = int(best_y - top_y + 32)
    shapes += f'<g class="leader"><circle cx="{best_x}" cy="{best_y}" r="3.5" fill="#ff5d73"/>'
    shapes += f'<path d="M{best_x} {best_y} V{top_y} L{hx_lead} {top_y}" fill="none" stroke="#ff5d73" stroke-width="1.6"/>'
    shapes += f'<text x="{hx_lead - 6}" y="{top_y + 5}" text-anchor="end" font-weight="600" fill="#e6edf3">Best day · 64 · Nov 1, 2026</text></g>'
    shapes += f'<text class="foot" x="16" y="{H - 10}" fill="#8b949e">{total_contributions} contributions in the last year</text>'

    # Apache vector group in SVG
    apache_svg = f'''
    <g class="apache-squadron">
      <!-- Apache Helicopter Facing Right -->
      <g class="apache-airframe">
        <!-- Main Rotor -->
        <g class="main-rotor-grp" transform="translate(47, 7)">
          <ellipse cx="0" cy="0" rx="44" ry="3.5" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
          <line class="rotor-spin" x1="-42" y1="0" x2="42" y2="0" stroke="#d0d7de" stroke-width="2"/>
          <line class="rotor-spin" x1="0" y1="-2" x2="0" y2="2" stroke="#d0d7de" stroke-width="2"/>
          <!-- Longbow Dome -->
          <ellipse cx="0" cy="-2" rx="6" ry="3" fill="#30363d" stroke="#58a6ff" stroke-width="0.5"/>
        </g>
        <!-- Tail Boom & Empennage -->
        <polygon points="42,16 8,14 4,10 2,10 6,18 42,20" fill="#30363d" stroke="#161b22" stroke-width="0.8"/>
        <polygon points="10,16 5,4 1,4 4,18 8,18" fill="#484f58" stroke="#161b22" stroke-width="0.8"/>
        <!-- Tail Rotor -->
        <g class="tail-rotor-grp" transform="translate(3, 7)">
          <line class="tail-spin" x1="-8" y1="0" x2="8" y2="0" stroke="#d0d7de" stroke-width="1.5"/>
          <line class="tail-spin" x1="0" y1="-8" x2="0" y2="8" stroke="#d0d7de" stroke-width="1.5"/>
        </g>
        <!-- Fuselage Core -->
        <polygon points="66,18 56,12 36,12 34,19 40,24 62,24 67,21" fill="#30363d" stroke="#21262d" stroke-width="1"/>
        <polygon points="52,11 37,11 35,17 52,17" fill="#161b22" stroke="#484f58" stroke-width="0.8"/>
        <!-- Tandem Cockpits with Green HUD Glass -->
        <polygon points="65,18 61,14 54,14 56,19 64,19" fill="#0e4429" stroke="#39d353" stroke-width="0.8"/>
        <polygon points="55,17 53,13 46,13 47,18 54,18" fill="#0e4429" stroke="#39d353" stroke-width="0.8"/>
        <!-- TADS Nose Turret Ball -->
        <circle cx="70" cy="18" r="3" fill="#161b22" stroke="#39d353" stroke-width="0.8"/>
        <circle cx="70" cy="18" r="1.2" fill="#39d353"/>
        <!-- 30mm Chin Gun -->
        <line x1="62" y1="24" x2="73" y2="28" stroke="#161b22" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Muzzle Flash -->
        <polygon class="muzzle-burst" points="73,28 82,31 77,33 85,35 77,37 80,41 73,32" fill="#39d353"/>
        <!-- Stub Wings & Weapon Pods -->
        <polygon points="54,19 46,19 45,22 55,22" fill="#484f58"/>
        <rect x="47" y="22" width="7" height="3" fill="#161b22" stroke="#39d353" stroke-width="0.6"/>
        <!-- Landing Gear -->
        <line x1="56" y1="23" x2="59" y2="28" stroke="#161b22" stroke-width="1.8"/>
        <circle cx="59" cy="28" r="2" fill="#0d1117" stroke="#484f58" stroke-width="0.8"/>
      </g>
      <!-- Target Laser Designator -->
      <line class="laser-beam" x1="70" y1="18" x2="136" y2="76" stroke="#39d353" stroke-width="1" stroke-dasharray="4,2"/>
    </g>
    <!-- Projectiles -->
    <g class="projectiles-group">
      <line class="proj-streak p1" x1="463" y1="123" x2="531" y2="175" stroke="#39d353" stroke-width="2.5"/>
      <line class="proj-streak p2" x1="463" y1="123" x2="531" y2="175" stroke="#7ee787" stroke-width="2.5"/>
    </g>
    <!-- Impact Burst & Sparks -->
    <g class="impact-burst-group" transform="translate(531, 175)">
      <circle class="impact-flash" cx="0" cy="0" r="14" fill="#ffffff" stroke="#39d353" stroke-width="2"/>
      <line class="spark s1" x1="-15" y1="-15" x2="15" y2="15" stroke="#39d353" stroke-width="1.5"/>
      <line class="spark s2" x1="15" y1="-15" x2="-15" y2="15" stroke="#7ee787" stroke-width="1.5"/>
    </g>
    <!-- Rebuilding Hologram Scanline -->
    <line class="rebuild-scanline" x1="514" y1="141" x2="544" y2="141" stroke="#39d353" stroke-width="2"/>
    '''

    # CSS styles and keyframes (14s loop)
    css = f'''
    :root {{ --txt: #e6edf3; }}
    text {{ font-family: {FONT_STACK}; font-size: 15px; fill: var(--txt); }}
    @media (max-width: 620px) {{ text {{ font-size: 26px; }} }}
    .l0.f {{ fill: #ebedf0; }} .l0.t {{ fill: #f2f3f5; }} .l0.s {{ fill: #b7b9bb; }}
    .l1.f {{ fill: #9be9a8; }} .l1.t {{ fill: #bef1c6; }} .l1.s {{ fill: #79b683; }}
    .l2.f {{ fill: #40c463; }} .l2.t {{ fill: #83d99a; }} .l2.s {{ fill: #32994d; }}
    .l3.f {{ fill: #30a14e; }} .l3.t {{ fill: #78c28c; }} .l3.s {{ fill: #257e3d; }}
    .l4.f {{ fill: #216e39; }} .l4.t {{ fill: #6fa17e; }} .l4.s {{ fill: #1a562c; }}
    
    .win {{ animation: win-breathe 3s ease-in-out infinite; }}
    @keyframes win-breathe {{ 0%, 100% {{ opacity: 0.8; }} 50% {{ opacity: 1; filter: drop-shadow(0 0 2px #39d353); }} }}
    
    /* Helicopter Flight Path & Dynamics (14s seamless loop) */
    .apache-squadron {{
      animation: apache-flight 14s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      transform-origin: 40px 16px;
    }}
    @keyframes apache-flight {{
      0% {{ transform: translate(-100px, 85px) rotate(0deg); opacity: 0; }}
      14% {{ opacity: 1; }}
      30% {{ transform: translate(390px, 95px) rotate(-4deg); opacity: 1; }}
      36% {{ transform: translate(390px, 95px) rotate(1deg); }}
      48% {{ transform: translate(390px, 95px) rotate(-2deg); }}
      60% {{ transform: translate(390px, 95px) rotate(0deg); }}
      68% {{ transform: translate(405px, 95px) rotate(-8deg); opacity: 1; }}
      76% {{ transform: translate(920px, 55px) rotate(-8deg); opacity: 1; }}
      77%, 100% {{ transform: translate(920px, 55px); opacity: 0; }}
    }}
    
    .rotor-spin {{ transform-origin: 0 0; animation: r-spin 0.1s linear infinite; }}
    @keyframes r-spin {{ to {{ transform: rotate(360deg); }} }}
    
    .tail-spin {{ transform-origin: 0 0; animation: r-spin 0.05s linear infinite; }}
    
    /* Target Laser Designator */
    .laser-beam {{
      opacity: 0;
      animation: laser-sweep 14s ease-in-out infinite;
    }}
    @keyframes laser-sweep {{
      0%, 32% {{ opacity: 0; }}
      33%, 38% {{ opacity: 0.9; stroke-dashoffset: 0; }}
      39%, 100% {{ opacity: 0; }}
    }}
    
    /* Muzzle Bursts */
    .muzzle-burst {{
      opacity: 0;
      animation: m-burst 14s ease infinite;
    }}
    @keyframes m-burst {{
      0%, 39% {{ opacity: 0; }}
      40%, 40.5% {{ opacity: 1; }}
      41%, 42% {{ opacity: 0; }}
      42.5%, 43% {{ opacity: 1; }}
      43.5%, 44% {{ opacity: 0; }}
      44.5%, 45% {{ opacity: 1; }}
      45.5%, 100% {{ opacity: 0; }}
    }}
    
    /* Projectiles */
    .proj-streak {{
      opacity: 0;
      stroke-dasharray: 20 80;
      animation: p-streak 14s linear infinite;
    }}
    .p1 {{ animation-delay: 0s; }}
    .p2 {{ animation-delay: 0.3s; }}
    @keyframes p-streak {{
      0%, 40% {{ opacity: 0; stroke-dashoffset: 100; }}
      41% {{ opacity: 1; stroke-dashoffset: 80; }}
      44% {{ opacity: 1; stroke-dashoffset: 0; }}
      45%, 100% {{ opacity: 0; stroke-dashoffset: 0; }}
    }}
    
    /* Impact Flare */
    .impact-burst-group {{
      opacity: 0;
      animation: impact-fx 14s ease-out infinite;
    }}
    @keyframes impact-fx {{
      0%, 43% {{ opacity: 0; transform: translate(531px, 175px) scale(0.2); }}
      44%, 47% {{ opacity: 1; transform: translate(531px, 175px) scale(1.3); }}
      48%, 100% {{ opacity: 0; transform: translate(531px, 175px) scale(1.6); }}
    }}
    
    /* Target Tower Collapse & Automatic Rebuilding */
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
    
    /* Rebuilding Hologram Scanline */
    .rebuild-scanline {{
      opacity: 0;
      animation: rebuild-scan 14s ease-in-out infinite;
    }}
    @keyframes rebuild-scan {{
      0%, 74% {{ opacity: 0; transform: translateY(105px); }}
      76% {{ opacity: 1; transform: translateY(90px); }}
      86% {{ opacity: 1; transform: translateY(0px); }}
      87%, 100% {{ opacity: 0; }}
    }}
    '''

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution skyline: {total_contributions} contributions in the last year">
    <style>
    {css}
    </style>
    <rect width="{W}" height="{H}" fill="#0d1117"/>
    {shapes}
    {apache_svg}
    </svg>'''
    
    with open('skyline.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("skyline.svg updated with full animated vector sequence!")

# 1. Export animated skyline.svg
build_animated_svg()

# 2. Export animated skyline.gif
TOTAL_DURATION = 14.0 # seconds
FPS = 10
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)
DT = TOTAL_DURATION / TOTAL_FRAMES

print(f"Generating {TOTAL_FRAMES} frames at {FPS} FPS (total duration: {TOTAL_DURATION}s)...")
start_time = time.time()
frames = []

for i in range(TOTAL_FRAMES):
    t_val = i * DT
    f_img = generate_frame(t_val)
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
print(f"skyline.gif created successfully! Size: {gif_size / 1024:.1f} KB")

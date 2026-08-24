#!/usr/bin/env python3
"""Generate aitoollab.cn favicon .ico - v2 (cleaner rendering).

⚠️ 已废弃（2026-08-10）：本脚本生成的是旧版紫蓝色「ai 星环」图标，
与当前绿色系品牌不一致。站点 favicon 请改用 scripts/generate_site_logo.py，
勿再运行本脚本覆盖 favicon.ico。
"""

import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "C:/Users/27040/WorkBuddy/2026-07-01-07-23-20/outputs"
MASTER_SIZE = 512
ICO_SIZES = [16, 32, 48, 64, 128, 256]

# Colors
BG_START = (10, 25, 82)
BG_MID   = (56, 20, 115)
BG_END   = (107, 31, 153)
CYAN     = (0, 229, 255)
WHITE    = (255, 255, 255)
GOLD     = (255, 215, 0)
PURPLE   = (123, 97, 255)


def make_bg_gradient(size):
    """Diagonal blue→purple gradient (pixel-by-pixel, no banding)."""
    img = Image.new("RGB", (size, size))
    px = img.load()
    max_coord = 2 * (size - 1)
    for y in range(size):
        for x in range(size):
            t = (x + y) / max_coord
            t = max(0, min(1, t))
            if t < 0.5:
                tt = t * 2
                r = int(BG_START[0] + (BG_MID[0] - BG_START[0]) * tt)
                g = int(BG_START[1] + (BG_MID[1] - BG_START[1]) * tt)
                b = int(BG_START[2] + (BG_MID[2] - BG_START[2]) * tt)
            else:
                tt = (t - 0.5) * 2
                r = int(BG_MID[0] + (BG_END[0] - BG_MID[0]) * tt)
                g = int(BG_MID[1] + (BG_END[1] - BG_MID[1]) * tt)
                b = int(BG_MID[2] + (BG_END[2] - BG_MID[2]) * tt)
            px[x, y] = (r, g, b)
    return img


def draw_glow_circle(draw, cx, cy, radius, color, max_alpha=80):
    """Draw a soft glow using concentric alpha rings."""
    for i in range(int(radius), 0, -1):
        # Quadratic alpha falloff
        t = i / radius
        alpha = int(max_alpha * t * t)
        draw.ellipse(
            [(cx - i, cy - i), (cx + i, cy + i)],
            outline=(*color, alpha),
            width=1,
        )


def draw_filled_glow(img, cx, cy, radius, color, max_alpha=120):
    """Draw a filled glow with radial falloff, blurred for smoothness."""
    size = int(radius * 2 + 4)
    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    # Draw circle with full alpha, then use distance to create falloff
    gd.ellipse([(0, 0), (size - 1, size - 1)], fill=max_alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius * 0.5))
    # Colorize: only the glowing part, not the whole image
    colored = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Paste using the blurred glow as the alpha mask
    solid = Image.new("RGBA", (size, size), (*color, 255))
    colored.paste(solid, (0, 0), mask=glow)
    # Composite with the target image
    img.alpha_composite(colored, dest=(int(cx - size / 2), int(cy - size / 2)))


def draw_dashed_circle(img, cx, cy, r, color, alpha, dash_count=24):
    """Draw a dashed circle on the image."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    circumference = 2 * math.pi * r
    n = int(circumference * dash_count / 100)
    for i in range(n):
        a0 = (i / n) * 2 * math.pi
        a1 = ((i + 0.6) / n) * 2 * math.pi
        x1 = cx + r * math.cos(a0)
        y1 = cy + r * math.sin(a0)
        x2 = cx + r * math.cos(a1)
        y2 = cy + r * math.sin(a1)
        draw.line([(x1, y1), (x2, y2)], fill=(*color, int(alpha * 255)), width=1)
    img.alpha_composite(overlay)


def draw_gradient_line_fading(img, x1, y1, x2, y2, color, base_alpha=0.6):
    """Draw line with linear alpha fade from (x1,y1) to (x2,y2)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    segments = 20
    for s in range(segments):
        t0 = s / segments
        t1 = (s + 1) / segments
        mid = (t0 + t1) / 2
        # Alpha decays from 0.6 at t=0 to 0.02 at t=1
        alpha = base_alpha * (1 - mid) + 0.02
        a_int = int(alpha * 255)
        px1 = x1 + (x2 - x1) * t0
        py1 = y1 + (y2 - y1) * t0
        px2 = x1 + (x2 - x1) * t1
        py2 = y1 + (y2 - y1) * t1
        draw.line([(px1, py1), (px2, py2)], fill=(*color, a_int), width=2)
    img.alpha_composite(overlay)


def draw_node(img, cx, cy, r, color, alpha=255, inner_white=True):
    """Draw a glowing node."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Outer glow
    for i in range(int(r * 2.5), 0, -2):
        t = i / (r * 2.5)
        a = int(alpha * 0.15 * t * t)
        draw.ellipse(
            [(cx - i, cy - i), (cx + i, cy + i)],
            fill=(*color, a),
        )
    # Main body
    draw.ellipse(
        [(cx - r, cy - r), (cx + r, cy + r)],
        fill=(*color, int(alpha)),
    )
    # White center dot
    if inner_white and r >= 3:
        ir = max(1, int(r * 0.45))
        draw.ellipse(
            [(cx - ir, cy - ir), (cx + ir, cy + ir)],
            fill=(*WHITE, int(alpha * 0.9)),
        )
    img.alpha_composite(overlay)


def draw_ai_text(img, cx, cy, scale=1.0):
    """Draw 'ai' text with vertical gradient: white → cyan → purple."""
    size = img.size[0]
    text = "ai"
    font_size = int(72 * scale)

    # Load font
    font = None
    for fp in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arialbd.ttf",
    ]:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # Measure
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1]

    # Render text with a subtle dark drop shadow for contrast
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    shadow_offset = int(3 * scale)
    sdraw.text((tx + shadow_offset, ty + shadow_offset), text, font=font, fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=2 * scale))
    img.alpha_composite(shadow_layer)

    # Render white text
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(text_layer)
    tdraw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    # Apply vertical gradient
    text_data = text_layer.load()
    for y in range(size):
        for x in range(size):
            p = text_data[x, y]
            if p[3] > 0:
                t = y / size
                if t < 0.4:
                    tt = t / 0.4
                    r = int(255 + (CYAN[0] - 255) * tt)
                    g = int(255 + (CYAN[1] - 255) * tt)
                    b = int(255 + (CYAN[2] - 255) * tt)
                elif t < 0.7:
                    tt = (t - 0.4) / 0.3
                    r = int(CYAN[0] + (PURPLE[0] - CYAN[0]) * tt)
                    g = int(CYAN[1] + (PURPLE[1] - CYAN[1]) * tt)
                    b = int(CYAN[2] + (PURPLE[2] - CYAN[2]) * tt)
                else:
                    r, g, b = PURPLE
                text_data[x, y] = (r, g, b, p[3])

    img.alpha_composite(text_layer)


def draw_icon(size=MASTER_SIZE):
    """Draw the full icon."""
    cx, cy = size // 2, size // 2
    s = size / 512.0  # scale factor

    # Step 1: Background gradient
    bg = make_bg_gradient(size)

    # Create final image with rounded mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    corner_r = int(102 * s)
    md.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=corner_r, fill=255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)

    # Step 2: Outer purple glow (faint)
    draw_filled_glow(img, cx, cy, int(220 * s), PURPLE, max_alpha=30)

    # Step 3: Mid cyan glow
    draw_filled_glow(img, cx, cy, int(150 * s), CYAN, max_alpha=55)

    # Step 4: Inner white-cyan glow (smaller, behind text)
    draw_filled_glow(img, cx, cy, int(50 * s), (200, 240, 255), max_alpha=35)

    # Step 5: Dashed orbit rings
    for r_factor, alpha in [(140, 0.18), (90, 0.28), (52, 0.4)]:
        r = int(r_factor * s)
        draw_dashed_circle(img, cx, cy, r, CYAN, alpha)

    # Step 6: Connection lines + nodes
    primary_angles = [0, 90, 180, 270]  # N, E, S, W
    secondary_angles = [45, 135, 225, 315]  # NE, SE, SW, NW
    outer_angles = [20, 70, 110, 160, 200, 250, 290, 340]

    # Draw connection lines first (behind nodes)
    for angle in primary_angles + secondary_angles + outer_angles:
        rad = math.radians(angle)
        ex = cx + (size / 2) * 0.72 * math.cos(rad)
        ey = cy + (size / 2) * 0.72 * math.sin(rad)
        # Start line from center circle (r=40) instead of exact center
        sx = cx + 40 * s * math.cos(rad)
        sy = cy + 40 * s * math.sin(rad)
        draw_gradient_line_fading(img, sx, sy, ex, ey, CYAN, base_alpha=0.5)

    # Draw primary nodes (cyan with white center, large)
    for angle in primary_angles:
        rad = math.radians(angle)
        nx = cx + (size / 2) * 0.72 * math.cos(rad)
        ny = cy + (size / 2) * 0.72 * math.sin(rad)
        draw_node(img, nx, ny, int(8 * s), CYAN)

    # Draw secondary nodes
    for angle in secondary_angles:
        rad = math.radians(angle)
        nx = cx + (size / 2) * 0.62 * math.cos(rad)
        ny = cy + (size / 2) * 0.62 * math.sin(rad)
        draw_node(img, nx, ny, int(6.5 * s), CYAN)

    # Draw outer nodes
    for angle in outer_angles:
        rad = math.radians(angle)
        nx = cx + (size / 2) * 0.58 * math.cos(rad)
        ny = cy + (size / 2) * 0.58 * math.sin(rad)
        draw_node(img, nx, ny, int(5 * s), CYAN, inner_white=False)

    # Gold accent nodes (outer ring)
    for angle in [25, 75, 205, 255, 285, 335]:
        rad = math.radians(angle)
        nx = cx + (size / 2) * 0.50 * math.cos(rad)
        ny = cy + (size / 2) * 0.50 * math.sin(rad)
        draw_node(img, nx, ny, int(2.5 * s), GOLD, alpha=180, inner_white=False)

    # Purple accent nodes (mid ring)
    for angle in [10, 55, 100, 125, 170, 215, 260, 305, 350]:
        rad = math.radians(angle)
        nx = cx + (size / 2) * 0.40 * math.cos(rad)
        ny = cy + (size / 2) * 0.40 * math.sin(rad)
        draw_node(img, nx, ny, int(2 * s), PURPLE, alpha=150, inner_white=False)

    # Step 7: Center "ai" text (drawn on top of everything)
    draw_ai_text(img, cx, cy, scale=s)

    # Step 8: Tiny accent dot (the highlight)
    # Small bright cyan dot at top-left of center area
    dot_r = max(2, int(4 * s))
    dx = int(cx - 12 * s)
    dy = int(cy - 14 * s)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([(dx - dot_r * 2, dy - dot_r * 2), (dx + dot_r * 2, dy + dot_r * 2)],
               fill=(*WHITE, 80))
    od.ellipse([(dx - dot_r, dy - dot_r), (dx + dot_r, dy + dot_r)],
               fill=(*WHITE, 255))
    od.ellipse([(dx - dot_r // 2, dy - dot_r // 2), (dx + dot_r // 2, dy + dot_r // 2)],
               fill=(*CYAN, 255))
    img.alpha_composite(overlay)

    return img


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Generating master icon ({MASTER_SIZE}x{MASTER_SIZE})...")
    master = draw_icon(MASTER_SIZE)
    master.save(os.path.join(OUTPUT_DIR, "aitoollab-icon-512.png"), "PNG")
    print(f"  Saved: aitoollab-icon-512.png")

    print("Generating size variants...")
    icons = []
    for size in ICO_SIZES:
        if size == MASTER_SIZE:
            img = master.copy()
        else:
            img = master.resize((size, size), Image.LANCZOS)
        icons.append(img)
        img.save(os.path.join(OUTPUT_DIR, f"aitoollab-icon-{size}.png"), "PNG")
        print(f"  Saved: aitoollab-icon-{size}.png")

    # Combine into .ico
    ico_path = os.path.join(OUTPUT_DIR, "favicon.ico")
    icons[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"\nICO saved: {ico_path}")
    print(f"  Sizes: {ICO_SIZES}")


if __name__ == "__main__":
    main()

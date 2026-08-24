#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI工具宝箱（aitoollab.cn）品牌标识生成器

设计概念：打开的宝箱 + 上浮的 AI 星光（宝箱 = 精选收纳好工具；星光 = AI）。
所有图标统一由一个矢量母版（assets/logo/logo-mark.svg）推导，保证 favicon /
PWA 图标 / 站点 logo / 社交分享图风格一致。

用法：
    python scripts/generate_site_logo.py

输出：
    assets/logo/logo-mark.svg        矢量母版（头部导航用，currentColor 填充）
    assets/logo/logo-tile-512.png    512 方形母版
    favicon.ico                      16/32/48/64 多尺寸
    assets/icons/pwa-192.png
    assets/icons/pwa-512.png
    images/logo.png                  站点 logo（结构化数据 Organization.logo）
    images/og/aitoolbox-og.png       1200x630 社交分享卡
    output/logo-preview.png          预览拼版（供人工检查）
"""

import math
import os
import struct
import sys
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 品牌色（与 css/style.css 保持一致） ──
C_PRIMARY_LIGHT = (0, 194, 80)   # #00C250
C_PRIMARY = (0, 166, 79)         # #00A64F
C_PRIMARY_DARK = (0, 133, 58)    # #00853A
C_GRAD_MID = (0, 158, 67)        # #009E43
C_GRAD_END = (0, 127, 57)        # #007F39
C_WHITE = (255, 255, 255)

# ── 标识几何（24x24 画布；与 assets/logo/logo-mark.svg 保持一致） ──
# AI 星光：居中四角星，中心 (12, 12.4)，外径 4.9，腰径 3.1（粗臂，小尺寸清晰）
SPARK_CX, SPARK_CY, SPARK_R, SPARK_WAIST = 12.0, 12.4, 4.9, 3.1
# 方框（圆角矩形外框，象征宝箱/收纳）：x 3.4–20.6，y 4.2–20.6，圆角 3.4，线宽 1.9
BOX_X0, BOX_X1, BOX_Y0, BOX_Y1, BOX_RADIUS, BOX_STROKE = 3.4, 20.6, 4.2, 20.6, 3.4, 1.9

MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<rect x="3.4" y="4.2" width="17.2" height="16.4" rx="3.4"/>'
    '<path d="M12 7.5 Q14.19 10.21 16.9 12.4 Q14.19 14.59 12 17.3 '
    'Q9.81 14.59 7.1 12.4 Q9.81 10.21 12 7.5 Z" '
    'fill="currentColor" stroke="none"/></svg>'
)


def _quad_points(p0, c, p1, steps=24):
    """采样二次贝塞尔曲线（凹向中心的星芒）。"""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt * mt * p0[0] + 2 * mt * t * c[0] + t * t * p1[0]
        y = mt * mt * p0[1] + 2 * mt * t * c[1] + t * t * p1[1]
        pts.append((x, y))
    return pts


def sparkle_outline(cx, cy, r, waist):
    """返回四角星轮廓点（依次：上、右、下、左，象限内凹）。"""
    top = (cx, cy - r)
    right = (cx + r, cy)
    bottom = (cx, cy + r)
    left = (cx - r, cy)
    d = waist / math.sqrt(2)
    ne = (cx + d, cy - d)
    se = (cx + d, cy + d)
    sw = (cx - d, cy + d)
    nw = (cx - d, cy - d)
    pts = []
    pts += _quad_points(top, ne, right)
    pts += _quad_points(right, se, bottom)
    pts += _quad_points(bottom, sw, left)
    pts += _quad_points(left, nw, top)
    return pts


def draw_glyph(draw, scale, ox, oy, color):
    """在 (ox, oy) 为左上角的区域内绘制标识（24 画布坐标 * scale）。
    居中对称：圆角方框（外框）+ 内嵌四角星光。
    注意：ox/oy 是图形包围盒左上角（= BOX_X0/BOX_Y0 在 24 画布中的位置），
    绘制时以包围盒为锚点换算，避免整体向右下偏移。"""
    x0, y0 = ox, oy
    x1 = ox + (BOX_X1 - BOX_X0) * scale
    y1 = oy + (BOX_Y1 - BOX_Y0) * scale
    r = BOX_RADIUS * scale
    w = max(1, int(round(BOX_STROKE * scale)))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=color, width=w)
    spark = [(ox + (x - BOX_X0) * scale, oy + (y - BOX_Y0) * scale)
             for x, y in sparkle_outline(SPARK_CX, SPARK_CY, SPARK_R, SPARK_WAIST)]
    draw.polygon(spark, fill=color)


def gradient_bg(size, c0, c1, c2=None, angle="diag"):
    """对角渐变背景（自左上向右下），像素级无带状。"""
    img = Image.new("RGB", (size, size))
    px = img.load()
    max_coord = 2 * (size - 1)
    for y in range(size):
        for x in range(size):
            t = (x + y) / max_coord if angle == "diag" else y / (size - 1)
            if c2 is None:
                r = int(c0[0] + (c1[0] - c0[0]) * t)
                g = int(c0[1] + (c1[1] - c0[1]) * t)
                b = int(c0[2] + (c1[2] - c0[2]) * t)
            else:
                if t < 0.5:
                    tt = t * 2
                    r = int(c0[0] + (c1[0] - c0[0]) * tt)
                    g = int(c0[1] + (c1[1] - c0[1]) * tt)
                    b = int(c0[2] + (c1[2] - c0[2]) * tt)
                else:
                    tt = (t - 0.5) * 2
                    r = int(c1[0] + (c2[0] - c1[0]) * tt)
                    g = int(c1[1] + (c2[1] - c1[1]) * tt)
                    b = int(c1[2] + (c2[2] - c1[2]) * tt)
            px[x, y] = (r, g, b)
    return img


def add_top_light(img, center_frac=(0.30, 0.26), radius_frac=0.95, alpha=34):
    """左上柔光，增加纵深（alpha 0-255）。"""
    size = img.size[0]
    cx, cy = int(size * center_frac[0]), int(size * center_frac[1])
    r = int(size * radius_frac)
    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.18))
    white = Image.new("RGBA", (size, size), (*C_WHITE, 0))
    white.putalpha(glow)
    img.alpha_composite(white)


def tile_image(size, supersample=4):
    """生成方形圆角母版：品牌渐变 + 左上柔光 + 白色标识。"""
    hi = size * supersample
    bg = gradient_bg(hi, C_PRIMARY_LIGHT, C_GRAD_MID, C_GRAD_END)
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    mask = Image.new("L", (hi, hi), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, hi - 1, hi - 1], radius=int(hi * 0.225), fill=255)
    img.paste(bg, (0, 0), mask)
    add_top_light(img, alpha=36)

    # 标识：方框 + 星光整体严格居中（高度约占母版 62%）
    glyph_h = BOX_Y1 - BOX_Y0
    glyph_w = BOX_X1 - BOX_X0
    scale = hi * 0.62 / glyph_h
    ox = (hi - glyph_w * scale) / 2
    oy = (hi - glyph_h * scale) / 2
    draw = ImageDraw.Draw(img)
    draw_glyph(draw, scale, ox, oy, C_WHITE)

    if supersample > 1:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def save_ico(path, frames):
    """手工写多尺寸 ICO（32bpp BMP-DIB 帧，兼容 Chrome/Edge/Firefox/Windows）。"""
    entries = []
    datas = []
    offset = 6 + 16 * len(frames)
    for im in frames:
        w, h = im.size
        rgba = im.convert("RGBA")
        # BMP-DIB：bottom-up BGRA 行 + 全 0 的 AND mask
        rows = []
        for y in range(h - 1, -1, -1):
            row = bytearray()
            for x in range(w):
                r, g, b, a = rgba.getpixel((x, y))
                row += bytes((b, g, r, a))
            rows.append(bytes(row))
        bmp_rows = b"".join(rows)
        mask_row_len = ((w + 31) // 32) * 4
        mask = b"\x00" * (mask_row_len * h)
        header = struct.pack(
            "<IiiHHIIiiII",
            40, w, h * 2, 1, 32, 0, w * h * 4 + len(mask), 0, 0, 0, 0,
        )
        data = header + bmp_rows + mask
        datas.append(data)
        entries.append(struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0, h if h < 256 else 0, 0, 0,
            1, 32, len(data), offset,
        ))
        offset += len(data)
    out = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    for e in entries:
        out += e
    for d in datas:
        out += d
    _robust_write(path, bytes(out))


def _robust_write(path, data, retries=8, delay=0.6):
    """写入文件，带重试（Windows 杀软/索引服务偶发占用文件时避免构建中断）。"""
    last = None
    for i in range(retries):
        try:
            with open(path, "wb") as f:
                f.write(data)
            return
        except OSError as e:
            last = e
            time.sleep(delay)
    raise last


def og_card_image():
    """1200x630 社交分享卡：深绿渐变 + 左侧 logo + 右侧品牌字。"""
    W, H = 1200, 630
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg = gradient_bg(H, (0, 133, 58), (0, 51, 26), angle="diag")  # 竖渐变深绿
    bg = bg.resize((W, H), Image.BILINEAR)
    bg = bg.convert("RGBA")
    # 对角双色加深：左上更亮、右下更深
    overlay = gradient_bg(H, (0, 168, 82), (0, 28, 14), angle="diag").resize(
        (W, H), Image.BILINEAR).convert("RGBA")
    bg = Image.blend(bg, overlay, 0.35)
    img.paste(bg, (0, 0))

    # 装饰星光（右上角两颗小星 + 底部光斑）
    deco = ImageDraw.Draw(img)
    for (cx, cy, r) in [(1050, 130, 26), (1130, 210, 14), (150, 470, 10)]:
        pts = [(cx + x * r, cy + y * r) for x, y in sparkle_outline(0, 0, 1.0, 0.44)]
        deco.polygon(pts, fill=(255, 255, 255, 60))
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-200, H * 0.45, 560, H + 220], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=90))
    white = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    white.putalpha(glow)
    img.alpha_composite(white)

    # 左侧大 logo（圆角方形，白色标识）
    logo_size = 300
    logo = tile_image(logo_size)
    img.paste(logo, (95, (H - logo_size) // 2 + 8), logo)

    # 右侧文字
    draw = ImageDraw.Draw(img)
    try:
        f_bold = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 82)
        f_eng = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 34)
        f_sub = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 30)
        f_url = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 25)
    except OSError:
        f_bold = f_eng = f_sub = f_url = ImageFont.load_default()

    x = 470
    draw.text((x, 150), "AI工具宝箱", font=f_bold, fill=(255, 255, 255, 255))
    draw.text((x + 4, 262), "AIToolLab", font=f_eng, fill=(185, 240, 211, 235))
    draw.text((x, 340), "每日精选优质 AI 工具 · 实测驱动你的选择", font=f_sub, fill=(235, 248, 240, 235))
    draw.text((x, 445), "aitoollab.cn", font=f_url, fill=(255, 255, 255, 150))
    return img


def preview_image():
    """预览拼版：母版 / PWA / favicon 各尺寸 + 头部示意 + OG 缩略图。"""
    W, H = 1180, 880
    canvas = Image.new("RGB", (W, H), (241, 245, 249, 255))
    draw = ImageDraw.Draw(canvas)
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
        f_sm = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)
    except OSError:
        f = f_sm = ImageFont.load_default()

    def label(x, y, text, font=f_sm, fill=(100, 116, 139, 255)):
        draw.text((x, y), text, font=font, fill=fill)

    x0, y0 = 70, 60
    tile = tile_image(512)
    canvas.paste(tile, (x0, y0), tile)
    label(x0, y0 + 522, "512 · 母版 / PWA")

    sizes = [192, 64, 48, 32, 16]
    sx = x0 + 560
    for i, s in enumerate(sizes):
        im = tile_image(s)
        canvas.paste(im, (sx, y0 + (s < 64) * 14), im)
        label(sx + (s < 64) * 22, y0 + 34 + (s < 64) * 14 + (s if s >= 64 else 56), f"{s}px")
        sx += s + 28 if s >= 64 else 66

    # 头部示意（浅色条 + 标识 + 站点名）
    hy = 330
    draw.rounded_rectangle([70, hy, 1110, hy + 64], radius=12, fill=(255, 255, 255, 255),
                           outline=(226, 232, 240, 255))
    mark = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)
    glyph_h = BOX_Y1 - BOX_Y0
    glyph_w = BOX_X1 - BOX_X0
    m_scale = 64 / glyph_h
    draw_glyph(md, m_scale, (64 - glyph_w * m_scale) / 2, (64 - glyph_h * m_scale) / 2,
               (30, 41, 59, 255))
    canvas.paste(mark, (96, hy + 6), mark)
    label(176, hy + 18, "AI工具宝箱", font=f, fill=(30, 41, 59, 255))
    label(340, hy + 25, "每日更新 · 已收录数百款工具", fill=(100, 116, 139, 255))

    # OG 缩略图
    og = og_card_image().resize((600, 315), Image.LANCZOS)
    canvas.paste(og, (70, 450))
    label(70, 775, "images/og/aitoolbox-og.png（1200x630 社交分享卡缩略）")
    return canvas


def main():
    logo_dir = os.path.join(BASE_DIR, "assets", "logo")
    icons_dir = os.path.join(BASE_DIR, "assets", "icons")
    images_dir = os.path.join(BASE_DIR, "images")
    og_dir = os.path.join(images_dir, "og")
    output_dir = os.path.join(BASE_DIR, "output")
    for d in (logo_dir, icons_dir, images_dir, og_dir, output_dir):
        os.makedirs(d, exist_ok=True)

    # 矢量母版
    _robust_write(os.path.join(logo_dir, "logo-mark.svg"), (MARK_SVG + "\n").encode("utf-8"))
    print("[OK] assets/logo/logo-mark.svg")

    master = tile_image(512)
    _buf = BytesIO()
    master.save(_buf, format="PNG")
    _robust_write(os.path.join(logo_dir, "logo-tile-512.png"), _buf.getvalue())
    print("[OK] assets/logo/logo-tile-512.png")

    # favicon.ico（16/32/48/64，手工 ICO 容器）
    ico_frames = [tile_image(s) for s in (16, 32, 48, 64)]
    save_ico(os.path.join(BASE_DIR, "favicon.ico"), ico_frames)
    print("[OK] favicon.ico (16/32/48/64)")

    _buf = BytesIO()
    tile_image(192).save(_buf, format="PNG")
    _robust_write(os.path.join(icons_dir, "pwa-192.png"), _buf.getvalue())
    _buf = BytesIO()
    master.save(_buf, format="PNG")
    _robust_write(os.path.join(icons_dir, "pwa-512.png"), _buf.getvalue())
    print("[OK] assets/icons/pwa-192.png / pwa-512.png")

    _buf = BytesIO()
    master.save(_buf, format="PNG")
    _robust_write(os.path.join(images_dir, "logo.png"), _buf.getvalue())
    print("[OK] images/logo.png")

    _buf = BytesIO()
    og_card_image().save(_buf, format="PNG")
    _robust_write(os.path.join(og_dir, "aitoolbox-og.png"), _buf.getvalue())
    print("[OK] images/og/aitoolbox-og.png")

    _buf = BytesIO()
    preview_image().save(_buf, format="PNG")
    _robust_write(os.path.join(output_dir, "logo-preview.png"), _buf.getvalue())
    print("[OK] output/logo-preview.png")
    print("全部完成。")


if __name__ == "__main__":
    main()

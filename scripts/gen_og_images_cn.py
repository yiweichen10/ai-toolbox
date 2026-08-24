#!/usr/bin/env python3
"""
gen_og_images_cn.py — 中文站 aitoollab.cn OG 图生成（Pillow 绘制版）

移植自英文站 gen_og_images_en.py 的专业设计语言：
  渐变背景 + 装饰光晕 + 左侧色条 + 分类徽章 + 主/副标题 + 描述 + 特性标签 +
  底部统计条（更新/阅读/来源）+ 品牌条。所有元素铺满 1200x630，不再留白。

与英文站区别：
  - 使用 Noto Sans SC 渲染中文（按字符换行，支持中英文混排）
  - 分类配色映射中文类目
  - 标签/统计均为中文

Usage:
  python scripts/gen_og_images_cn.py            # 跳过已存在
  python scripts/gen_og_images_cn.py --force    # 全部重生成
"""
import argparse
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OG_DIR   = BASE_DIR / "images" / "og"

# ─── Canvas ───────────────────────────────────────────────────────────────────
W, H = 1200, 630

# ─── Palette（与英文站一致）────────────────────────────────────────────────────
C_BG      = (13,  18,  35)
C_CARD    = (22,  32,  56)
C_ACCENT  = (59, 130, 246)
C_ACCENT2 = (139, 92, 246)
C_BORDER  = (40,  55,  90)
C_WHITE   = (248, 250, 252)
C_SUB     = (148, 163, 184)
C_MUTED   = (71,  85, 105)
C_TAG_BG  = (30,  42,  72)

# ─── 中文分类 → 颜色 ──────────────────────────────────────────────────────────
CAT_COLOR = {
    "AI对话":   (59, 130, 246),
    "AI编程":   (16, 185, 129),
    "AI代码":   (16, 185, 129),
    "AI图像":   (168, 85, 247),
    "AI视频":   (239, 68, 68),
    "AI音频":   (245, 158, 11),
    "AI音乐":   (245, 158, 11),
    "AI写作":   (99, 102, 241),
    "AI办公":   (20, 184, 166),
    "AI搜索":   (236, 72, 153),
    "AI智能体": (139, 92, 246),
    "AI开发":   (16, 185, 129),
    "AI效率":   (20, 184, 166),
    "AI设计":   (236, 72, 153),
    "AI翻译":   (14, 165, 233),
    "AI行业应用": (234, 88, 12),
    "AI医疗":   (16, 185, 129),
    "AI教育":   (234, 179, 8),
    "AI绘画":   (168, 85, 247),
    "AI大模型": (59, 130, 246),
    "AI评测":   (99, 102, 241),
}
def _cat_color(category):
    return CAT_COLOR.get((category or "").strip(), C_ACCENT)

# ─── Fonts（Noto Sans SC，支持可变字重；回退微软雅黑）─────────────────────────
_FONT_VF = "C:/Windows/Fonts/NotoSansSC-VF.ttf"
_FONT_REG = "C:/Windows/Fonts/msyh.ttc"
_FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"

def _font(size, weight=400):
    # 优先 Noto Sans SC 可变字体（站点品牌字体）
    if os.path.exists(_FONT_VF):
        try:
            f = ImageFont.truetype(_FONT_VF, size)
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
            return f
        except Exception:
            pass
    # 回退：微软雅黑（静态粗体/常规）
    path = _FONT_BOLD if weight >= 600 else _FONT_REG
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

# ─── Text helpers ─────────────────────────────────────────────────────────────
def _wrap_cjk(text, font, max_w, draw):
    """按字符宽度换行，兼容中英文混排（中文逐字断，英文尽量整词）。"""
    if not text:
        return []
    lines, cur = [], ""
    buf = ""  # 英文单词缓冲
    for ch in text:
        if ch == "\n":
            if buf:
                cur += buf; buf = ""
            if cur:
                lines.append(cur); cur = ""
            continue
        if ch == " " or ch.isascii() and ch.isalnum():
            # 英文/数字累积成词，遇到边界再判断
            test = cur + buf + ch
            if draw.textbbox((0, 0), test, font=font)[2] > max_w and (cur or buf):
                if cur:
                    lines.append(cur); cur = ""
                # 若当前词本身超宽，强制断词
                if draw.textbbox((0, 0), buf + ch, font=font)[2] > max_w and buf:
                    while buf and draw.textbbox((0, 0), buf, font=font)[2] > max_w:
                        lines.append(buf[0]); buf = buf[1:]
                buf = buf + ch
            else:
                buf += ch
            continue
        # 中文/标点：先 flush 英文缓冲
        if buf:
            cur += buf; buf = ""
        test = cur + ch
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur = test
    if buf:
        cur += buf
    if cur:
        lines.append(cur)
    return lines

def _tw(text, font, draw):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def _parse_rating(s):
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(s))
    return m.group(1) if m else None

# ─── Drawing primitives（移植英文站）────────────────────────────────────────────
def _gradient_bg(img):
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(C_BG[0] + (C_CARD[0] - C_BG[0]) * t)
        g = int(C_BG[1] + (C_CARD[1] - C_BG[1]) * t)
        b = int(C_BG[2] + (C_CARD[2] - C_BG[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

def _left_bar(draw, color):
    draw.rectangle([(0, 0), (3, H)], fill=color)

def _glow_circle(img, cx, cy, radius, color, alpha=18):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    step = max(1, radius // 6)
    for r in range(radius, 0, -step):
        a = int(alpha * (1 - r / radius))
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                  fill=(color[0], color[1], color[2], a))
    base = img.convert("RGBA")
    combined = Image.alpha_composite(base, overlay)
    img.paste(combined.convert("RGB"))

def _category_badge(draw, text, x, y, color, font):
    tw, th = _tw(text, font, draw)
    px, py = 16, 7
    rx2, ry2 = x + tw + px * 2, y + th + py * 2
    draw.rounded_rectangle([(x, y), (rx2, ry2)], radius=6, fill=color)
    draw.text((x + px, y + py), text, font=font, fill=C_WHITE)
    return rx2, ry2

def _divider(draw, y, color):
    draw.rectangle([(72, y), (72 + 48, y + 2)], fill=color)

def _feature_tags(draw, tags, y, font, color, max_w=W - 132):
    x = 72
    for tag in tags:
        tw, th = _tw(tag, font, draw)
        px, py = 14, 7
        x2 = x + tw + px * 2
        if x2 > max_w:
            break
        draw.rounded_rectangle([(x, y), (x2, y + th + py * 2)], radius=5,
                                fill=C_TAG_BG, outline=C_BORDER, width=1)
        dot_x = x + px
        dot_y = y + py + th // 2
        draw.ellipse([(dot_x, dot_y - 3), (dot_x + 6, dot_y + 3)], fill=color)
        draw.text((x + px + 12, y + py), tag, font=font, fill=C_SUB)
        x = x2 + 10

# ─── Tool OG Image ────────────────────────────────────────────────────────────
def make_tool_og(tool, out_path):
    img = Image.new("RGB", (W, H))
    _gradient_bg(img)
    category = tool.get("category", "AI工具")
    color = _cat_color(category)
    _glow_circle(img, W - 160, 120, 280, color, alpha=22)
    _glow_circle(img, 80, H - 80, 200, C_ACCENT2, alpha=14)
    draw = ImageDraw.Draw(img)
    _left_bar(draw, color)

    f_badge = _font(14, weight=700)
    f_title = _font(54, weight=800)
    f_sub   = _font(19)
    f_meta  = _font(15)
    f_tag   = _font(13)
    f_label = _font(12)

    PAD = 72; BRAND_H = 40; RIGHT_W = 210
    LEFT_MAX = W - PAD - RIGHT_W - 24

    name = tool.get("name", "未知工具")
    desc = tool.get("description") or ""
    pros = tool.get("pros", [])[:3]
    features = tool.get("features", [])[:6]
    price = str(tool.get("price") or "免费").split("+")[0].strip()[:22]
    platform = str(tool.get("platform") or "")[:18]
    rating = _parse_rating(tool.get("rating"))

    _SKIP = {"免费", "付费", "免费可用", "热门", "新品", "趋势", "推荐", "hot", "new", "free", "paid"}
    raw_tags = tool.get("tags", [])
    best_tags = [t.get("text") for t in raw_tags
                 if isinstance(t, dict) and not t.get("type")
                 and t.get("text", "").strip() not in _SKIP][:4]

    name_lines = _wrap_cjk(name, f_title, LEFT_MAX, draw)[:2]
    desc_lines = _wrap_cjk(desc, f_sub, LEFT_MAX, draw)[:2]

    y = 44
    # 评分块（右上）
    if rating:
        f_big = _font(78, weight=800)
        f_bsub = _font(13)
        num_tw, _ = _tw(rating, f_big, draw)
        num_x = W - num_tw - 60
        num_y = y + 6
        cx = num_x + num_tw // 2
        bb = draw.textbbox((num_x, num_y), rating, font=f_big)
        draw.text((cx - 24, num_y - 16), "评分", font=f_label, fill=C_MUTED)
        draw.text((num_x, num_y), rating, font=f_big, fill=(*color, 255))
        draw.text((cx - 18, bb[3] + 4), "/ 10", font=f_bsub, fill=C_MUTED)

    _, badge_b = _category_badge(draw, category, PAD, y, color, f_badge)
    y = badge_b + 22
    for line in name_lines:
        draw.text((PAD, y), line, font=f_title, fill=C_WHITE); y += 62
    y += 4
    for line in desc_lines:
        draw.text((PAD, y), line, font=f_sub, fill=C_SUB); y += 26
    y += 14
    _divider(draw, y, color); y += 16
    # 定价 / 平台
    x = PAD
    for label, val in [("定价", price), ("平台", platform)]:
        if not val:
            continue
        draw.text((x, y), label, font=f_label, fill=C_MUTED)
        draw.text((x, y + 17), str(val)[:22], font=f_meta, fill=C_WHITE)
        x += 260
    y += 50
    for pro in pros:
        dot_x, dot_y = PAD + 3, y + 6
        draw.ellipse([(dot_x, dot_y), (dot_x + 7, dot_y + 7)], fill=color)
        draw.text((PAD + 18, y), _wrap_cjk(pro, f_meta, LEFT_MAX - 18, draw)[0][:42], font=f_meta, fill=C_SUB)
        y += 26
    if pros:
        y += 18
    if features:
        _feature_tags(draw, features, y, f_tag, color)
        y += 50
    if best_tags:
        draw.text((PAD, y), "适合", font=f_label, fill=C_MUTED); y += 18
        _feature_tags(draw, best_tags, y, f_tag, color)
        y += 44
    # 品牌条
    draw.rectangle([(0, H - BRAND_H - 1), (W, H - BRAND_H)], fill=C_BORDER)
    draw.rectangle([(0, H - BRAND_H), (W, H)], fill=(10, 14, 28))
    draw.text((PAD, H - 27), "aitoollab.cn — AI 工具箱 · 中文 AI 导航", font=f_label, fill=C_MUTED)
    draw.text((W - 150, H - 27), "AI工具宝箱", font=f_label, fill=color)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG", optimize=True)
    return img

# ─── Article OG Image ───────────────────────────────────────────────────────────
def make_article_og(article, out_path):
    img = Image.new("RGB", (W, H))
    _gradient_bg(img)
    category = article.get("category", "AI工具")
    color = _cat_color(category)
    _glow_circle(img, W - 100, 80, 320, color, alpha=18)
    _glow_circle(img, 60, H - 60, 180, C_ACCENT2, alpha=12)
    draw = ImageDraw.Draw(img)
    _left_bar(draw, color)

    f_badge = _font(14, weight=700)
    f_main  = _font(50, weight=800)
    f_sub   = _font(21)
    f_desc  = _font(16)
    f_meta  = _font(15)
    f_label = _font(12)

    PAD = 72; BRAND_H = 40
    title = article.get("title", "")
    if "：" in title:
        main_t, sub_t = title.split("：", 1)
    elif "——" in title:
        main_t, sub_t = title.split("——", 1)
    else:
        main_t, sub_t = title, ""
    main_t, sub_t = main_t.strip(), sub_t.strip()
    main_lines = _wrap_cjk(main_t, f_main, W - PAD - 100, draw)[:2]
    sub_lines  = _wrap_cjk(sub_t, f_sub, W - PAD - 100, draw)[:2] if sub_t else []

    desc = article.get("excerpt") or article.get("description") or ""
    desc = re.sub(r"\s+", " ", desc).strip()
    desc_lines = _wrap_cjk(desc[:120], f_desc, W - PAD - 90, draw)[:3] if desc else []

    tags = article.get("keywords", article.get("tags", []))
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags = [t for t in tags if t and len(t) <= 8][:5]

    # 测量总块高，垂直居中
    _ay = 0
    _, _abb = _category_badge(draw, category, PAD, _ay, color, f_badge)
    _ay = _abb + 20
    _ay += len(main_lines) * 58 + 6
    _ay += len(sub_lines) * 30 + (8 if sub_lines else 0)
    _ay += 18
    _ay += len(desc_lines) * 24 + (16 if desc_lines else 0)
    _ay += 36
    _ay += 22 + 10 + 36
    art_total_h = _ay
    USABLE = H - BRAND_H
    y = max(40, (USABLE - art_total_h) // 2)

    _, badge_b = _category_badge(draw, category, PAD, y, color, f_badge)
    y = badge_b + 20
    for line in main_lines:
        draw.text((PAD, y), line, font=f_main, fill=C_WHITE); y += 58
    y += 6
    if sub_lines:
        for line in sub_lines:
            draw.text((PAD, y), line, font=f_sub, fill=C_SUB); y += 30
        y += 8
    _divider(draw, y, color); y += 18
    if desc_lines:
        block_h = len(desc_lines) * 24
        draw.rectangle([(PAD, y), (PAD + 3, y + block_h + 4)], fill=color)
        for line in desc_lines:
            draw.text((PAD + 16, y), line, font=f_desc, fill=C_SUB); y += 24
        y += 16
    if tags:
        x = PAD
        for tag in tags:
            tw, th = _tw(tag, f_label, draw)
            px = 12
            x2 = x + tw + px * 2
            if x2 > W - 60:
                break
            draw.rounded_rectangle([(x, y), (x2, y + th + 14)], radius=4,
                                    fill=C_TAG_BG, outline=C_BORDER)
            draw.text((x + px, y + 7), tag, font=f_label, fill=C_SUB)
            x = x2 + 10
    y += 36
    rule_y = y + 22
    stats_y = rule_y + 10
    draw.rectangle([(PAD, rule_y), (PAD + 500, rule_y + 1)], fill=C_BORDER)
    date_str = article.get("dateFull", article.get("date", ""))
    sx = PAD
    for slabel, sval in [("更新", date_str), ("阅读", "8 分钟"), ("来源", "aitoollab.cn")]:
        if not sval:
            continue
        draw.text((sx, stats_y), slabel, font=f_label, fill=C_MUTED)
        draw.text((sx, stats_y + 18), sval, font=f_meta, fill=C_WHITE)
        sx += 220
    # 品牌条
    draw.rectangle([(0, H - BRAND_H - 1), (W, H - BRAND_H)], fill=C_BORDER)
    draw.rectangle([(0, H - BRAND_H), (W, H)], fill=(10, 14, 28))
    draw.text((PAD, H - 27), "aitoollab.cn — AI 工具箱 · 中文 AI 导航", font=f_label, fill=C_MUTED)
    draw.text((W - 150, H - 27), "AI工具宝箱", font=f_label, fill=color)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG", optimize=True)
    return img

# ─── Dict OG Image ──────────────────────────────────────────────────────────────
def make_dict_og(term_data, out_path):
    img = Image.new("RGB", (W, H))
    _gradient_bg(img)
    category = term_data.get("category", "AI基础")
    color = _cat_color(category)
    _glow_circle(img, W - 120, 90, 300, color, alpha=18)
    _glow_circle(img, 70, H - 70, 180, C_ACCENT2, alpha=12)
    draw = ImageDraw.Draw(img)
    _left_bar(draw, color)

    f_badge = _font(14, weight=700)
    f_term  = _font(52, weight=800)
    f_en    = _font(20)
    f_desc  = _font(16)
    f_label = _font(12)

    PAD = 72; BRAND_H = 40
    term = term_data.get("term", "")
    en = term_data.get("en", "")
    emoji = term_data.get("emoji", "🤖")
    brief = term_data.get("brief", "")
    tags = term_data.get("tags", [])[:5]

    term_lines = _wrap_cjk(term, f_term, W - PAD - 120, draw)[:2]
    en_lines = _wrap_cjk(en, f_en, W - PAD - 120, draw)[:1] if en else []
    brief_lines = _wrap_cjk(brief[:110], f_desc, W - PAD - 90, draw)[:3] if brief else []

    y = 48
    _, badge_b = _category_badge(draw, f"{emoji} {category}", PAD, y, color, f_badge)
    y = badge_b + 22
    for line in term_lines:
        draw.text((PAD, y), line, font=f_term, fill=C_WHITE); y += 60
    y += 4
    if en_lines:
        for line in en_lines:
            draw.text((PAD, y), line, font=f_en, fill=C_SUB); y += 28
        y += 8
    _divider(draw, y, color); y += 18
    if brief_lines:
        block_h = len(brief_lines) * 24
        draw.rectangle([(PAD, y), (PAD + 3, y + block_h + 4)], fill=color)
        for line in brief_lines:
            draw.text((PAD + 16, y), line, font=f_desc, fill=C_SUB); y += 24
        y += 18
    if tags:
        x = PAD
        for tag in tags:
            tw, th = _tw(tag, f_label, draw)
            px = 12
            x2 = x + tw + px * 2
            if x2 > W - 60:
                break
            draw.rounded_rectangle([(x, y), (x2, y + th + 14)], radius=4,
                                    fill=C_TAG_BG, outline=C_BORDER)
            draw.text((x + px, y + 7), tag, font=f_label, fill=C_SUB)
            x = x2 + 10
    draw.rectangle([(0, H - BRAND_H - 1), (W, H - BRAND_H)], fill=C_BORDER)
    draw.rectangle([(0, H - BRAND_H), (W, H)], fill=(10, 14, 28))
    draw.text((PAD, H - 27), "aitoollab.cn — AI 词典 · 搞懂每个 AI 术语", font=f_label, fill=C_MUTED)
    draw.text((W - 150, H - 27), "AI工具宝箱", font=f_label, fill=color)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG", optimize=True)
    return img

# ─── Batch generation ───────────────────────────────────────────────────────────
def _iter_articles():
    p = DATA_DIR / "articles.json"
    if p.exists():
        for a in json.load(open(p, encoding="utf-8")):
            yield a.get("slug"), a

def _iter_tools():
    p = DATA_DIR / "tools.json"
    if p.exists():
        for t in json.load(open(p, encoding="utf-8")):
            yield t.get("slug"), t

def _iter_dict():
    p = DATA_DIR / "dict_terms.json"
    if p.exists():
        for d in json.load(open(p, encoding="utf-8")):
            yield d.get("slug"), d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="强制重生成所有 OG")
    args = ap.parse_args()
    OG_DIR.mkdir(parents=True, exist_ok=True)
    counts = {"tool": 0, "article": 0, "dict": 0}

    for slug, tool in _iter_tools():
        if not slug:
            continue
        out = OG_DIR / f"{slug}-og.png"
        if out.exists() and not args.force:
            continue
        make_tool_og(tool, out)
        counts["tool"] += 1
    for slug, art in _iter_articles():
        if not slug:
            continue
        out = OG_DIR / f"{slug}-og.png"
        if out.exists() and not args.force:
            continue
        make_article_og(art, out)
        counts["article"] += 1
    for slug, term in _iter_dict():
        if not slug:
            continue
        out = OG_DIR / f"{slug}-og.png"
        if out.exists() and not args.force:
            continue
        make_dict_og(term, out)
        counts["dict"] += 1

    print(f"✅ OG 生成完成：工具 {counts['tool']} / 文章 {counts['article']} / 词典 {counts['dict']}")

if __name__ == "__main__":
    main()

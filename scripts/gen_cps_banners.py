# -*- coding: utf-8 -*-
"""
生成 3 张 CPS 推广卡片宣传图（600x340 WebP）。
设计：品牌渐变背景 + 白色芯片logo + 中文大字品牌名 + 卖点文案。
比 AI 生图可靠：中文/logo 清晰，信用度高，改文案重跑即可。
依赖：Pillow + Windows 微软雅黑字体。
输出：ads/images/{aliyun,tencent,baidu}-cps.webp
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'ads', 'images')
FONT_REG = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'

W, H = 1200, 680  # 2x，最终缩到 600x340


def load(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(w, h, c1, c2):
    base = Image.new('RGB', (w, h))
    px = base.load()
    for y in range(h):
        for x in range(w):
            t = min(1, max(0, (x / w + y / h) / 2.0))
            px[x, y] = lerp(c1, c2, t)
    return base


def add_deco(base, color, alpha, shapes):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for s in shapes:
        if s[0] == 'circle':
            cx, cy, r = s[1:]
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    base.alpha_composite(layer)


def text_size(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


def make(brand, out_path):
    base = gradient(W, H, brand['c1'], brand['c2']).convert('RGBA')
    add_deco(base, (255, 255, 255), 22,
             [('circle', 1050, 110, 240), ('circle', 1010, 650, 170), ('circle', 120, 650, 150)])

    # 右侧大水印字
    wl = Image.new('RGBA', base.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wl)
    wf = load(380, True)
    tw, th = text_size(wd, brand['wm'], wf)
    wd.text(((W - tw) / 2 + 140, (H - th) / 2), brand['wm'], font=wf, fill=(255, 255, 255, 14))
    base.alpha_composite(wl)

    d = ImageDraw.Draw(base)

    # 白色芯片 + 品牌字
    chip = brand['chip']
    d.rounded_rectangle([70, 95, 200, 225], radius=30, fill=chip['bg'])
    cf = load(86, True)
    cw, ch = text_size(d, brand['char'], cf)
    d.text(((70 + 200) / 2 - cw / 2, (95 + 225) / 2 - ch / 2 - 4), brand['char'],
           font=cf, fill=chip['fg'])

    # 品牌名
    nf = load(78, True)
    d.text((238, 94), brand['name'], font=nf, fill=(255, 255, 255))
    # 渠道/子标题
    sf = load(36, False)
    d.text((240, 196), brand['sub'], font=sf, fill=(255, 255, 255, 220))

    # 分隔线
    d.line([72, 272, 1128, 272], fill=(255, 255, 255, 70), width=2)

    # 主卖点
    tf = load(58, True)
    d.text((72, 300), brand['tagline'], font=tf, fill=(255, 255, 255))
    # 副卖点
    stf = load(38, False)
    d.text((72, 392), brand['subtag'], font=stf, fill=(255, 255, 255, 235))

    # 底部胶囊标签
    pf = load(32, True)
    pw, ph = text_size(d, brand['pill'], pf)
    padx, pady = 22, 12
    px0, py0 = 72, 556
    d.rounded_rectangle([px0, py0, px0 + pw + padx * 2, py0 + ph + pady * 2],
                        radius=26, fill=(255, 255, 255, 45))
    d.text((px0 + padx, py0 + pady - 2), brand['pill'], font=pf, fill=(255, 255, 255))

    out = base.convert('RGB').resize((600, 340), Image.LANCZOS)
    out.save(out_path, 'WEBP', quality=85)
    print('%s  %d KB' % (os.path.basename(out_path), os.path.getsize(out_path) // 1024))


BRANDS = [
    {
        'key': 'aliyun',
        'c1': (255, 122, 0), 'c2': (224, 66, 11),
        'chip': {'bg': (255, 255, 255), 'fg': (255, 106, 0)}, 'char': '云',
        'name': '阿里云', 'sub': '阿里云云大使',
        'tagline': '企业级 AI 平台 · 免费试用', 'subtag': '百炼大模型 · Agent 返佣 30%',
        'pill': '官方授权推广', 'wm': '云',
    },
    {
        'key': 'tencent',
        'c1': (40, 120, 255), 'c2': (0, 70, 210),
        'chip': {'bg': (255, 255, 255), 'fg': (0, 85, 233)}, 'char': '混',
        'name': '腾讯混元', 'sub': '腾讯混元推广',
        'tagline': '腾讯自研大模型 · 免费体验', 'subtag': '对话/绘画/视频/音频全覆盖',
        'pill': '官方授权推广', 'wm': '混',
    },
    {
        'key': 'baidu',
        'c1': (92, 110, 255), 'c2': (41, 50, 225),
        'chip': {'bg': (255, 255, 255), 'fg': (41, 50, 225)}, 'char': '文',
        'name': '文心一言', 'sub': '百度文心合伙人',
        'tagline': '企业级 AI 写作 · 免费试用', 'subtag': '百度智能云 · 文案场景强',
        'pill': '官方授权推广', 'wm': '文',
    },
]

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    for b in BRANDS:
        make(b, os.path.join(OUT_DIR, '%s-cps.webp' % b['key']))
    print('done')

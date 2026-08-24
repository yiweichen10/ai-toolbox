# -*- coding: utf-8 -*-
"""fetch_icons.py — 自动抓取工具官方 favicon/logo 存为 assets/icons/{slug}.png
解决"入库工具无真实 LOGO、回退 emoji 色块"的未闭环。

数据源：Google s2 favicons 服务（返回正方形 PNG），兜底直抓 {domain}/favicon.ico。
幂等：assets/icons/{slug}.png 已存在则跳过。
用法：
  python scripts/fetch_icons.py                 # 补全所有无图标的工具
  python scripts/fetch_icons.py --slug foo,bar   # 只抓指定 slug
  python scripts/fetch_icons.py --limit 10       # 只抓前 N 个（调试）
"""
import json, os, io, sys, argparse
from urllib.request import Request, urlopen
from urllib.parse import urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data', 'tools.json')
ICONS = os.path.join(BASE, 'assets', 'icons')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

# slug → favicon 域名兜底（url 字段域名过期/子域名特殊时用）
# 背景：transmart.qq.com / niji.midjourney.com / autogpt.com 等 url 里域名已失效或子域无独立 favicon，
# 需手动指定真实 favicon 域名。新增工具抓不到图标时，先查此表。
FALLBACK_DOMAINS = {
    'transmart': 'fanyi.qq.com',
    'niji-journey': 'nijijourney.com',
    'autogpt': 'autogpt.net',
    'soloop': 'soloop.com',
    'goose': 'block.xyz',
}


def _domain(url):
    try:
        d = urlparse(url if '://' in url else 'https://' + url).netloc.lower()
        if d.startswith('www.'):
            d = d[4:]
        return d
    except Exception:
        return ''


def _to_square_png(raw, out_path, size=128):
    """把任意 favicon 字节流转成正方形 PNG。非图片/失败返回 False。"""
    from PIL import Image
    img = Image.open(io.BytesIO(raw)).convert('RGBA')
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    # 透明底填充为白底（避免透明 favicon 在暗色下不可见）
    bg = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    bg.alpha_composite(img)
    bg.convert('RGB').save(out_path, 'PNG')
    return True


def fetch_icon(slug, url):
    """抓单个工具的图标，返回 (ok, src)。已存在返回 (True, 'exists')。"""
    out = os.path.join(ICONS, slug + '.png')
    if os.path.exists(out):
        return True, 'exists'
    dom = _domain(url)
    if not dom:
        return False, 'no-domain'
    # fallback 域名优先（url 域名过期时用）
    if slug in FALLBACK_DOMAINS:
        dom = FALLBACK_DOMAINS[slug]
    # 1) Google s2 favicons（正方形 PNG）
    for sz in (128, 64):
        try:
            req = Request(f'https://www.google.com/s2/favicons?domain={dom}&sz={sz}', headers={'User-Agent': UA})
            raw = urlopen(req, timeout=8).read()
            if len(raw) > 200 and _to_square_png(raw, out):
                return True, f's2-{sz}'
        except Exception:
            pass
    # 2) 兜底：直抓 favicon.ico
    try:
        req = Request(f'https://{dom}/favicon.ico', headers={'User-Agent': UA})
        raw = urlopen(req, timeout=8).read()
        if len(raw) > 200 and _to_square_png(raw, out):
            return True, 'favicon.ico'
    except Exception:
        pass
    return False, 'failed'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', help='逗号分隔的 slug 列表')
    ap.add_argument('--limit', type=int, help='最多抓 N 个')
    args = ap.parse_args()

    tools = json.load(open(DATA, encoding='utf-8'))
    os.makedirs(ICONS, exist_ok=True)

    # 已存在的图标 stem
    have = {os.path.splitext(f)[0] for f in os.listdir(ICONS) if f.endswith(('.svg', '.png'))}

    if args.slug:
        targets = [t for t in tools if t.get('slug') in args.slug.split(',')]
    else:
        targets = [t for t in tools if t.get('slug') not in have]
    if args.limit:
        targets = targets[:args.limit]

    ok = skip = fail = 0
    for t in targets:
        slug, url = t.get('slug', ''), t.get('url', '')
        r, src = fetch_icon(slug, url)
        if r and src == 'exists':
            skip += 1
        elif r:
            ok += 1
            print(f'  ✅ {slug}  ← {src}')
        else:
            fail += 1
            print(f'  ❌ {slug}  ({src})')
    print(f'\n完成: 新增 {ok} | 已存在 {skip} | 失败 {fail} | 共 {len(targets)}')

if __name__ == '__main__':
    main()

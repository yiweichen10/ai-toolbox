# -*- coding: utf-8 -*-
"""
从 LobeHub 图标库(@lobehub/icons-static-svg CDN)同步真实品牌 logo，
替换站点上仍在使用 emoji/首字母占位的工具图标。

用法:
  python scripts/sync_lobehub_icons.py --scan          # 只扫描，列出仍回退 emoji 的工具 + LobeHub 匹配情况
  python scripts/sync_lobehub_icons.py --download      # 下载已匹配的图标到 assets/icons/
  python scripts/sync_lobehub_icons.py --download --force  # 覆盖已存在的图标

原理:
  build.py 的 resolve_icon(slug) 会优先读取 assets/icons/{slug}.svg|png，
  找不到才回退 emoji+色块。所以只要把真实 logo 存成 assets/icons/{slug}.svg 即可自动生效。

图标来源:
  https://unpkg.com/@lobehub/icons-static-svg@latest/icons/{name}.svg        (单色)
  https://unpkg.com/@lobehub/icons-static-svg@latest/icons/{name}-color.svg  (彩色, 部分品牌无)
  优先彩色, 无彩色则用单色。
"""
import os, re, json, argparse, urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ICONS_DIR = os.path.join(BASE_DIR, 'assets', 'icons')
CDN = "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/{}.svg"
META = "https://unpkg.com/@lobehub/icons-static-svg@latest/?meta"

# 人工别名: 站点 slug -> LobeHub 基础名 (中文品牌 / 命名差异)
ALIAS = {
    'tencent-yuanbao': 'yuanbao', 'tencent-hunyuan': 'hunyuan', 'tencent-docs-ai': 'tencent',
    'adobe-firefly': 'adobefirefly', 'kling-ai': 'kling', 'microsoft-copilot': 'copilot',
    'xinghuo-iflytek': 'spark', 'xinghuo-cognitive-model': 'spark', 'tiangong': 'tiangong',
    'baichuan-ai': 'baichuan', 'baichuan-2': 'baichuan', 'cognition-ai': 'devin', 'devin-ai': 'devin',
    'capcut-ai': 'capcut', 'luma-ai': 'luma', 'v0.dev': 'v0', 'fireflies.ai': 'fireflies',
    'vidu-ai': 'vidu', 'vidu-2-0': 'vidu', 'longcat20': 'longcat', 'modelscope-agent': 'modelscope',
    'open-router': 'openrouter', 'mistral-ai': 'mistral', 'llamaindex': 'llamaindex', 'metagpt': 'metagpt',
}

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def http_get(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode('utf-8')

def load_lobe_names():
    meta = json.loads(http_get(META))
    names = [f['path'].rsplit('/', 1)[-1][:-4]
             for f in meta['files']
             if f['path'].startswith('/icons/') and f['path'].endswith('.svg')]
    return sorted(set(names))

def build_lobe_lookup(names):
    """normalized base name -> raw lobe basename (无后缀优先)"""
    suff = ['-brand-color', '-combine-color', '-brand', '-combine', '-color', '-text', '-mono']
    base = set()
    for n in names:
        b = n
        for x in suff:
            if b.endswith(x):
                b = b[:-len(x)]; break
        base.add(b)
    lookup = {}
    for b in sorted(base):
        lookup.setdefault(norm(b), b)
    for n in names:
        lookup.setdefault(norm(n), n)
    return lookup, set(names)

def local_have():
    have = set()
    for f in os.listdir(ICONS_DIR):
        b, e = os.path.splitext(f)
        if e.lower() in ('.svg', '.png'):
            have.add(b)
    return have

def match_tool(slug, name, lookup):
    cands = []
    if slug in ALIAS:
        cands.append(ALIAS[slug])
    base = slug
    for suf in ('-ai', '-app', '.ai', '.new', '.dev', '.bg', '-2-0', '-2', '-o', '20'):
        if base.endswith(suf):
            base = base[:-len(suf)]; break
    cands += [slug, base, name]
    for c in cands:
        nc = norm(c)
        if nc and nc in lookup:
            return lookup[nc]
    return None

def pick_svg_url(lobe_base, all_names):
    """优先彩色, 其次单色。返回 (url, variant)"""
    for variant in (lobe_base + '-color', lobe_base):
        if variant in all_names:
            return CDN.format(variant), variant
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    if not (args.scan or args.download):
        args.scan = True

    tools = json.load(open(os.path.join(DATA_DIR, 'tools.json'), encoding='utf-8'))
    have = local_have()
    gap = [t for t in tools if t.get('slug') and t['slug'] not in have]

    print(f"总工具 {len(tools)} | 已有本地图标 {len(have)} | 仍回退emoji {len(gap)}")
    print("拉取 LobeHub 图标清单...")
    names = load_lobe_names()
    lookup, all_names = build_lobe_lookup(names)
    print(f"LobeHub 图标 {len(all_names)} 个\n")

    matched, unmatched = [], []
    for t in gap:
        lb = match_tool(t['slug'], t['name'], lookup)
        if lb:
            url, variant = pick_svg_url(lb, all_names)
            if url:
                matched.append((t['slug'], t['name'], variant, url))
            else:
                unmatched.append((t['slug'], t['name'], t.get('emoji', '')))
        else:
            unmatched.append((t['slug'], t['name'], t.get('emoji', '')))

    print(f"=== 可从 LobeHub 补齐: {len(matched)} ===")
    for s, n, v, u in matched:
        print(f"  {s:26} -> {v}")
    print(f"\n=== LobeHub 无对应(需其他来源/保留emoji): {len(unmatched)} ===")
    for s, n, e in unmatched:
        print(f"  {s:26} | {n:22} | {e}")

    if args.download:
        print("\n开始下载...")
        ok = skip = fail = 0
        for s, n, v, u in matched:
            dst = os.path.join(ICONS_DIR, s + '.svg')
            if os.path.exists(dst) and not args.force:
                skip += 1; continue
            try:
                svg = http_get(u, binary=True)
                if not svg.lstrip().startswith(b'<svg') and b'<svg' not in svg[:200]:
                    print(f"  [跳过] {s}: 非SVG内容"); fail += 1; continue
                with open(dst, 'wb') as f:
                    f.write(svg)
                print(f"  [OK] {s}.svg  <- {v}")
                ok += 1
            except Exception as ex:
                print(f"  [失败] {s}: {ex}"); fail += 1
        print(f"\n下载完成: 成功 {ok} | 跳过(已存在) {skip} | 失败 {fail}")
        print("提示: 运行 python scripts/build.py 重建站点后图标即生效。")

if __name__ == '__main__':
    main()

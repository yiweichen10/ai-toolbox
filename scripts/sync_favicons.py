# -*- coding: utf-8 -*-
"""
用真实 favicon 补齐仍回退 emoji 的工具图标到 assets/icons/。

数据源（按优先级，第一个成功即用）：
  1. icon.horse/icon/{domain}     —— 聚合 favicon（后端不直连官网，可绕过 heygen 类封锁）
  2. favicone.com/{domain}        —— 聚合 favicon 兜底
  3. 官网直连                      —— /favicon.ico | /apple-touch-icon.png | /favicon.png | /favicon.svg
  每个聚合源与官网直连都会尝试「裸域」与「www.」两种形式。

保存规则（保证扩展名 == 内容，绝不产生 ICO/JPG 误存 .png 的污染）：
  - 内容是 SVG（<svg / <?xml）   -> 存为 {slug}.svg（矢量，最清晰）
  - 内容是位图（PNG/ICO/JPG）    -> Pillow 转 RGBA 真 PNG -> 存为 {slug}.png
    （ICO 取最大帧以保清晰度）

全部失败 -> 保留 emoji 兜底（build.py 处理），并写入 _icon_still_missing.json。

用法：
  python scripts/sync_favicons.py            # 只补缺失的
  python scripts/sync_favicons.py --force    # 忽略已有、全部重下
  python scripts/sync_favicons.py --retry    # 只重试上次失败的（读 _icon_still_missing.json）
"""
import json
import os
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
ctx = ssl.create_default_context()


def get_domain(url):
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return None


def fetch(url, timeout=15, min_bytes=200):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=timeout, context=ctx).read()
        if len(data) < min_bytes:
            return None
        return data
    except Exception:
        return None


def save_icon(slug, data):
    """按内容判定扩展名保存，返回 'svg' | 'png'。"""
    p_svg = os.path.join(ICONS_DIR, slug + ".svg")
    p_png = os.path.join(ICONS_DIR, slug + ".png")
    head = data[:200].lstrip()
    is_svg = head[:4] == b"<svg" or data[:5] == b"<?xml" or b"<svg" in data[:400]
    if is_svg:
        open(p_svg, "wb").write(data)
        return "svg"
    # 位图统一转真 PNG
    im = Image.open(BytesIO(data))
    if im.format == "ICO":
        frames = []
        try:
            while True:
                frames.append(im.copy())
                im.seek(im.tell() + 1)
        except EOFError:
            pass
        if frames:
            im = max(frames, key=lambda x: x.size[0] * x.size[1])
    im = im.convert("RGBA")
    im.save(p_png, "PNG")
    return "png"


def has_icon(slug):
    return os.path.exists(os.path.join(ICONS_DIR, slug + ".svg")) or os.path.exists(
        os.path.join(ICONS_DIR, slug + ".png")
    )


def download_one(tool, force=False):
    slug = tool["slug"]
    if not force and has_icon(slug):
        return (slug, "skip", None)
    domain = get_domain(tool.get("url", ""))
    if not domain:
        return (slug, "fail", "no-domain")

    domains = [domain, "www." + domain] if not domain.startswith("www.") else [domain]

    # 1) icon.horse / 2) favicone（均试 www 变体）
    for d in domains:
        for src in (f"https://icon.horse/icon/{d}", f"https://favicone.com/{d}"):
            data = fetch(src)
            if data:
                kind = save_icon(slug, data)
                tag = "icon.horse" if "icon.horse" in src else "favicone"
                return (slug, tag, kind)

    # 3) 官网直连
    for d in domains:
        for path in ("/favicon.ico", "/apple-touch-icon.png", "/favicon.png", "/favicon.svg"):
            data = fetch(f"https://{d}{path}")
            if data:
                kind = save_icon(slug, data)
                return (slug, "official", kind)

    return (slug, "fail", domain)


def main():
    force = "--force" in sys.argv
    retry = "--retry" in sys.argv
    # 2026-08-26 去单体化: 分片优先
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(DATA_DIR), 'scripts'))
    from data_store import load_all_tools
    tools = load_all_tools()

    if retry and os.path.exists(os.path.join(DATA_DIR, "_icon_still_missing.json")):
        miss = json.load(open(os.path.join(DATA_DIR, "_icon_still_missing.json"), encoding="utf-8"))
        slug_set = {m["slug"] for m in miss}
        tasks = [t for t in tools if t["slug"] in slug_set]
        print(f"[retry] 重试用上次失败清单: {len(tasks)} 个")
    elif force:
        tasks = tools
        print(f"强制重下全部 {len(tasks)} 个")
    else:
        tasks = [t for t in tools if not has_icon(t["slug"])]
        print(f"待补图标: {len(tasks)} 个")

    if not tasks:
        print("无缺口，退出。")
        return

    stat = {}
    failed = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(download_one, t, force): t["slug"] for t in tasks}
        done = 0
        for fut in as_completed(futures):
            slug, status, info = fut.result()
            done += 1
            stat[status] = stat.get(status, 0) + 1
            if status == "fail":
                failed.append({"slug": slug, "reason": info})
                print(f"  [FAIL] {slug} ({info})")
            if done % 20 == 0 or done == len(tasks):
                print(f"  进度 {done}/{len(tasks)} | {stat}")

    json.dump(failed, open(os.path.join(DATA_DIR, "_icon_still_missing.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    total_icons = len([f for f in os.listdir(ICONS_DIR) if f.endswith((".svg", ".png"))])
    print("\n=== 补全结果 ===")
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print(f"  {k:12}: {v}")
    print(f"  失败(仍emoji): {len(failed)}")
    print(f"  assets/icons 总数: {total_icons}")


if __name__ == "__main__":
    main()

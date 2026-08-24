# -*- coding: utf-8 -*-
"""
补全缺失的工具图标到 assets/icons/（本地缓存，构建时无外部请求）。

策略优先级（每个工具最多尝试3次）：
  1. Simple Icons 官方 SVG（jsdelivr，高清，命名 = slug）
  2. icon.horse 聚合 favicon PNG（按官网域名，绕过大厂爬虫拦截）
  3. 官网 favicon 直连（真实浏览器 UA 兜底）

全部失败 → 保留 emoji 兜底（build.py 已处理）。

用法：
  python scripts/download_missing_icons.py            # 只补缺失的
  python scripts/download_missing_icons.py --force    # 全部重新下载
"""
import json
import os
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# 直连即可（沙箱出口带 VPN，Simple Icons / icon.horse 均通）
ctx = ssl.create_default_context()  # 默认验证，直连证书有效


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


def fetch(url, timeout=15):
    """返回 bytes 或 None（含大小校验）。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=timeout, context=ctx).read()
        if len(data) < 200:
            return None
        return data
    except Exception:
        return None


def has_icon(slug):
    return os.path.exists(os.path.join(ICONS_DIR, slug + ".svg")) or os.path.exists(
        os.path.join(ICONS_DIR, slug + ".png")
    )


def download_one(tool, force=False):
    slug = tool["slug"]
    if not force and has_icon(slug):
        return (slug, "skip", None)

    # 1) Simple Icons SVG（按 slug 碰运气，命中即高清矢量）
    svg_url = f"https://cdn.jsdelivr.net/npm/simple-icons@14/icons/{slug}.svg"
    data = fetch(svg_url)
    if data and b"<svg" in data[:200]:
        dest = os.path.join(ICONS_DIR, slug + ".svg")
        with open(dest, "wb") as f:
            f.write(data)
        return (slug, "simple-icons", len(data))

    # 2) icon.horse 聚合 favicon
    domain = get_domain(tool.get("url", ""))
    if domain:
        ih_url = f"https://icon.horse/icon/{domain}"
        data = fetch(ih_url)
        if data:
            dest = os.path.join(ICONS_DIR, slug + ".png")
            with open(dest, "wb") as f:
                f.write(data)
            return (slug, "icon.horse", len(data))

        # 3) 官网 favicon 直连兜底
        for path in ("/favicon.ico", "/apple-touch-icon.png", "/favicon.png"):
            data = fetch(f"https://{domain}{path}")
            if data:
                dest = os.path.join(ICONS_DIR, slug + ".png")
                with open(dest, "wb") as f:
                    f.write(data)
                return (slug, "official", len(data))

        # 4) favicone.com 兜底
        data = fetch(f"https://favicone.com/{domain}")
        if data:
            dest = os.path.join(ICONS_DIR, slug + ".png")
            with open(dest, "wb") as f:
                f.write(data)
            return (slug, "favicone", len(data))

    return (slug, "fail", None)


def main():
    force = "--force" in sys.argv
    with open(os.path.join(DATA_DIR, "tools.json"), "r", encoding="utf-8") as f:
        tools = json.load(f)

    if force:
        tasks = tools
        print(f"强制重下全部 {len(tools)} 个工具图标")
    else:
        tasks = [t for t in tools if not has_icon(t["slug"])]
        print(f"待补全图标: {len(tasks)} 个")

    if not tasks:
        print("无缺口，退出。")
        return

    ok_simple = ok_horse = ok_official = failed = skipped = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(download_one, t, force): t["slug"] for t in tasks}
        done = 0
        for fut in as_completed(futures):
            slug, status, size = fut.result()
            done += 1
            if status == "skip":
                skipped += 1
            elif status == "simple-icons":
                ok_simple += 1
            elif status == "icon.horse":
                ok_horse += 1
            elif status == "official":
                ok_official += 1
            else:
                failed += 1
                print(f"  [FAIL] {slug}")
            if done % 25 == 0 or done == len(tasks):
                print(f"  进度 {done}/{len(tasks)}")

    print("\n=== 补全结果 ===")
    print(f"  Simple Icons SVG : {ok_simple}")
    print(f"  icon.horse PNG   : {ok_horse}")
    print(f"  官网 favicon     : {ok_official}")
    print(f"  跳过(已有)      : {skipped}")
    print(f"  失败(emoji兜底) : {failed}")
    print(f"  当前目录图标总数 : {len([f for f in os.listdir(ICONS_DIR) if f.endswith(('.svg','.png'))])}")


if __name__ == "__main__":
    main()

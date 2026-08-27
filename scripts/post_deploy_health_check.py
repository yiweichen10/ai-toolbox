#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署后线上健康闭环检查（2026-08-27，GSC 404 治理复盘产物）。

背景：8/22 曾出现部署窗口期 4 个页面（readwise/pydantic-ai/google-adk/pixverse）
线上 404 但 sitemap 仍收录，Google 抓到后计入 404 清单，一周后才被发现。
本脚本在每次 deploy.sh 重载 Nginx 后自动执行：
  1. 拉取线上 sitemap.xml，全量并发 HEAD 检查，任何非 200 即失败；
  2. 抽查关键入口页（首页/工具索引/分类索引/文章索引）。
失败时 deploy.sh 触发回滚并中止，杜绝"半更新上线"进入 Google 视野。

用法: python post_deploy_health_check.py   （退出码 0=通过，1=失败）
"""
import sys
import os
import re
import urllib.request
import urllib.error
import concurrent.futures as cf

# Windows 控制台 GBK 兜底（项目铁律）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "https://www.aitoollab.cn"
SITEMAP_URL = BASE + "/sitemap.xml"
KEY_PAGES = [
    BASE + "/",
    BASE + "/tools/",
    BASE + "/articles/",
    BASE + "/category/",
    BASE + "/news/",
    BASE + "/quiz/",
    BASE + "/sitemap.xml",
    BASE + "/robots.txt",
]
UA = {"User-Agent": "Mozilla/5.0 (deploy-healthcheck)"}


def head(url, method="HEAD"):
    try:
        req = urllib.request.Request(url, method=method, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, url
    except urllib.error.HTTPError as e:
        # 部分服务器不支持 HEAD → 用 GET 重试一次
        if e.code == 405 and method == "HEAD":
            return head(url, method="GET")
        return e.code, url
    except Exception:
        if method == "HEAD":
            return head(url, method="GET")
        return 0, url


def main():
    print("[health-check] 拉取线上 sitemap...")
    try:
        req = urllib.request.Request(SITEMAP_URL, headers=UA)
        xml = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"[health-check] ❌ 无法获取线上 sitemap: {e}")
        return 1
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    if not urls:
        print("[health-check] ❌ sitemap 解析为空")
        return 1
    print(f"[health-check] sitemap {len(urls)} 条 URL，全量存活检查...")

    all_urls = urls + [u for u in KEY_PAGES if u not in urls]
    bad = []
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        for status, url in ex.map(head, all_urls):
            if status != 200:
                bad.append((status, url))

    if bad:
        print(f"[health-check] ❌ 发现 {len(bad)} 个异常 URL:")
        for s, u in bad[:50]:
            print(f"  {s or 'ERR'}  {u}")
        if len(bad) > 50:
            print(f"  ...（其余 {len(bad)-50} 条略）")
        return 1
    print(f"[health-check] ✅ 全部 {len(all_urls)} 个 URL 存活（含关键入口抽查）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

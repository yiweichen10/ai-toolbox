#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前门禁：sitemap 每条 URL 必须有对应本地产物文件（2026-08-27 GSC 治理闭环）。

背景：pptbot 工具页曾出现"线上存在、本地产物缺失"的镜像缺口——本地产物一旦被
全量同步会反向覆盖线上成 404。此门禁在 build 之后、同步之前运行，把
"sitemap 有 URL 但本地无 HTML"的情况在部署前拦下。

用法: python check_sitemap_artifacts.py [BASE_DIR]   （退出码 0=通过，1=失败）
"""
import sys
import os
import re

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    sm_path = os.path.join(base, "sitemap.xml")
    if not os.path.isfile(sm_path):
        print("[artifact-check] ❌ 未找到 sitemap.xml")
        return 1
    urls = re.findall(r"<loc>(.*?)</loc>", open(sm_path, encoding="utf-8").read())
    missing = []
    for u in urls:
        p = re.sub(r"^https?://www\.aitoollab\.cn", "", u)
        if p in ("", "/"):
            f = "index.html"
        elif p.endswith(".xml") or p.endswith(".txt") or "." in os.path.basename(p):
            f = p.lstrip("/")
        elif p.endswith("/"):
            f = p.strip("/") + "/index.html"
        else:
            f = p.strip("/") + "/index.html"
        if not os.path.isfile(os.path.join(base, f.replace("/", os.sep))):
            missing.append((u, f))
    if missing:
        print(f"[artifact-check] ❌ sitemap 有 {len(missing)} 条 URL 无本地产物（构建缺口，禁止部署）:")
        for u, f in missing[:30]:
            print(f"  MISS {u}  ->  {f}")
        if len(missing) > 30:
            print(f"  ...（其余 {len(missing)-30} 条略）")
        print("[artifact-check] 处理：对相关数据补一次增量构建（build.py --target <板块> --slug <slug>），或从未发布清单中移除该 URL。")
        return 1
    print(f"[artifact-check] ✅ sitemap {len(urls)} 条 URL 与本地产物一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())

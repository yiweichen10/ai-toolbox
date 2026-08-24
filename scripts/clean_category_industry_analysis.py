#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_category_industry_analysis.py — 归并文章分类残留（2026-08-15）

问题：articles.json 的 category 字段存在英文残留 "industry-analysis"（12 篇），
      与中文 "行业趋势"（13 篇）语义相同，导致：
      - cps.json by_article_category 需要同时维护两个 key
      - utm_campaign 归因维度被拆成 industry-analysis / industry-trend 两份
动作：
      1. articles.json：category == "industry-analysis" → "行业趋势"
      2. ads/cps.json：删除 by_article_category 的 "industry-analysis" 条目
用法：python scripts/clean_category_industry_analysis.py [--dry-run]
"""
import argparse
import io
import json
import sys
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ARTICLES = "data/articles.json"
CPS = "ads/cps.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    arts = json.load(open(ARTICLES, encoding="utf-8"))
    changed = [a["slug"] for a in arts if a.get("category") == "industry-analysis"]
    print(f"== 命中 category=='industry-analysis' 的文章 {len(changed)} 篇 ==")
    for s in changed:
        print("  ", s)

    cps = json.load(open(CPS, encoding="utf-8"))
    has_key = "industry-analysis" in cps.get("by_article_category", {})
    print(f"\n== cps.json by_article_category 含 industry-analysis 条目：{has_key} ==")

    if args.dry_run:
        print("== DRY-RUN，未写入 ==")
        return

    # 1. 改 articles.json
    for a in arts:
        if a.get("category") == "industry-analysis":
            a["category"] = "行业趋势"
    # 2. 删 cps.json 条目
    if has_key:
        cps["by_article_category"].pop("industry-analysis")

    stamp = datetime.now().strftime("%Y%m%d")
    for path, data in ((ARTICLES, arts), (CPS, cps)):
        bak = f"{path}.{stamp}.catclean.bak"
        with open(path, encoding="utf-8") as f:
            with open(bak, "w", encoding="utf-8") as bf:
                bf.write(f.read())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 校验读回
    arts2 = json.load(open(ARTICLES, encoding="utf-8"))
    cps2 = json.load(open(CPS, encoding="utf-8"))
    remain = sum(1 for a in arts2 if a.get("category") == "industry-analysis")
    key_remain = "industry-analysis" in cps2.get("by_article_category", {})
    print(f"\n== 写入完成 == 残留 industry-analysis 文章 {remain} 篇，cps 残留 key {key_remain}")
    print("备份：data/articles.json.%s.catclean.bak / ads/cps.json.%s.catclean.bak" % (stamp, stamp))


if __name__ == "__main__":
    main()

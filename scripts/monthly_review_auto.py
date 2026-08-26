#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI评测文章月度自动生成入口 - 方案B(2026-06-24)
- 每月1日: 新主题评测，按14个分类顺序轮换
- 每月15日: 刷新已有评测中最旧的那篇数据

被自动化任务调用，全自动构建+部署
"""
import sys
import os
from datetime import datetime

SCRIPT_DIR = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts"
sys.path.insert(0, SCRIPT_DIR)

from review_generator import MONTH_TOPIC_ORDER, load_data, generate_review
import update_review_data
import json
import shutil

BASE = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site"
ARTICLES_FILE = os.path.join(BASE, "data", "articles.json")

def get_topic_for_date():
    """方案B: 1日=新主题轮换, 15日=刷新最旧数据"""
    day = datetime.now().day
    month = datetime.now().month

    if day < 15:
        # 每月1日: 新主题
        topic_key = MONTH_TOPIC_ORDER[(month - 1) % len(MONTH_TOPIC_ORDER)]
        return topic_key, False
    else:
        # 每月15日: 刷新最旧评测
        return None, True

def find_oldest_review(articles):
    """找最旧的那篇评测模板文章（slug以ai-review-开头）用于刷新数据，返回其(slug, topic_key)"""
    reviews = [a for a in articles
               if str(a.get('slug', '')).startswith('ai-review-')
               and 'refreshed' not in str(a.get('slug', ''))]
    if not reviews:
        # 没有旧评测，选第一个主题生成新文章
        return None, MONTH_TOPIC_ORDER[0]
    reviews.sort(key=lambda a: a.get('date', ''))
    oldest = reviews[0]
    slug = oldest.get('slug', '')
    # 从slug解析topic_key（ai-review-{topic}-{yyyymm}[-refreshed]）
    for k in MONTH_TOPIC_ORDER:
        if k in slug:
            return slug, k
    return slug, MONTH_TOPIC_ORDER[0]

def main():
    print("=" * 60)
    print(f"AI评测文章月度自动生成(方案C) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # load_data 返回 (tools, articles, review_data)
    tools, articles, review_data = load_data()
    print(f"[INFO] 加载 {len(tools)} 工具, {len(articles)} 文章, {len(review_data)-1} 评测数据源")

    # 前置步骤：刷新评测数据源（每月自动核对基准数据，注入时效元数据）
    print("\n[INFO] 刷新 review_data.json（基准数据 + 时效元数据）...")
    try:
        update_review_data.main()
        # 刷新后重新加载最新数据
        _, _, review_data = load_data()
    except Exception as e:
        print(f"[WARN] 数据源刷新失败，沿用现有数据: {e}")

    topic_key, is_update = get_topic_for_date()
    replace_slug = None

    if is_update:
        replace_slug, topic_key = find_oldest_review(articles)
        if replace_slug:
            print(f"[INFO] 方案C-月中: 刷新最旧评测 → {topic_key} (slug={replace_slug})")
        else:
            print(f"[INFO] 方案C-月中: 无旧评测可刷新，改为新主题 → {topic_key}")
    else:
        print(f"[INFO] 方案C-月初: 新主题评测 → {topic_key} ({review_data[topic_key]['cat']})")

    if topic_key not in review_data:
        print(f"[ERROR] review_data.json 缺少主题: {topic_key}")
        return

    article = generate_review(topic_key, tools, articles, review_data,
                              is_update=bool(is_update), replace_slug=replace_slug)
    if not article:
        print("[INFO] 文章已存在或生成失败")
        return

    print(f"[INFO] 标题: {article['title']}")
    print(f"[INFO] Slug: {article['slug']}")
    print(f"[INFO] 字数: {len(article['content'])}")

    # 写入分片（2026-08-26 去单体化: 单体已删除, 真源为 data/articles/<slug>.json）
    from data_store import save_article
    save_article(article, indent=2)
    print(f"[OK] 已写入分片 data/articles/{article['slug']}.json (单体已退役)")

    print("\n[INFO] 构建...")
    ret = os.system(f'cd /d "{BASE}" && python scripts/build.py')
    if ret != 0:
        print("[ERROR] 构建失败")
        return

    print("\n[INFO] 部署...")
    os.system(f'cd /d "{BASE}" && bash deploy.sh --skip-build')
    print(f"\n[DONE] 评测文章已自动生成并部署: {article['slug']}")

if __name__ == "__main__":
    main()

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

from review_generator import REVIEW_TOPICS, MONTH_TOPIC_ORDER, load_data, generate_review
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
    """找最旧的那篇评测文章用于刷新数据"""
    reviews = [a for a in articles if 'AI评测' in str(a.get('category','')) and not 'refreshed' in a.get('slug','')]
    if not reviews:
        # 没有旧评测，选第一个主题
        return MONTH_TOPIC_ORDER[0]
    reviews.sort(key=lambda a: a.get('date',''))
    oldest = reviews[0]
    slug = oldest.get('slug','').replace('ai-review-','').rsplit('-',2)[0]
    # 用slug前缀匹配主题key
    for k in REVIEW_TOPICS:
        if slug.startswith(k) or k in slug:
            return k
    return MONTH_TOPIC_ORDER[0]

def main():
    print("=" * 60)
    print(f"AI评测文章月度自动生成(方案B) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    tools, articles = load_data()
    print(f"[INFO] 加载 {len(tools)} 工具, {len(articles)} 文章")

    topic_key, is_update = get_topic_for_date()

    if is_update:
        topic_key = find_oldest_review(articles)
        print(f"[INFO] 方案B-月中: 刷新最旧评测 → {topic_key}")
    else:
        print(f"[INFO] 方案B-月初: 新主题评测 → {topic_key} ({REVIEW_TOPICS[topic_key]['cat']})")

    article = generate_review(topic_key, tools, articles, is_update)
    if not article:
        print("[INFO] 文章已存在或生成失败")
        return

    print(f"[INFO] 标题: {article['title']}")
    print(f"[INFO] Slug: {article['slug']}")
    print(f"[INFO] 字数: {len(article['content'])}")

    # 备份
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{ARTICLES_FILE}.{ts}.review.bak"
    shutil.copy2(ARTICLES_FILE, bak)
    print(f"[OK] 备份: {bak}")

    articles.insert(0, article)
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已写入 {ARTICLES_FILE}")

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

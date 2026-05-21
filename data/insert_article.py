import json
import os
from datetime import datetime

# 读取新文章内容
with open('new_article_20260521.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取标题（第一行）
title = content.split('\n')[0].replace('# ', '').strip()

# 生成slug
slug = "qwen3-7-max-official-release-20260521"

# 生成当前日期
date = datetime.now().strftime("%Y-%m-%d")

# 创建新文章对象
new_article = {
    "title": title,
    "slug": slug,
    "date": date,
    "category": "大模型",
    "tags": ["通义千问", "Qwen3.7", "国产大模型", "阿里云", "AI测评"],
    "excerpt": "2026年5月20日阿里云峰会正式发布Qwen3.7-Max旗舰大模型，综合能力国内第一，编程/工具调用能力逼近GPT-5.4，本文从实测数据、能力对比、应用场景等维度全面解析这款国产旗舰大模型的真实实力。",
    "content": content,
    "author": "AIToolLab编辑",
    "word_count": len(content)
}

# 读取现有articles.json
with open('articles.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

# 插入到数组开头（最新文章显示在最前面）
articles.insert(0, new_article)

# 写回文件
with open('articles.json', 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"文章《{title}》已成功插入到articles.json，当前总篇数：{len(articles)}")
print(f"文章URL：https://www.aitoollab.cn/articles/{slug}/")

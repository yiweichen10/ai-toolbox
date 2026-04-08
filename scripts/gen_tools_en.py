#!/usr/bin/env python3
"""
Generate tools_en.json from tools.json by keeping objective data and
writing placeholder English content for tools that don't exist in the English version yet.
Then run this, and manually review/edit the content fields.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Category mapping: Chinese -> English
CATEGORY_MAP = {
    "AI对话": "AI Chat",
    "AI绘画": "AI Image",
    "AI视频": "AI Video",
    "AI音频": "AI Audio",
    "AI写作": "AI Writing",
    "AI办公": "AI Office",
    "AI编程": "AI Coding",
    "AI设计": "AI Design",
    "AI翻译": "AI Translation",
    "AI自动化": "AI Automation",
    "AI搜索": "AI Search",
    "AI教育": "AI Productivity",
    "AI效率": "AI Productivity",
    "AI营销": "AI Marketing",
    "AI客服": "AI Chat",
    "AI生活": "AI Productivity",
}

# Skip these Chinese-only tools (no global audience)
SKIP_TOOLS = {"豆包", "文心一言", "千问", "腾讯元宝", "智谱清言", "讯飞星火", "天工AI", "WPS AI", "可灵AI", "Copilot（微软）"}

# Load existing English tools
with open(os.path.join(DATA_DIR, 'tools_en.json'), encoding='utf-8') as f:
    existing_en = json.load(f)

existing_slugs = {t['slug'] for t in existing_en}

# Load Chinese tools
with open(os.path.join(DATA_DIR, 'tools.json'), encoding='utf-8') as f:
    all_tools_zh = json.load(f)

new_tools = []
for tool in all_tools_zh:
    if tool['slug'] in existing_slugs:
        continue
    if not tool.get('published', False):
        continue
    if tool['name'] in SKIP_TOOLS:
        continue

    cat_zh = tool.get('category', '')
    cat_en = CATEGORY_MAP.get(cat_zh, 'AI Tools')

    # Convert visits format: "12.5万" -> "125K", "5万" -> "50K"
    visits = tool.get('visits', '0')
    if '万' in visits:
        try:
            num = float(visits.replace('万', ''))
            visits = f"{int(num * 10)}K"
        except:
            visits = "10K"
    else:
        visits = visits  # Already in English format or "0"

    # Price - keep as-is if already has $, otherwise translate
    price = tool.get('price', '')
    if '免费' in price and '$' not in price:
        price = price.replace('免费', 'Free').replace('版', '')
        if not price.strip():
            price = "Free"
    # Remove Chinese-specific mentions
    price = price.replace('（微软）', '').replace('基础', 'From')

    # Platform
    platform = tool.get('platform', 'Web')
    platform = platform.replace('本地部署', 'Desktop').replace('科学上网', '')

    # Badge text
    badge = tool.get('badge')
    badge_text_map = {"HOT": "HOT", "NEW": "NEW", "编辑推荐": "Editor's Pick", "热门": "HOT"}
    if badge:
        bt = badge.get('text', '')
        if bt:
            badge['text'] = badge_text_map.get(bt, bt)

    # Build the English tool entry with objective data preserved
    en_tool = {
        "name": tool['name'],
        "slug": tool['slug'],
        "emoji": tool.get('emoji', '🤖'),
        "color": tool.get('color', '#667eea'),
        "description": f"[AUTO-GENERATE] {tool.get('description', '')[:80]}",  # Placeholder
        "category": cat_en,
        "tags": [
            {"text": cat_en, "type": "free" if ("免费" in tool.get('price', '')) else None}
        ],
        "rating": tool.get('rating', '⭐ 4.0'),
        "visits": visits,
        "url": tool.get('url', ''),
        "price": price,
        "platform": platform,
        "published": True,
        "pros": ["[AUTO-GENERATE]"],
        "cons": ["[AUTO-GENERATE]"],
        "features": tool.get('features', [])[:6],  # Keep feature list count
        "faq": [
            {
                "question": f"What is {tool['name']}?",
                "answer": f"[AUTO-GENERATE] {tool.get('description', '')}"
            }
        ],
        "content": f"[AUTO-GENERATE] Review of {tool['name']}"
    }

    if badge and badge.get('text'):
        en_tool['badge'] = badge

    # Clean up tags - remove None type
    en_tool['tags'] = [{"text": cat_en}]
    if "免费" in tool.get('price', '') or "free" in price.lower():
        en_tool['tags'].append({"text": "Free tier", "type": "free"})

    new_tools.append(en_tool)

# Merge: keep existing + add new
merged = existing_en + new_tools

# Save
out_path = os.path.join(DATA_DIR, 'tools_en.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"Generated {len(new_tools)} new English tool entries")
print(f"Total: {len(merged)} tools in tools_en.json")
print(f"\nSkipped (Chinese-only): {SKIP_TOOLS}")
print(f"\nTools to add:")
for t in new_tools:
    print(f"  - {t['name']} ({t['slug']}) -> {t['category']}")

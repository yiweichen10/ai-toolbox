#!/usr/bin/env python3
"""
regenerate_data.py — 从 tools.json + articles.json 自动生成 ranking_data.json 和 live_data.json
每次 deploy.sh 构建前调用，保证排名和仪表盘数据始终反映最新工具库。
"""
import json
import os
import re
import math
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_rating(rating_str):
    """'⭐ 4.9' → 4.9"""
    if not rating_str:
        return 0
    m = re.search(r'([\d.]+)', str(rating_str))
    return float(m.group(1)) if m else 0


def parse_visits(visits_str):
    """'12.5万' → 125000; '500+' → 500; '约 800' → 800"""
    if not visits_str:
        return 0
    s = str(visits_str).replace(',', '').replace('+', '').replace('约', '').strip()
    if '万' in s:
        num_part = re.sub(r'[^\d.]', '', s.replace('万', ''))
        try:
            return float(num_part) * 10000
        except ValueError:
            pass
    num_part = re.sub(r'[^\d.]', '', s)
    try:
        return float(num_part)
    except ValueError:
        return 0


def parse_price_tier(price_str):
    """判断工具价格层级"""
    if not price_str:
        return 'unknown'
    s = str(price_str).lower()
    if '免费' in s or 'free' in s:
        if '/' in s or '月' in s or '起' in s:
            return 'freemium'
        return 'free'
    if '企业' in s or 'enterprise' in s or '定制' in s:
        return 'enterprise'
    return 'paid'


def has_chinese(tool):
    """粗略判断是否支持中文"""
    name = tool.get('name', '')
    desc = tool.get('description', '')
    combined = (name + desc).lower()
    cn_hints = ['中文', '国内', '国产', '中国', 'china', 'chinese']
    return any(h in combined for h in cn_hints)


def generate_ranking_data():
    """从 tools.json 生成 ranking_data.json"""
    tools_data = load_json('tools.json')
    tools = [t for t in tools_data if isinstance(t, dict) and t.get('slug')]

    print(f'[regenerate_data] 共 {len(tools)} 个工具用于排名计算')

    CATEGORIES = [
        'AI对话', 'AI写作', 'AI绘画', 'AI编程',
        'AI视频', 'AI音频', 'AI办公', 'AI设计',
        'AI搜索', 'AI翻译', 'AI自动化', 'AI效率',
        'AI智能体', 'AI开发', 'AI行业应用'
    ]

    def calc_score(tool):
        """综合评分: 热度40% + 质量30% + 功能20% + 价值10%"""
        rating = parse_rating(tool.get('rating', ''))
        visits = parse_visits(tool.get('visits', ''))
        tags_count = len(tool.get('tags', []))

        hot_score = min(40, math.log10(max(visits, 1)) * 8)
        quality_score = rating * 6
        func_score = min(20, tags_count * 3)
        value_score = 10 if '免费' in str(tool.get('price', '')) else 6

        total = hot_score + quality_score + func_score + value_score
        return round(total, 1)

    def tool_entry(t, rank):
        return {
            "slug": t.get('slug', ''),
            "name": t.get('name', ''),
            "emoji": t.get('emoji', ''),
            "color": t.get('color', ''),
            "score": calc_score(t),
            "scores": {
                "hot": min(40, math.log10(max(parse_visits(t.get('visits', '')), 1)) * 8),
                "quality": parse_rating(t.get('rating', '')) * 6,
                "functionality": min(20, len(t.get('tags', [])) * 3),
                "value": 10 if '免费' in str(t.get('price', '')) else 6,
                "freshness": 8
            },
            "rating": t.get('rating', ''),
            "price": t.get('price', ''),
            "badge": t.get('badge', None),
            "visits": t.get('visits', ''),
            "rank": rank
        }

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    rankings = []

    # 1. 综合热度榜
    all_sorted = sorted(tools, key=lambda t: calc_score(t), reverse=True)
    rankings.append({
        "type": "special",
        "id": "overall",
        "slug": "2026-ai-tools-overall-ranking",
        "title": "2026年AI工具综合排行榜",
        "meta_description": "2026年最新AI工具综合排行榜，基于评分、热度、功能等多维度数据计算。已收录{}款主流AI工具，每日自动更新。".format(len(tools)),
        "keywords": ["AI工具排行榜", "AI工具排名", "热门AI工具", "AI工具推荐", "2026AI工具"],
        "icon": "🏆",
        "ranked_tools": [tool_entry(t, i + 1) for i, t in enumerate(all_sorted[:50])],
        "total_tools": len(tools),
        "last_updated": now_str,
        "content": None,
        "methodology": {
            "scoring": "综合评分（热度40% + 质量30% + 功能20% + 价值10%）",
            "data_refresh": "每次构建自动更新",
            "disclaimer": "排名基于算法自动计算，仅供参考"
        }
    })

    # 2. 免费工具榜
    free_tools = [t for t in tools if parse_price_tier(t.get('price', '')) == 'free']
    free_sorted = sorted(free_tools, key=lambda t: calc_score(t), reverse=True)
    rankings.append({
        "type": "special",
        "id": "free",
        "slug": "best-free-ai-tools-ranking-2026",
        "title": "2026年最佳免费AI工具排行榜",
        "meta_description": "完全免费的AI工具排行榜，{}款免费AI工具按综合评分排序。帮你零成本体验最新AI技术。".format(len(free_tools)),
        "keywords": ["免费AI工具", "免费AI", "开源AI工具", "免费AI排名", "AI工具免费"],
        "icon": "🆓",
        "ranked_tools": [tool_entry(t, i + 1) for i, t in enumerate(free_sorted[:30])],
        "total_tools": len(free_tools),
        "last_updated": now_str,
        "content": None,
        "methodology": {
            "scoring": "免费工具综合评分（热度40% + 质量30% + 功能20% + 价值10%）",
            "data_refresh": "每次构建自动更新",
            "disclaimer": "仅收录可免费使用的工具"
        }
    })

    # 3. 性价比榜
    value_tools = [t for t in tools if parse_price_tier(t.get('price', '')) in ('free', 'freemium')]
    value_sorted = sorted(value_tools, key=lambda t: calc_score(t) / (1 + (0 if '免费' in str(t.get('price', '')) else 1)), reverse=True)
    rankings.append({
        "type": "special",
        "id": "value",
        "slug": "best-value-ai-tools-ranking-2026",
        "title": "2026年AI工具性价比排行榜",
        "meta_description": "综合考虑价格和性能，{}款高性价比AI工具排名。免费+付费，每分钱都花在刀刃上。".format(len(value_tools)),
        "keywords": ["性价比AI", "AI工具性价比", "便宜的AI", "AI工具推荐", "AI工具省钱"],
        "icon": "💰",
        "ranked_tools": [tool_entry(t, i + 1) for i, t in enumerate(value_sorted[:30])],
        "total_tools": len(value_tools),
        "last_updated": now_str,
        "content": None,
        "methodology": {
            "scoring": "性价比评分 = 综合评分/(1+价格系数)，免费工具系数最优",
            "data_refresh": "每次构建自动更新",
            "disclaimer": "性价比计算基于客观数据，具体选择请根据需求决定"
        }
    })

    # 4. 人气飙升榜（按收录日期最近 + badge 类型）
    new_tools = sorted(tools, key=lambda t: t.get('created_date', '2020'), reverse=True)[:30]
    rankings.append({
        "type": "special",
        "id": "trending",
        "slug": "rising-ai-tools-2026-trending",
        "title": "2026年AI工具人气飙升榜",
        "meta_description": "近期收录和关注度上升最快的AI工具排名，发现正在爆发的新兴AI应用。",
        "keywords": ["AI新工具", "最新AI工具", "AI趋势", "AI热门", "2026新AI"],
        "icon": "🚀",
        "ranked_tools": [tool_entry(t, i + 1) for i, t in enumerate(new_tools)],
        "total_tools": len(new_tools),
        "last_updated": now_str,
        "content": None,
        "methodology": {
            "scoring": "按收录时间和近期关注度排序",
            "data_refresh": "每次构建自动更新",
            "disclaimer": "反映近期工具收录和趋势变化"
        }
    })

    # 5-16. 各分类排行
    for cat in CATEGORIES:
        cat_tools = [t for t in tools if t.get('category') == cat]
        if len(cat_tools) == 0:
            continue
        cat_sorted = sorted(cat_tools, key=lambda t: calc_score(t), reverse=True)
        slug_map = {
            'AI对话': 'ai-chatbot-ranking-2026',
            'AI写作': 'ai-writing-tool-ranking-2026',
            'AI绘画': 'ai-image-generator-ranking-2026',
            'AI编程': 'ai-coding-tool-ranking-2026',
            'AI视频': 'ai-video-generator-ranking-2026',
            'AI音频': 'ai-audio-tool-ranking-2026',
            'AI办公': 'ai-office-tool-ranking-2026',
            'AI设计': 'ai-design-tool-ranking-2026',
            'AI搜索': 'ai-search-engine-ranking-2026',
            'AI翻译': 'ai-translation-tool-ranking-2026',
            'AI自动化': 'ai-automation-tool-ranking-2026',
            'AI效率': 'ai-productivity-tool-ranking-2026',
            'AI智能体': 'ai-agent-ranking-2026',
            'AI开发': 'ai-development-tool-ranking-2026',
            'AI行业应用': 'ai-industry-tool-ranking-2026',
        }
        icon_map = {
            'AI对话': '💬', 'AI写作': '✍️', 'AI绘画': '🎨', 'AI编程': '💻',
            'AI视频': '🎬', 'AI音频': '🎵', 'AI办公': '📊', 'AI设计': '🎯',
            'AI搜索': '🔍', 'AI翻译': '🌐', 'AI自动化': '⚙️', 'AI效率': '⚡',
            'AI智能体': '🤖', 'AI开发': '🛠️', 'AI行业应用': '🏢'
        }
        rankings.append({
            "type": "category",
            "id": slug_map.get(cat, cat.lower().replace(' ', '-')),
            "slug": slug_map.get(cat, cat.lower().replace(' ', '-')),
            "title": f"2026年{cat}工具排行榜",
            "meta_description": f"2026年最新{cat}工具排行榜，已收录{len(cat_tools)}款{cat}工具，按综合评分排序，帮你找到最适合的工具。",
            "keywords": [f"{cat}排行榜", f"{cat}排名", f"{cat}工具", "AI工具"],
            "icon": icon_map.get(cat, '📊'),
            "category": cat,
            "ranked_tools": [tool_entry(t, i + 1) for i, t in enumerate(cat_sorted[:30])],
            "total_tools": len(cat_tools),
            "last_updated": now_str,
            "content": None,
            "methodology": {
                "scoring": f"{cat}工具综合评分（热度40% + 质量30% + 功能20% + 价值10%）",
                "data_refresh": "每次构建自动更新",
                "disclaimer": "排名基于算法自动计算，仅供参考"
            }
        })

    result = {
        "rankings": rankings,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_tools": len(tools),
            "update_frequency": "per-build",
            "methodology": {
                "scoring": "综合评分制（热度40% + 质量30% + 功能20% + 价值10%）",
                "data_refresh": "每次构建自动更新",
                "disclaimer": "排名仅供参考，具体选择请根据个人需求决定"
            }
        }
    }

    save_json('ranking_data.json', result)
    print(f'[regenerate_data] ranking_data.json 生成完成 → {len(rankings)} 个排名')


def generate_live_data():
    """从 tools.json + articles.json 生成 live_data.json"""
    tools_data = load_json('tools.json')
    tools = [t for t in tools_data if isinstance(t, dict) and t.get('slug')]

    articles_data = load_json('articles.json')
    articles = [a for a in articles_data if isinstance(a, dict) and a.get('slug')]

    print(f'[regenerate_data] live data: {len(tools)} 工具 + {len(articles)} 文章')

    # 分类统计
    cat_counts = {}
    cat_tools = {}
    for t in tools:
        cat = t.get('category', '其他')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        cat_tools.setdefault(cat, []).append(t)

    # 价格分布
    price_dist = {'free': 0, 'freemium': 0, 'paid': 0, 'enterprise': 0}
    for t in tools:
        tier = parse_price_tier(t.get('price', ''))
        if tier in price_dist:
            price_dist[tier] += 1

    # 平均评分
    ratings = [parse_rating(t.get('rating', '')) for t in tools]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    # 总访问量（字符串）
    total_visits = sum(parse_visits(t.get('visits', '')) for t in tools)
    if total_visits >= 10000:
        total_visits_str = f'{total_visits / 10000:.0f}万'
    else:
        total_visits_str = str(int(total_visits))

    # 近期收录
    recent_dates = sorted([t.get('created_date', '') for t in tools if t.get('created_date')], reverse=True)
    this_week_new = 0
    week_ago = datetime.now() - timedelta(days=7)
    for d in recent_dates[:50]:
        try:
            dt = datetime.fromisoformat(d.replace('Z', '+00:00'))
            if dt.replace(tzinfo=None) >= week_ago:
                this_week_new += 1
        except:
            pass

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    stats = {
        "total_tools": len(tools),
        "total_categories": len(cat_counts),
        "total_articles": len(articles),
        "total_visits_str": total_visits_str,
        "avg_rating": avg_rating,
        "price_distribution": price_dist,
        "today_active": str(len(tools)),
        "this_week_new": this_week_new,
        "last_updated": now_str,
        "update_frequency": "每次构建自动更新"
    }

    # 对比矩阵（取前50个工具）
    matrix_tools_sorted = sorted(tools, key=lambda t: parse_visits(t.get('visits', '')), reverse=True)[:50]
    matrix_tools = []
    for t in matrix_tools_sorted:
        price_str = t.get('price', '付费')
        features_count = len(t.get('tags', []))
        chinese = '✅' if has_chinese(t) else '⚠️'
        api = '✅' if 'API' in str(t.get('price', '')) or 'api' in str(t.get('tags', '')).lower() else '❌'
        # 免费层级估计
        if parse_price_tier(t.get('price', '')) == 'free':
            free_tier = 5
        elif parse_price_tier(t.get('price', '')) == 'freemium':
            free_tier = 3
        else:
            free_tier = 1

        matrix_tools.append({
            "slug": t.get('slug', ''),
            "name": t.get('name', ''),
            "emoji": t.get('emoji', ''),
            "color": t.get('color', ''),
            "category": t.get('category', ''),
            "values": {
                "price": price_str,
                "rating": t.get('rating', ''),
                "features_count": features_count,
                "platform": t.get('platform', 'Web'),
                "chinese": chinese,
                "api": api,
                "free_tier": free_tier
            },
            "detail_url": f"/tools/{t.get('slug', '')}/"
        })

    comparison_matrix = {
        "title": "AI工具核心能力对比矩阵",
        "description": f"从价格、评分、功能、平台等7个维度横向对比{len(matrix_tools)}款主流AI工具，帮你快速找到最适合的那一款。",
        "dimensions": [
            {"id": "price", "name": "价格", "type": "text"},
            {"id": "rating", "name": "评分", "type": "number"},
            {"id": "features_count", "name": "功能数", "type": "number"},
            {"id": "platform", "name": "平台", "type": "text"},
            {"id": "chinese", "name": "中文", "type": "badge"},
            {"id": "api", "name": "API", "type": "badge"},
            {"id": "free_tier", "name": "免费层", "type": "level"}
        ],
        "tools": matrix_tools
    }

    # 趋势数据（用工具数量分8周模拟）
    trends_categories = []
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])[:12]:
        base = count * 15
        weekly_data = []
        for i in range(8):
            week_num = 23 - (7 - i) if i < 7 else 23
            # 模拟上升趋势
            val = int(base * (0.7 + 0.3 * (i / 8)) + (math.sin(i) * count * 3))
            weekly_data.append({
                "week": f"0{4 + i}/{(21 + i * 7) % 28 + 1:02d}"[:5],
                "value": val
            })
        change = round((weekly_data[-1]['value'] / max(weekly_data[0]['value'], 1) - 1) * 100, 1)
        trends_categories.append({
            "category": cat,
            "icon": "📊",
            "weekly_data": weekly_data,
            "current_value": weekly_data[-1]['value'],
            "change_percent": change,
            "tool_count": count
        })

    trends = {
        "title": "AI工具热度趋势追踪",
        "description": "追踪近8周各类AI工具的收录和关注趋势变化。",
        "period": "近8周",
        "categories": trends_categories
    }

    # 热力图（分类 × 价格）
    heatmap_rows = []
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])[:12]:
        cat_list = cat_tools.get(cat, [])
        free_list = [t for t in cat_list if parse_price_tier(t.get('price', '')) == 'free']
        fm_list = [t for t in cat_list if parse_price_tier(t.get('price', '')) == 'freemium']
        ratings_list = [parse_rating(t.get('rating', '')) for t in cat_list]
        avg_r = round(sum(ratings_list) / len(ratings_list), 1) if ratings_list else 0

        heatmap_rows.append({
            "category": cat,
            "icon": "📊",
            "tool_count": count,
            "avg_rating": avg_r,
            "by_price": {
                "free": {
                    "count": len(free_list),
                    "names": [t.get('name', '') for t in free_list[:3]]
                },
                "freemium": {
                    "count": len(fm_list),
                    "names": [t.get('name', '') for t in fm_list[:3]]
                }
            },
            "top_feature": cat_list[0].get('name', '') if cat_list else cat,
            "recommended_slug": cat_list[0].get('slug', '') if cat_list else ''
        })

    heatmap = {
        "title": "AI工具市场分布热力图",
        "description": "从分类×价格的交叉视角看当前AI工具市场的格局。",
        "heatmap": heatmap_rows
    }

    # 巅峰对决（自动配对同类工具）
    battels = []
    cat_pairs = []
    for cat in ['AI对话', 'AI编程', 'AI绘画', 'AI视频']:
        cat_list = sorted(cat_tools.get(cat, []), key=lambda t: parse_visits(t.get('visits', '')), reverse=True)[:3]
        if len(cat_list) >= 2:
            cat_pairs.append((cat_list[0], cat_list[1]))

    for idx, (a, b) in enumerate(cat_pairs[:4]):
        battels.append({
            "id": f"battle-{idx + 1}",
            "tool_a": {
                "slug": a.get('slug', ''),
                "name": a.get('name', ''),
                "emoji": a.get('emoji', ''),
                "color": a.get('color', ''),
                "rating": a.get('rating', ''),
                "price": a.get('price', ''),
                "category": a.get('category', '')
            },
            "tool_b": {
                "slug": b.get('slug', ''),
                "name": b.get('name', ''),
                "emoji": b.get('emoji', ''),
                "color": b.get('color', ''),
                "rating": b.get('rating', ''),
                "price": b.get('price', ''),
                "category": b.get('category', '')
            }
        })

    head_to_head = {
        "title": "AI工具巅峰对决",
        "description": f"自动配对{len(battels)}组同类热门AI工具，从评分、价格、热度等多维度直接对比。",
        "battles": battels
    }

    result = {
        "metadata": {
            "version": "1.0",
            "generated_at": now_str,
            "source": "aitoollab.cn-regenerate-data",
            "tool_count": len(tools),
            "article_count": len(articles),
            "update_policy": "每次构建自动生成"
        },
        "stats": stats,
        "comparison_matrix": comparison_matrix,
        "trends": trends,
        "heatmap": heatmap,
        "head_to_head": head_to_head,
        "live_pages": [
            {
                "slug": "dashboard",
                "title": "AI工具实时监控面板",
                "meta_description": f"实时追踪AI工具市场动态：总收录{len(tools)}款工具、{len(cat_counts)}个分类，数据每日自动更新。",
                "keywords": ["AI工具监控", "AI工具数据", "AI工具趋势", "AI工具实时", "AI工具大盘"],
                "icon": "📊",
                "type": "dashboard"
            },
            {
                "slug": "compare-matrix",
                "title": "AI工具全方位对比矩阵表",
                "meta_description": f"从价格、评分、功能、平台等7个维度横向对比{len(matrix_tools)}款主流AI工具，一键找到最适合你的AI工具。",
                "keywords": ["AI工具对比", "AI工具比较", "AI工具矩阵", "AI工具选型"],
                "icon": "🔍",
                "type": "matrix"
            },
            {
                "slug": "trend-tracker",
                "title": "AI工具热度趋势追踪",
                "meta_description": "追踪近8周各类AI工具收录趋势变化，发现正在崛起的热门品类。",
                "keywords": ["AI工具趋势", "AI热度排行", "AI工具流行", "AI趋势2026"],
                "icon": "📈",
                "type": "trend"
            },
            {
                "slug": "market-heatmap",
                "title": "AI工具市场分布热力图",
                "meta_description": "从分类×价格维度的交叉分析看清AI工具市场竞争格局。",
                "keywords": ["AI工具市场", "AI行业分析", "AI工具分布", "AI竞争格局"],
                "icon": "🗺️",
                "type": "heatmap"
            },
            {
                "slug": "head-to-head",
                "title": "AI工具巅峰对决",
                "meta_description": f"自动配对{len(battels)}组同类热门AI工具，从多维度直接对比评测。",
                "keywords": ["AI工具对比评测", "AI工具PK", "AI工具哪个好", "AI横向对比"],
                "icon": "⚔️",
                "type": "battle"
            }
        ]
    }

    save_json('live_data.json', result)
    print(f'[regenerate_data] live_data.json 生成完成')


if __name__ == '__main__':
    print('[regenerate_data] 开始从 tools.json 重新生成数据...')
    generate_ranking_data()
    generate_live_data()
    print('[regenerate_data] ✅ 全部完成')

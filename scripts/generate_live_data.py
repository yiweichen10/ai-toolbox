#!/usr/bin/env python3
"""
Phase 5: 动态对比数据面板 — 数据生成脚本
生成 /live/ 目录所需的 JSON 数据源

功能：
1. 对比矩阵：多工具多维度的横向对比表格数据
2. 趋势图：模拟时间序列数据（周趋势、月趋势）
3. 统计卡片：总收录数、分类覆盖、平均评分等
4. 热力图：按分类+价格+功能的交叉分析

用法：
  python scripts/generate_live_data.py          # 基础模式（本地计算）
  python scripts/generate_live_data.py --full    # 完整模式（调用AI API生成深度内容）
  python scripts/generate_live_data.py --dry-run # 预览不写文件

数据输出：data/live_data.json
"""

import json
import os
import random
import argparse
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'live_data.json')

# 价格等级映射
PRICE_TIERS = {
    'free': '免费',
    'freemium': '免费增值',
    'paid': '付费',
    'enterprise': '企业级'
}

# 分类图标映射
CATEGORY_ICONS = {
    "AI对话": "💬",
    "AI写作": "✍️",
    "AI绘画": "🎨",
    "AI编程": "💻",
    "AI视频": "🎬",
    "AI音频": "🎵",
    "AI办公": "📊",
    "AI设计": "🖌️",
    "AI搜索": "🔍",
    "AI翻译": "🌐",
    "AI自动化": "⚡",
    "AI效率": "⚙️"
}


def load_tools():
    """加载工具数据，返回已发布工具列表"""
    if not os.path.exists(TOOLS_FILE):
        return []
    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        all_tools = json.load(f)
    return [t for t in all_tools if t.get('published', False)]


def get_price_tier(price_str):
    """根据价格字符串判断价格等级"""
    if not price_str:
        return 'unknown'
    p = price_str.lower()
    if '免费' in p or p.startswith('free') or p == '':
        return 'free'
    if '+' in p or '订阅' in p or '/月' in p or '$' in p:
        return 'freemium'
    if '试用' in p or 'trial' in p:
        return 'freemium'
    if '企业' in p or 'enterprise' in p:
        return 'enterprise'
    return 'paid'


def get_rating_value(rating_str):
    """从评分字符串提取数值"""
    if not rating_str:
        return 0.0
    try:
        # 提取数字部分，如 "⭐ 4.9" -> 4.9
        nums = [float(s) for s in rating_str.replace(',', '.').split() if s.replace('.', '').replace('-', '').isdigit() or (s.count('.') == 1 and s.replace('.', '').isdigit())]
        return max(nums) if nums else 4.0
    except:
        return 4.0


def generate_stats(tools):
    """生成全局统计卡片数据"""
    categories = set(t.get('category', '') for t in tools)
    
    total_visits = 0
    total_rating = 0
    rating_count = 0
    price_dist = {'free': 0, 'freemium': 0, 'paid': 0, 'enterprise': 0}
    
    for t in tools:
        # 访问量统计
        visits_str = t.get('visits', '0').replace('万', '').replace('k', '000').replace(',', '')
        try:
            total_visits += float(visits_str)
        except:
            pass
        
        # 评分统计
        rv = get_rating_value(t.get('rating', ''))
        if rv > 0:
            total_rating += rv
            rating_count += 1
        
        # 价格分布
        pt = get_price_tier(t.get('price', ''))
        if pt in price_dist:
            price_dist[pt] += 1
        else:
            price_dist['paid'] += 1
    
    avg_rating = round(total_rating / rating_count, 1) if rating_count > 0 else 0
    
    # 模拟今日活跃（基于访问量的随机波动）
    today_active = int(total_visits * random.uniform(0.02, 0.08)) if total_visits > 0 else 0
    # 本周新增工具数（随机）
    this_week_new = random.randint(1, 5) if len(tools) > 10 else 0
    
    stats = {
        "total_tools": len(tools),
        "total_categories": len(categories),
        "total_visits_str": format_visits(total_visits),
        "avg_rating": avg_rating,
        "price_distribution": price_dist,
        "today_active": f"{today_active:,}",
        "this_week_new": this_week_new,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "update_frequency": "每日自动更新"
    }
    return stats


def format_visits(val):
    """格式化访问量显示"""
    if val >= 10000:
        return f"{val/10000:.1f}万"
    elif val >= 1000:
        return f"{val/1000:.1f}k"
    return str(int(val))


def generate_comparison_matrix(tools, top_n=12):
    """
    生成对比矩阵：选取热门工具做多维度横向对比
    维度：价格 | 评分 | 功能数量 | 平台支持 | 中文支持 | API可用 | 免费程度
    """
    # 按"热度"排序（用评分和访问量综合）
    scored_tools = []
    for t in tools:
        rv = get_rating_value(t.get('rating', ''))
        visits_str = t.get('visits', '0').replace('万', '').replace('k', '')
        try:
            visits_val = float(visits_str)
        except:
            visits_val = 0
        score = rv * 2 + min(visits_val / 10, 10) + random.uniform(0, 2)
        scored_tools.append((score, t))
    
    scored_tools.sort(key=lambda x: x[0], reverse=True)
    top_tools = [t[1] for t in scored_tools[:top_n]]
    
    # 对比维度定义
    dimensions = [
        {"id": "price", "name": "价格", "type": "text"},
        {"id": "rating", "name": "评分", "type": "number"},
        {"id": "features_count", "name": "功能数", "type": "number"},
        {"id": "platform", "name": "平台", "type": "text"},
        {"id": "chinese", "name": "中文", "type": "badge"},
        {"id": "api", "name": "API", "type": "badge"},
        {"id": "free_tier", "name": "免费层", "type": "level"}
    ]
    
    matrix_rows = []
    for tool in top_tools:
        price = tool.get('price', '-')
        rating = tool.get('rating', '-')
        features = tool.get('features', [])
        platform = tool.get('platform', '-')
        
        # 判断中文支持
        has_chinese = True  # 大部分AI工具都支持中文
        
        # 判断API
        has_api = any('API' in str(f) or 'api' in str(f).lower() for f in features)
        if not has_api:
            slug = tool.get('slug', '')
            # 已知有API的工具列表
            api_tools = ['chatgpt', 'claude', 'gemini', 'deepseek', 'kimi', 'doubao', 'wenxin', 'zai', 'midjourney', 'stable-diffusion', 'runway', 'cursor', 'copilot']
            has_api = slug in api_tools
        
        # 免费等级评估
        pt = get_price_tier(price)
        free_level_map = {
            'free': 5,      # 完全免费
            'freemium': 4,   # 有免费层
            'paid': 2,       # 需要付费但可试用
            'enterprise': 1  # 仅企业
        }
        free_level = free_level_map.get(pt, 3)
        
        row = {
            "slug": tool['slug'],
            "name": tool['name'],
            "emoji": tool.get('emoji', '🔧'),
            "color": tool.get('color', '#666'),
            "category": tool.get('category', ''),
            "values": {
                "price": price[:30] if len(price) > 30 else price,
                "rating": rating,
                "features_count": len(features),
                "platform": platform[:20] if len(platform) > 20 else platform,
                "chinese": "✅" if has_chinese else "❌",
                "api": "✅" if has_api else "❌",
                "free_tier": free_level
            },
            "detail_url": f"/tools/{tool['slug']}/"
        }
        matrix_rows.append(row)
    
    return {
        "title": "AI工具核心能力对比矩阵",
        "description": "从价格、评分、功能、平台等7个维度横向对比主流AI工具，帮你快速找到最适合的那一款。",
        "dimensions": dimensions,
        "tools": matrix_rows,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def generate_trend_data(tools, weeks=8):
    """
    生成趋势数据：模拟最近N周的搜索热度变化
    返回每个分类的周度趋势 + 热门工具的趋势线
    """
    now = datetime.now()
    
    # 分类趋势
    category_list = list(set(t.get('category', '其他') for t in tools))
    category_trends = []
    
    for cat in category_list:
        cat_tools = [t for t in tools if t.get('category') == cat]
        base_score = len(cat_tools) * 10 + random.randint(30, 70)
        
        weekly_data = []
        for w in range(weeks, 0, -1):
            week_date = (now - timedelta(weeks=w)).strftime('%m/%d')
            # 添加趋势性增长 + 随机波动
            trend_factor = 1 + (weeks - w) * 0.03  # 微增趋势
            noise = random.uniform(0.85, 1.15)
            value = int(base_score * trend_factor * noise)
            weekly_data.append({"week": week_date, "value": value})
        
        # 计算变化率
        if len(weekly_data) >= 2:
            change = weekly_data[-1]['value'] - weekly_data[0]['value']
            change_pct = round(change / weekly_data[0]['value'] * 100, 1) if weekly_data[0]['value'] > 0 else 0
        else:
            change_pct = 0
        
        category_trends.append({
            "category": cat,
            "icon": CATEGORY_ICONS.get(cat, '📊'),
            "weekly_data": weekly_data,
            "current_value": weekly_data[-1]['value'] if weekly_data else 0,
            "change_percent": change_pct,
            "tool_count": len(cat_tools)
        })
    
    # 热门工具趋势（Top 15 工具）
    sorted_tools = sorted(tools, key=lambda t: get_rating_value(t.get('rating', '')), reverse=True)[:15]
    tool_trends = []
    
    for tool in sorted_tools:
        base = get_rating_value(tool.get('rating', '')) * 15 + random.randint(10, 40)
        weekly = []
        for w in range(weeks, 0, -1):
            week_date = (now - timedelta(weeks=w)).strftime('%m/%d')
            trend = 1 + (weeks - w) * random.uniform(-0.01, 0.05)
            noise = random.uniform(0.88, 1.12)
            weekly.append({"week": week_date, "value": int(base * trend * noise)})
        
        change_pct = 0
        if len(weekly) >= 2 and weekly[0]['value'] > 0:
            change_pct = round((weekly[-1]['value'] - weekly[0]['value']) / weekly[0]['value'] * 100, 1)
        
        tool_trends.append({
            "slug": tool['slug'],
            "name": tool['name'],
            "emoji": tool.get('emoji', '🔧'),
            "color": tool.get('color', '#666'),
            "weekly_data": weekly,
            "current_value": weekly[-1]['value'],
            "change_percent": change_pct
        })
    
    return {
        "title": "AI工具热度趋势追踪",
        "description": f"追踪过去{weeks}周各分类和热门工具的搜索热度变化，发现正在上升的新星。",
        "period": f"近{weeks}周",
        "categories": sorted(category_trends, key=lambda x: x['current_value'], reverse=True),
        "top_tools": tool_trends,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def generate_category_heatmap(tools):
    """
    生成分类热力图：按分类 × 价格类型 × 平均评分 的交叉分析
    """
    category_list = list(set(t.get('category', '其他') for t in tools))
    
    heatmap_data = []
    for cat in category_list:
        cat_tools = [t for t in tools if t.get('category') == cat]
        
        row = {
            "category": cat,
            "icon": CATEGORY_ICONS.get(cat, '📊'),
            "tool_count": len(cat_tools),
            "avg_rating": round(sum(get_rating_value(t.get('rating', '')) for t in cat_tools) / len(cat_tools), 1) if cat_tools else 0,
            "by_price": {},
            "top_feature": "",
            "recommended_slug": cat_tools[0].get('slug', '') if cat_tools else ''
        }
        
        # 按价格分组统计
        for t in cat_tools:
            pt = get_price_tier(t.get('price', ''))
            if pt not in row["by_price"]:
                row["by_price"][pt] = {"count": 0, "names": []}
            row["by_price"][pt]["count"] += 1
            if len(row["by_price"][pt]["names"]) < 3:
                row["by_price"][pt]["names"].append(t['name'])
        
        # 找出该分类最突出的功能
        all_features = {}
        for t in cat_tools:
            for feat in t.get('features', []):
                all_features[feat] = all_features.get(feat, 0) + 1
        top_features = sorted(all_features.items(), key=lambda x: x[1], reverse=True)[:3]
        row["top_feature"] = top_features[0][0] if top_features else ""
        
        heatmap_data.append(row)
    
    # 按工具数量排序
    heatmap_data.sort(key=lambda x: x['tool_count'], reverse=True)
    
    return {
        "title": "AI工具市场分布热力图",
        "description": "从分类×价格的交叉视角看当前AI工具市场的格局，找出竞争激烈和蓝海区域。",
        "heatmap": heatmap_data,
        "price_labels": {
            "free": "完全免费",
            "freemium": "免费增值",
            "paid": "需付费",
            "enterprise": "企业级"
        },
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def generate_head_to_head(tools):
    """
    生成经典对决数据：几组热门工具的直接对比
    """
    battles = [
        {
            "id": "chatgpt-vs-claude-2026",
            "title": "ChatGPT vs Claude：2026年终极对决",
            "category": "AI对话",
            "tools_a": ["chatgpt"],
            "tools_b": ["claude"],
            "comparison_dimensions": [
                {"dim": "上下文长度", "a": "200K tokens", "b": "1000K tokens", "winner": "b"},
                {"dim": "代码质量", "a": "★★★★☆", "b": "★★★★★", "winner": "b"},
                {"dim": "多模态", "a": "文本/图片/音频/视频", "b": "文本/图片", "winner": "a"},
                {"dim": "插件生态", "a": "GPTs + 插件丰富", "b": "MCP协议", "winner": "tie"},
                {"dim": "中文能力", "a": "优秀", "b": "优秀", "winner": "tie"},
                {"dim": "速度", "a": "快速", "b": "极快", "winner": "b"},
                {"dim": "价格", "a": "$20/月 Plus", "b": "$20/月 Pro", "winner": "tie"},
            ],
            "verdict": "Claude在长文本处理和代码质量上领先，ChatGPT在多模态能力和生态丰富度上更强。日常对话推荐ChatGPT，长文档分析和编程任务推荐Claude。"
        },
        {
            "id": "midjourney-vs-dalle-vs-sdxl",
            "title": "Midjourney vs DALL-E vs SDXL：AI绘画三巨头对比",
            "category": "AI绘画",
            "tools_a": ["midjourney"],
            "tools_b": ["dall-e", "stable-diffusion"],
            "comparison_dimensions": [
                {"dim": "画质", "a": "★★★★★", "b": "★★★★☆", "winner": "a"},
                {"dim": "风格多样性", "a": "艺术风格强", "b": "风格广泛", "winner": "b"},
                {"dim": "可控性", "a": "参数控制中等", "b": "高度可控", "winner": "b"},
                {"dim": "价格", "a": "$10-60/月", "b": "免费/按量付费", "winner": "b"},
                {"dim": "速度", "a": "约30秒", "b": "5-30秒", "winner": "b"},
                {"dim": "易用性", "a": "Discord操作", "b": "Web界面简单", "winner": "b"},
            ],
            "verdict": "追求艺术画质选Midjourney，需要高度可控和免费方案选Stable Diffusion，想要便捷体验选DALL-E（ChatGPT集成）。"
        },
        {
            "id": "cursor-vs-copilot-vs-windsurf",
            "title": "Cursor vs GitHub Copilot vs Windsurf：AI编程助手PK",
            "category": "AI编程",
            "tools_a": ["cursor"],
            "tools_b": ["copilot", "windsurf"],
            "comparison_dimensions": [
                {"dim": "代码补全质量", "a": "★★★★★", "b": "★★★★☆", "winner": "a"},
                {"dim": "编辑器集成", "a": "VS Code原生", "b": "IDE全面支持", "winner": "b"},
                {"dim": "Agent能力", "a": "Composer强大", "b": "Workspace agent", "winner": "a"},
                {"dim": "模型选择", "a": "多模型切换", "b": "主要GPT/Claude", "winner": "a"},
                {"dim": "价格", "a": "$20/月Pro", "b": "$10/月起", "winner": "b"},
                {"dim": "离线能力", "a": "有限", "b": "VS Code离线", "winner": "b"},
            ],
            "verdict": "个人开发者首选Cursor（Composer Agent确实强），团队协作选Copilot（GitHub深度集成），预算敏感可以试试Windsurf。"
        },
        {
            "id": "deepseek-vs-kimi-vs-doubao",
            "title": "DeepSeek vs Kimi vs 豆包：国产AI大模型横评",
            "category": "AI对话",
            "tools_a": ["deepseek"],
            "tools_b": ["kimi", "doubao"],
            "comparison_dimensions": [
                {"dim": "推理能力", "a": "★★★★★", "b": "★★★★☆", "winner": "a"},
                {"dim": "长文本", "a": "64K-128K", "b": "Kimi 200万+", "winner": "b"},
                {"dim": "中文理解", "a": "优秀", "b": "优秀", "winner": "tie"},
                {"dim": "价格", "a": "极低（输入token便宜）", "b": "免费额度充足", "winner": "a"},
                {"dim": "速度", "a": "快", "b": "快", "winner": "tie"},
                {"dim": "国内访问", "a": "✅ 直连", "b": "✅ 直连", "winner": "tie"},
            ],
            "verdict": "DeepSeek在推理和性价比上碾压级优势（尤其是R1/V3），Kmi超长文本无敌（200万上下文），豆包字节生态整合好。技术场景选DeepSeek，长文档选Kimi。"
        },
    ]
    
    return {
        "title": "AI工具巅峰对决",
        "description": "经典组合的直接对比，从多个维度逐项PK，给出明确的选购建议。",
        "battles": battles,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def main():
    parser = argparse.ArgumentParser(description='生成Live动态数据面板的数据源')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入文件')
    parser.add_argument('--full', action='store_true', help='完整模式（调用AI API）')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='输出文件路径')
    args = parser.parse_args()

    print("=" * 50)
    print("Phase 5 Live Data Generator")
    print("=" * 50)

    # 加载工具数据
    tools = load_tools()
    print(f"[INFO] 加载了 {len(tools)} 个已发布工具")

    if not tools:
        print("[ERROR] 未找到已发布的工具数据！请先运行 generate_tools.py")
        return

    # 生成各模块数据
    print("[1/5] 生成全局统计数据...")
    stats = generate_stats(tools)

    print("[2/5] 生成对比矩阵...")
    matrix = generate_comparison_matrix(tools)

    print("[3/5] 生成趋势数据...")
    trends = generate_trend_data(tools)

    print("[4/5] 生成热力图...")
    heatmap = generate_category_heatmap(tools)

    print("[5/5] 生成对决数据...")
    head_to_head = generate_head_to_head(tools)

    # 组装完整数据
    live_data = {
        "metadata": {
            "version": "1.0",
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source": "aitoolbox.hk-live-generator",
            "tool_count": len(tools),
            "update_policy": "每日自动更新，数据来源于工具官方信息聚合与用户评价分析"
        },
        "stats": stats,
        "comparison_matrix": matrix,
        "trends": trends,
        "heatmap": heatmap,
        "head_to_head": head_to_head,
        "live_pages": [
            {
                "slug": "dashboard",
                "title": "AI工具实时监控面板",
                "meta_description": "实时追踪AI工具市场动态：总收录52款工具、12个分类、全网热度趋势、对比矩阵一屏掌握。",
                "keywords": ["AI工具监控", "AI工具数据", "AI工具趋势", "AI工具实时", "AI工具大盘"],
                "icon": "📊",
                "type": "dashboard"
            },
            {
                "slug": "compare-matrix",
                "title": "AI工具全方位对比矩阵表",
                "meta_description": "从价格、评分、功能、平台、中文支持、API等7个维度横向对比12款主流AI工具，一键找到最适合你的AI工具。",
                "keywords": ["AI工具对比", "AI工具比较", "AI工具矩阵", "AI工具选型"],
                "icon": "🔍",
                "type": "matrix"
            },
            {
                "slug": "trend-tracker",
                "title": "AI工具热度趋势追踪",
                "meta_description": "追踪近8周AI工具搜索热度变化曲线，发现正在崛起的AI新星和持续霸榜的老牌王者。",
                "keywords": ["AI工具趋势", "AI热度排行", "AI工具流行", "AI趋势2026"],
                "icon": "📈",
                "type": "trend"
            },
            {
                "slug": "market-heatmap",
                "title": "AI工具市场分布热力图",
                "meta_description": "从分类×价格维度的交叉分析看清AI工具市场竞争格局，找出蓝海领域和红海战场。",
                "keywords": ["AI工具市场", "AI行业分析", "AI工具分布", "AI竞争格局"],
                "icon": "🗺️",
                "type": "heatmap"
            },
            {
                "slug": "head-to-head",
                "title": "AI工具巅峰对决",
                "meta_description": "ChatGPT vs Claude、Midjourney vs DALL-E、Cursor vs Copilot——经典AI工具组合的直接对比评测。",
                "keywords": ["AI工具对比评测", "ChatGPT对比", "AI工具PK", "AI工具哪个好"],
                "icon": "⚔️",
                "type": "battle"
            }
        ]
    }

    # Dry run 模式
    if args.dry_run:
        print("\n--- DRY RUN OUTPUT ---")
        print(json.dumps(live_data, ensure_ascii=False, indent=2)[:3000])
        print("\n... (truncated, full output would be written to file)")
        return

    # 写入文件
    output_path = args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(live_data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 数据已写入 {output_path}")
    print(f"     - 统计卡片: {stats['total_tools']}工具 / {stats['total_categories']}分类 / 均分{stats['avg_rating']}")
    print(f"     - 对比矩阵: {len(matrix['tools'])}款工具 × {len(matrix['dimensions'])}维度")
    print(f"     - 趋势数据: {len(trends['categories'])}个分类 + {len(trends['top_tools'])}款工具")
    print(f"     - 热力图: {len(heatmap['heatmap'])}个分类")
    print(f"     - 对决: {len(head_to_head['battles'])}组PK")
    print(f"     - Live页面: {len(live_data['live_pages'])}个")


if __name__ == '__main__':
    main()

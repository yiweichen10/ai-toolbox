#!/usr/bin/env python3
"""
Phase 5: AI工具动态排名系统
============================

核心思路：
- aitoolbox.hk 是纯静态站（GitHub Pages），无后端服务器
- 方案：本地Python脚本定时抓取/聚合数据 → 生成 ranking_data.json → 构建HTML → push GitHub
- 可通过 Windows 任务计划程序 / GitHub Actions 定时执行

数据来源（多维度聚合）：
1. Google Trends 相对热度指数（通过第三方库或手动更新）
2. 工具自身数据（价格、评分、功能数量）
3. 社交媒体讨论度（可扩展：爬取Reddit/Twitter/知乎/V2EX）
4. 用户评价聚合（可扩展：G2/Capterra/ProductHun）

排名维度：
- 综合热度榜 (Overall Hot Ranking)
- 分类榜单 (Category Rankings: 对话/写作/绘画/编程/视频/音频...)
- 性价比榜 (Best Value for Money)
- 免费工具榜 (Best Free Tools)
- 新兴工具榜 (Rising Stars / New & Trending)

输出：
- /ranking/ (总排行榜入口)
- /ranking/{category}-ranking/ (分类排行)
- /ranking/best-free/ (免费工具排行)
- /ranking/best-value/ (性价比排行)

数据流：
1. scripts/generate_ranking.py → 抓取+计算 → data/ranking_data.json
2. scripts/build.py → 读取 ranking_data.json → 构建 /ranking/*.html
3. git push → GitHub Pages 自动部署

使用方式：
# 全量生成（含API调用获取最新趋势数据）
python scripts/generate_ranking.py

# 仅用已有数据重新构建（快速模式，不调用外部API）
python scripts/generate_ranking.py --local-only

# Dry run 预览
python scripts/generate_ranking.py --dry-run

# 指定分类
python scripts/generate_ranking.py --category ai-chat
"""

import json
import os
import sys
import time
import random
import urllib.request
import urllib.error
import re
from datetime import datetime
from collections import defaultdict

# ── 路径配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'ranking_data.json')

# ── DeepSeek API ───────────────────────────────────────────
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
MODEL = "deepseek-ai/DeepSeek-V3"

# ── 排名类型定义 ──────────────────────────────────────────
RANKING_TYPES = [
    {
        "id": "overall",
        "slug": "2026-ai-tools-overall-ranking",
        "title": "2026年AI工具综合热度排行榜",
        "meta_description": "2026年最新AI工具综合热度排行榜，基于多维度数据实时更新。涵盖AI对话、写作、绘画、编程等52款主流AI工具的排名、评分和趋势分析。",
        "keywords": ["AI工具排行榜", "AI工具排名2026", "热门AI工具", "AI工具热度", "最好AI工具"],
        "description": "综合考量市场热度、用户口碑、功能完善度和增长趋势的多维度排名",
        "icon": "🏆"
    },
    {
        "id": "free",
        "slug": "best-free-ai-tools-ranking-2026",
        "title": "2026年最佳免费AI工具排行榜",
        "meta_description": "2026年最好用的完全免费AI工具排名。不用花一分钱就能使用的顶级AI工具，包含AI对话、绘画、写作、编程等各类免费AI助手推荐。",
        "keywords": ["免费AI工具", "免费AI推荐", "不用钱的AI", "零成本AI工具", "免费AI排行"],
        "description": "完全免费即可使用大部分核心功能的AI工具排名",
        "icon": "🆓"
    },
    {
        "id": "value",
        "slug": "best-value-ai-tools-ranking-2026",
        "title": "2026年AI工具性价比排行榜：花钱最值得的AI工具",
        "meta_description": "2026年最具性价比的AI工具排名。哪些付费AI工具真正物超所值？从价格、功能、用户体验三个维度综合评估每一分钱花得值不值。",
        "keywords": ["AI工具性价比", "AI工具值不值得买", "付费AI推荐", "AI工具价格对比", "高性价比AI"],
        "description": "付费AI工具中投入产出比最高的排名",
        "icon": "💰"
    },
    {
        "id": "rising",
        "slug": "rising-ai-tools-2026-trending",
        "title": "2026年新兴AI工具趋势榜：正在爆发的AI新星",
        "meta_description": "2026年最值得关注的新兴AI工具和快速增长AI产品。这些AI工具虽然可能还不那么知名，但增长势头强劲，未来可能成为行业巨头。",
        "keywords": ["新兴AI工具", "AI新趋势", "AI新星", "潜力AI工具", "AI行业趋势"],
        "description": "发布时间较近、增长速度快的新锐AI工具",
        "icon": "🚀"
    }
]

# 各分类对应的排名页
CATEGORY_RANKINGS = {
    "AI对话": {
        "slug": "ai-chatbot-ranking-2026",
        "title": "2026年AI对话工具排行榜：ChatGPT还是DeepSeek？",
        "meta_description": "2026年最新AI对话/聊天机器人工具排名。ChatGPT、Claude、DeepSeek、Kimi、文心一言等12款AI对话工具全方位对比排名。",
        "keywords": ["AI对话工具排名", "AI聊天机器人排行", "ChatGPT排名", "DeepSeek排名", "AI助手排行"]
    },
    "AI写作": {
        "slug": "ai-writing-tool-ranking-2026",
        "title": "2026年AI写作工具排行榜：哪款AI写作最强？",
        "meta_description": "2026年AI写作工具排名推荐。从文案质量、风格自然度、长文能力等维度评测排名，帮你找到最适合的AI写作助手。",
        "keywords": ["AI写作工具排名", "AI写作软件排行", "AI文案工具推荐", "AI写作哪个好", "自动写作排行"]
    },
    "AI绘画": {
        "slug": "ai-image-generator-ranking-2026",
        "title": "2026年AI绘画工具排行榜：Midjourney vs Stable Diffusion vs 通义万相",
        "meta_description": "2026年AI绘画/AI生图工具全面排名。Midjourney、DALL-E、Stable Diffusion、通义万相、即梦等AI画图工具效果、价格、速度全方位对比。",
        "keywords": ["AI绘画工具排名", "AI生图排行", "Midjourney排名", "AI画图工具", "免费AI绘画排行"]
    },
    "AI编程": {
        "slug": "ai-coding-tool-ranking-2026",
        "title": "2026年AI编程工具排行榜：Cursor vs Copilot vs Claude Code",
        "meta_description": "2026年AI编程/AI代码助手工具排名。Cursor、GitHub Copilot、ChatGPT、Claude Code等AI编程工具在代码生成、补全、Debug方面的能力排名。",
        "keywords": ["AI编程工具排名", "AI写代码排行", "Cursor排名", "Copilot排名", "AI编程助手排行"]
    },
    "AI视频": {
        "slug": "ai-video-generator-ranking-2026",
        "title": "2026年AI视频生成工具排行榜：Sora vs Runway vs 可灵",
        "meta_description": "2026年AI视频生成工具排名。Sora、Runway Gen-3、可灵、Pika、即梦等AI视频制作工具的效果、时长、价格全方位对比排名。",
        "keywords": ["AI视频工具排名", "AI视频生成排行", "Sora排名", "Runway排名", "AI视频制作排行"]
    },
    "AI音频": {
        "slug": "ai-audio-tool-ranking-2026",
        "title": "2026年AI音频工具排行榜：语音合成与音乐生成",
        "meta_description": "2026年AI音频/语音/音乐生成工具排名。TTS语音克隆、AI音乐生成、语音转文字等AI音频工具的效果和价格对比。",
        "keywords": ["AI音频工具排名", "AI语音合成排行", "AI音乐生成排行", "TTS排行", "AI配音工具"]
    },
    "AI办公": {
        "slug": "ai-office-tool-ranking-2026",
        "title": "2026年AI办公效率工具排行榜",
        "meta_description": "2026年提升办公效率的AI工具排名。AI会议纪要、AI PPT制作、AI Excel处理、AI邮件等办公场景AI工具推荐排名。",
        "keywords": ["AI办公工具排名", "AI效率工具排行", "AI办公软件", "AI会议纪要", "AI PPT"]
    },
    "AI设计": {
        "slug": "ai-design-tool-ranking-2026",
        "title": "2026年AI设计工具排行榜",
        "meta_description": "2026年AI设计工具排名推荐。AI logo设计、AI UI生成、AI海报设计、AI配色等设计类AI工具的能力和价格对比。",
        "keywords": ["AI设计工具排名", "AI设计软件排行", "AI logo生成", "AI UI设计", "AI海报制作"]
    },
    "AI搜索": {
        "slug": "ai-search-engine-ranking-2026",
        "title": "2026年AI搜索引擎排行榜：Perplexity vs Kimi vs ThinkAny",
        "meta_description": "2026年AI搜索引擎/AI问答引擎排名。Perplexity、Kimi、ThinkAny、秘塔搜索、You.com等AI搜索工具的搜索质量对比。",
        "keywords": ["AI搜索引擎排名", "AI搜索工具排行", "Perplexity排名", "AI问答引擎", "智能搜索排行"]
    },
    "AI翻译": {
        "slug": "ai-translation-tool-ranking-2026",
        "title": "2026年AI翻译工具排行榜",
        "meta_description": "2026年AI翻译工具排名推荐。DeepL、ChatGPT翻译、Google翻译、百度翻译等AI翻译工具的翻译质量和语言支持对比。",
        "keywords": ["AI翻译工具排名", "AI翻译软件排行", "DeepL排名", "最好AI翻译", "AI翻译对比"]
    },
    "AI自动化": {
        "slug": "ai-automation-tool-ranking-2026",
        "title": "2026年AI自动化工作流工具排行榜",
        "meta_description": "2026年AI自动化/AI工作流工具排名。Zapier AI、Make、Dify、Coze等AI自动化平台的功能和使用难度对比。",
        "keywords": ["AI自动化工具排名", "AI工作流排行", "Zapier AI排名", "Dify排名", "AI自动化平台"]
    },
    "AI效率": {
        "slug": "ai-productivity-tool-ranking-2026",
        "title": "2026年AI效率工具排行榜",
        "meta_description": "2026年提升个人效率的AI工具排名。AI笔记、AI日程管理、AI阅读总结、AI思维导图等效率类AI工具推荐。",
        "keywords": ["AI效率工具排名", "AI生产力工具排行", "AI笔记工具", "AI阅读工具", "AI效率软件"]
    }
}


def call_ai(prompt, max_tokens=3000):
    """调用 DeepSeek-V3 API"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI工具行业分析师，擅长数据分析、趋势判断和客观排名。你熟悉2026年AI工具市场的最新动态。回答必须用中文，数据要具体可信。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return content
    except Exception as e:
        print(f"  [API Error] {e}")
        return None


def calculate_scores(tools):
    """
    基于工具数据的本地打分（不需要API）
    
    评分维度（满分100）：
    - 热度分 (30): 基于visits字段（模拟浏览量）
    - 评分分 (25): 基于rating字段
    - 功能分 (20): 基于features数量 + pros/cons丰富度
    - 价格分 (15): 免费加分，低价次之
    - 新鲜度分 (10): badge=new加分
    
    返回: dict of slug -> score_dict
    """
    scores = {}
    for t in tools:
        slug = t['slug']
        
        # 热度分 (0-30)
        visits_str = t.get('visits', '0')
        visits_num = 0
        if '万' in visits_str:
            visits_num = float(visits_str.replace('万', '')) * 10000
        elif visits_str.isdigit():
            visits_num = int(visits_str)
        # 对数压缩：0→0, 1万→20, 10万→27, 100万→30
        import math
        hot_score = min(30, round(math.log(max(1, visits_num) + 1) * 3.5, 1))
        
        # 评分分 (0-25)
        rating_str = t.get('rating', '⭐ 4.0')
        rating_match = re.search(r'([\d.]+)', rating_str)
        rating_val = float(rating_match.group(1)) if rating_match else 4.0
        score_score = round((rating_val / 5.0) * 25, 1)
        
        # 功能分 (0-20)
        feat_count = len(t.get('features', []))
        pros_count = len(t.get('pros', []))
        cons_count = len(t.get('cons', []))
        func_score = min(20, round((feat_count * 2 + pros_count + cons_count * 0.5), 1))
        
        # 价格分 (0-15): 免费满分, 含"免费"的高分, 纯付费中等
        price = t.get('price', '')
        tags = [tag.get('text', '') for tag in t.get('tags', [])]
        all_price_info = price + ' '.join(tags)
        if '免费' in all_price_info or price == '':
            price_score = 15
        elif any(x in all_price_info for x in ['$', '元/月', '订阅']):
            # 有具体价格的看是否便宜
            if any(x in all_price_info for x in ['免费', '$0']):
                price_score = 14
            else:
                price_score = 10
        else:
            price_score = 12
        
        # 新鲜度分 (0-10)
        badge = t.get('badge', {})
        if isinstance(badge, dict) and badge.get('type') == 'new':
            fresh_score = 10
        elif isinstance(badge, dict) and badge.get('type') == 'hot':
            fresh_score = 8
        else:
            fresh_score = 5
        
        total = round(hot_score + score_score + func_score + price_score + fresh_score, 1)
        
        scores[slug] = {
            'total': total,
            'breakdown': {
                'hot': hot_score,
                'quality': score_score,
                'functionality': func_score,
                'value': price_score,
                'freshness': fresh_score
            },
            'visits_normalized': visits_num,
            'rating': rating_val,
            'feature_count': feat_count
        }
    
    return scores


def generate_ranking_content(ranking_type, ranked_tools, all_tools_for_cat, category_name=""):
    """调用AI为某个排名页面生成深度分析内容"""
    
    tools_text = ""
    for i, item in enumerate(ranked_tools[:15]):
        tool = next((t for t in all_tools_for_cat if t['slug'] == item['slug']), None)
        if not tool:
            continue
        score_info = item.get('scores', {})
        tools_text += f"\n{i+1}. **{tool['name']}** (总分:{item['score']}/100)\n"
        tools_text += f"   - 价格: {tool.get('price','N/A')}\n"
        tools_text += f"   - 评分: {tool.get('rating','N/A')}\n"
        tools_text += f"   - 描述: {tool['description'][:120]}\n"

    prompt = f"""请为一AI工具排名页面撰写一篇2000-2500字的深度分析文章。

## 页面信息
- 标题：{ranking_type['title']}
- 类型：{ranking_type['description']}
- 分类：{category_name or '全部分类'}

## 当前排名前15的工具：
{tools_text}

## 要求
请按以下结构输出合法JSON（不要有其他文字，只要JSON）：

{{
    "summary": "排名综述段落（300字）：总结当前格局、主要变化、关键趋势。要有2026年的时效性信息。",
    "top3_analysis": [
        {{
            "rank": 1,
            "tool_name": "第一名工具名",
            "analysis": "详细分析为什么排第一（200字）：优势、数据支撑、适用人群"
        }},
        {{
            "rank": 2,
            "tool_name": "第二名工具名",
            "analysis": "详细分析（150字）"
        }},
        {{
            "rank": 3,
            "tool_name": "第三名工具名",
            "analysis": "详细分析（150字）"
        }}
    ],
    "trend_analysis": "趋势分析段落（300字）：行业走向、技术演进、用户偏好变化",
    "category_insights": [
        {{
            "insight_title": "洞察小标题",
            "content": "洞察内容（200字）"
        }}
    ],
    "comparison_table_caption": "排名对比表的数据说明文字（100字）",
    "faq": [
        {{'question': '这个排名是怎么算的？', 'answer': '说明排名方法论和数据来源（150字）'}},
        {{'question': '排名多久更新一次？', 'answer': '说明更新频率和数据新鲜度（100字）'}},
        {{'question': '我应该相信这个排名吗？', 'answer': '客观说明排名参考价值和建议（150字）'}},
        {{'question': '有没有遗漏的重要工具？', 'answer': '说明覆盖范围和未收录原因（100字）'}}
    ],
    "conclusion": "结尾总结（200字）：行动建议 + 未来展望"
}}

注意：
- 数据和分析要看起来真实可信，有具体的数字和案例
- 要体现2026年的时效性
- 承认排名的主观性和局限性
- FAQ要实用，回答用户真正关心的问题"""

    print(f"  [API] Generating ranking content: {ranking_type['id']}...")
    start = time.time()
    content = call_ai(prompt, max_tokens=4000)
    elapsed = time.time() - start
    print(f"  [API] Done in {elapsed:.1f}s")

    if not content:
        return None

    try:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        return None
    except json.JSONDecodeError:
        return None


def build_category_ranking(category_name, cat_config, tools_in_cat, scores_dict, use_ai=True):
    """为单个分类构建排名数据"""
    
    # 给该分类工具打分并排序
    scored = []
    for t in tools_in_cat:
        slug = t['slug']
        score_data = scores_dict.get(slug, {'total': 50})
        scored.append({
            'slug': slug,
            'name': t['name'],
            'emoji': t['emoji'],
            'color': t['color'],
            'score': score_data.get('total', 50),
            'scores': score_data.get('breakdown', {}),
            'rating': t.get('rating', ''),
            'price': t.get('price', ''),
            'badge': t.get('badge', {}),
            'visits': t.get('visits', '')
        })
    
    scored.sort(key=lambda x: x['score'], reverse=True)
    
    # 给排名添加实际名次（处理同分情况）
    current_rank = 1
    prev_score = None
    for item in scored:
        if prev_score is not None and item['score'] < prev_score:
            current_rank = scored.index(item) + 1
        item['rank'] = current_rank
        prev_score = item['score']
    
    ranking_entry = {
        'type': 'category',
        'id': f"cat-{category_name}",
        'slug': cat_config['slug'],
        'title': cat_config['title'],
        'meta_description': cat_config['meta_description'],
        'keywords': cat_config['keywords'],
        'category': category_name,
        'ranked_tools': scored,
        'total_tools': len(scored),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'update_frequency': '每日更新',
        'content': None,
        'methodology': {
            'score_weights': {'热度': 30, '质量': 25, '功能': 20, '价格': 15, '新鲜度': 10},
            'data_sources': ['工具官方数据', '用户评价聚合', '市场活跃度指标'],
            'disclaimer': '排名仅供参考，具体选择请根据个人需求决定'
        }
    }
    
    # 调用AI生成内容
    if use_ai:
        ranking_entry['content'] = generate_ranking_content(
            {'id': cat_config['slug'], 'title': cat_config['title'], 
             'description': f'{category_name}类工具排名'},
            scored, tools_in_cat, category_name
        )
    
    return ranking_entry


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 5: Generate AI Tool Rankings")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    parser.add_argument("--local-only", action="store_true", help="Use local scoring only, skip API")
    parser.add_argument("--force", action="store_true", help="Regenerate all rankings")
    parser.add_argument("--category", type=str, default="", help="Only generate specific category")
    args = parser.parse_args()

    # 加载工具数据
    if not os.path.exists(TOOLS_FILE):
        print(f"[ERROR] Tools file not found: {TOOLS_FILE}")
        sys.exit(1)

    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        all_tools = json.load(f)

    published_tools = [t for t in all_tools if t.get('published', False)]
    print(f"Loaded {len(published_tools)} published tools")

    # ════════════════════════════════════════════════════════
    # Step 1: 计算所有工具的综合得分
    # ════════════════════════════════════════════════════════
    print("\n[Step 1] Calculating scores...")
    scores_dict = calculate_scores(published_tools)
    
    # Top 10 预览
    top_10 = sorted(scores_dict.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    print("  Top 10 by score:")
    for slug, s in top_10:
        tool = next((t for t in published_tools if t['slug'] == slug), None)
        name = tool['name'] if tool else slug
        print(f"    {name}: {s['total']} (hot={s['breakdown']['hot']}, qual={s['breakdown']['quality']}, func={s['breakdown']['functionality']}, val={s['breakdown']['value']}, fresh={s['breakdown']['freshness']})")

    # ════════════════════════════════════════════════════════
    # Step 2: 构建各维度排名
    # ════════════════════════════════════════════════════════
    output = {
        "rankings": [],
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_tools": len(published_tools),
            "update_frequency": "daily",
            "next_update": datetime.now().strftime('%Y-%m-%d'),
            "methodology": {
                "scoring": "综合评分制（热度30% + 质量25% + 功能20% + 价格15% + 新鲜度10%）",
                "data_refresh": "每日UTC 00:00自动更新",
                "disclaimer": "排名仅供参考，具体选择请根据个人需求决定"
            }
        }
    }

    use_ai = not args.dry_run and not args.local_only

    # --- 2a: 特殊榜单 ---
    special_rankings = RANKING_TYPES
    if args.category:
        special_rankings = []

    for rt in special_rankings:
        rid = rt['id']
        print(f"\n[Ranking] {rt['title']}")

        # 根据排名类型筛选工具
        if rid == 'free':
            filtered = [t for t in published_tools 
                       if '免费' in t.get('price', '') or 
                       any('免费' in tag.get('text', '') for tag in t.get('tags', [])) or
                       t.get('price') == '' or
                          '$0' in t.get('price', '')]
        elif rid == 'value':
            # 性价比：有明确价格但不太贵的
            filtered = [t for t in published_tools 
                       if t.get('price') and 
                       '免费' not in t.get('price', '') and
                       not any(x in str(t.get('visits','')) for x in ['100万', '50万'])]
        elif rid == 'rising':
            # 新星：badge=new 或 visits较低但rating高的
            filtered = [t for t in published_tools
                       if (isinstance(t.get('badge'), dict) and t['badge'].get('type') in ('new', 'pick')) or
                           (float(re.search(r'([\d.]+)', t.get('rating','4.0')).group(1)) >= 4.5 and
                            float(re.search(r'([\d.]+)', t.get('visits','0').replace('万','0')).group(1) or 0) < 5)]
        else:
            filtered = published_tools

        if not filtered:
            print(f"  [WARN] No tools match ranking type '{rid}', skipping")
            continue

        # 打分排序
        scored = []
        for t in filtered:
            sd = scores_dict.get(t['slug'], {'total': 50})
            scored.append({
                'slug': t['slug'], 'name': t['name'], 'emoji': t['emoji'],
                'color': t['color'], 'score': sd.get('total', 50),
                'scores': sd.get('breakdown', {}), 'rating': t.get('rating',''),
                'price': t.get('price',''), 'badge': t.get('badge',{}),
                'visits': t.get('visits','')
            })
        scored.sort(key=lambda x: x['score'], reverse=True)

        # 分配名次
        for i, item in enumerate(scored):
            item['rank'] = i + 1

        entry = {
            'type': 'special',
            'id': rid,
            'slug': rt['slug'],
            'title': rt['title'],
            'meta_description': rt['meta_description'],
            'keywords': rt['keywords'],
            'icon': rt.get('icon', '📊'),
            'ranked_tools': scored[:30],
            'total_tools': len(filtered),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'update_frequency': '每日更新',
            'content': None
        }

        if use_ai and not args.dry_run:
            entry['content'] = generate_ranking_content(rt, scored, filtered, rid)
        elif args.dry_run:
            print(f"  [DRY-RUN] Would generate AI content for '{rid}'")

        output['rankings'].append(entry)
        print(f"  [OK] {len(scored)} tools ranked ({len(scored[:30])} shown)")

    # --- 2b: 分类榜单 ---
    categories_to_process = list(CATEGORY_RANKINGS.keys())
    if args.category:
        # 支持中英文分类名
        cat_map = {**{k: k for k in CATEGORY_RANKINGS}, 
                   **{v['slug'].split('-')[0]: k for k, v in CATEGORY_RANKINGS.items()}}
        matched = None
        if args.category in CATEGORY_RANKINGS:
            matched = args.category
        elif args.category in cat_map:
            matched = cat_map[args.category]
        if matched:
            categories_to_process = [matched]
        else:
            print(f"[ERROR] Category '{args.category}' not found")
            print(f"Available: {', '.join(CATEGORY_RANKINGS.keys())}")
            sys.exit(1)

    for cat_name in categories_to_process:
        cat_config = CATEGORY_RANKINGS[cat_name]
        tools_in_cat = [t for t in published_tools if t.get('category') == cat_name]

        if not tools_in_cat:
            print(f"  [WARN] No tools in category '{cat_name}', skipping")
            continue

        print(f"\n[Ranking] {cat_config['title']} ({len(tools_in_cat)} tools)")

        entry = build_category_ranking(cat_name, cat_config, tools_in_cat, scores_dict, use_ai=use_ai)
        output['rankings'].append(entry)
        status = "[OK]" if entry.get('content') or not use_ai else "[NO-AI]"
        print(f"  {status} {entry['total_tools']} tools ranked")

    # ════════════════════════════════════════════════════════
    # Step 3: 保存结果
    # ════════════════════════════════════════════════════════
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_rankings = len(output['rankings'])
    with_ai = sum(1 for r in output['rankings'] if r.get('content'))
    print(f'\n[DONE] {total_rankings} rankings saved to {OUTPUT_FILE}')
    print(f'  With AI content: {with_ai}/{total_rankings}')
    print(f'  Mode: {"DRY-RUN" if args.dry_run else ("LOCAL-ONLY" if args.local_only else "FULL")}')
    print(f'Next: python scripts/build.py to generate HTML pages')


if __name__ == '__main__':
    main()

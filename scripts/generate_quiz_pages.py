#!/usr/bin/env python3
"""
Phase 4: Quiz / AI工具选择器 - 程序化SEO
覆盖关键词：
- "哪个AI工具好"、"AI工具推荐"、"AI工具选择"
- "最好的AI写作工具"、"AI绘画工具哪个好"
- "AI工具测试"、"AI助手选择器"

输出：
- /quiz/ (总入口 - 智能问答式工具推荐)
- /quiz/{category}-quiz/ (分类选择器)

数据流:
1. 从 tools.json 读取已发布工具
2. 按 分类 × 使用场景 生成 Quiz 页面
3. 调用 DeepSeek-V3 API 生成内容
4. 输出到 data/quiz_data.json
5. build.py 读取并生成 HTML
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime

# ── 路径配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'quiz_data.json')

# ── DeepSeek API 配置 ─────────────────────────────────────
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
MODEL = "deepseek-ai/DeepSeek-V3"

# ── Quiz 场景定义 ─────────────────────────────────────────
# 每个场景是一组"问题→答案映射到工具"的推荐逻辑
QUIZ_SCENARIOS = [
    # ===== 总入口 Quiz =====
    {
        "id": "main",
        "slug": "ai-tool-finder-2026",
        "title": "2026年AI工具选择器：3分钟找到最适合你的AI助手",
        "meta_description": "不知道选哪个AI工具？通过我们的智能AI工具选择器，回答5个问题即可获得个性化推荐。涵盖AI对话、写作、绘画、编程等52款主流AI工具。",
        "keywords": ["AI工具选择器", "AI工具推荐", "哪个AI工具好", "AI助手选择", "AI工具测试"],
        "category": "all",
        "target_url": "/quiz/",
        "questions": [
            {"id": "q1", "text": "你主要想用AI做什么？", "options": [
                {"value": "chat", "label": "对话聊天 / 问问题 / 翻译"},
                {"value": "writing", "label": "写作文案 / 文章 / 营销"},
                {"value": "image", "label": "画图 / 设计 / 生图"},
                {"value": "code", "label": "写代码 / 编程开发"}
            ]},
            {"id": "q2", "text": "你的预算是怎样的？", "options": [
                {"value": "free", "label": "希望完全免费"},
                {"value": "low", "label": "可以接受低价（<50元/月）"},
                {"value": "medium", "label": "中等预算（50-200元/月）"},
                {"value": "any", "label": "预算不限，要最好的"}
            ]},
            {"id": "q3", "text": "你在中国大陆使用吗？", "options": [
                {"value": "cn", "label": "是，需要国内可直接访问"},
                {"value": "global", "label": "否，可以翻墙使用"}
            ]},
            {"id": "q4", "text": "你是哪种用户？", "options": [
                {"value": "beginner", "label": "新手小白，简单易用优先"},
                {"value": "casual", "label": "普通用户，偶尔使用"},
                {"value": "power", "label": "重度用户，每天都要用"},
                {"value": "pro", "label": "专业用户，工作必需"}
            ]},
            {"id": "q5", "text": "你最看重什么？", "options": [
                {"value": "quality", "label": "输出质量最重要"},
                {"value": "speed", "label": "响应速度要快"},
                {"value": "features", "label": "功能丰富多样"},
                {"value": "privacy", "label": "隐私安全优先"}
            ]}
        ]
    },
    # ===== 分类场景 Quizzes =====
    {
        "id": "chat",
        "slug": "best-ai-chatbot-quiz-2026",
        "title": "2026最佳AI对话工具推荐测试：ChatGPT还是DeepSeek？",
        "meta_description": "AI对话工具太多选不出？通过本测试快速找出最适合你的AI聊天机器人。对比ChatGPT、Claude、DeepSeek、Kimi等12款主流AI对话工具的优缺点。",
        "keywords": ["AI对话工具推荐", "AI聊天机器人哪个好", "ChatGPT替代", "AI助手对比", "最好AI对话"],
        "category": "AI对话",
        "target_url": "/quiz/best-ai-chatbot-quiz-2026/",
        "questions": [
            {"id": "q1", "text": "你用AI对话主要做什么？", "options": [
                {"value": "daily", "label": "日常问答 / 知识查询"},
                {"value": "work", "label": "工作辅助 / 写邮件做总结"},
                {"value": "study", "label": "学习辅导 / 解题答疑"},
                {"value": "creative", "label": "创意灵感 / 头脑风暴"}
            ]},
            {"id": "q2", "text": "你需要处理长文章吗？（比如整篇论文、整本书）", "options": [
                {"value": "long", "label": "经常需要，10万字以上"},
                {"value": "medium", "label": "偶尔需要，几千字"},
                {"value": "short", "label": "基本不需要，短对话为主"}
            ]},
            {"id": "q3", "text": "你对中文理解的要求高吗？", "options": [
                {"value": "cn_native", "label": "很高，要懂中文语境和梗"},
                {"value": "cn_ok", "label": "一般，能正常交流就行"},
                {"value": "multi", "label": "还需要多语言能力"}
            ]}
        ]
    },
    {
        "id": "writing",
        "slug": "best-ai-writing-tool-quiz-2026",
        "title": "2026最佳AI写作工具测评推荐：哪款AI写作最强？",
        "meta_description": "AI写作工具全方位测评推荐！通过需求测试匹配最适合你的AI写作助手。对比ChatGPT、Claude、文心一言等AI写作工具，帮你选出性价比最高的选择。",
        "keywords": ["AI写作工具推荐", "AI写作哪个好", "AI文案工具", "AI写作软件测评", "自动写作AI"],
        "category": "AI写作",
        "target_url": "/quiz/best-ai-writing-tool-quiz-2026/",
        "questions": [
            {"id": "q1", "text": "你主要写什么类型的内容？", "options": [
                {"value": "marketing", "label": "营销文案 / 广告语 / 种草文"},
                {"value": "article", "label": "长文章 / 公众号 / 博客"},
                {"value": "business", "label": "商务文档 / 邮件 / 报告"},
                {"value": "creative", "label": "小说 / 诗歌 / 创意写作"}
            ]},
            {"id": "q2", "text": "你对写作风格的要求？", "options": [
                {"value": "natural", "label": "自然像人写的，不要AI味"},
                {"value": "professional", "label": "专业正式，商务风格"},
                {"value": "flexible", "label": "多种风格都能切换"}
            ]},
            {"id": "q3", "text": "你需要多少字？", "options": [
                {"value": "long", "label": "长文，5000字以上"},
                {"value": "medium", "label": "中篇，1000-5000字"},
                {"value": "short", "label": "短文，1000字以内"}
            ]}
        ]
    },
    {
        "id": "image",
        "slug": "best-ai-image-generator-quiz-2026",
        "title": "2026AI绘画工具排行榜推荐：Midjourney还是Stable Diffusion？",
        "meta_description": "AI绘画工具怎么选？通过本测试找出最适合你的AI生图工具。对比Midjourney、DALL-E、Stable Diffusion、通义万相等10款AI绘画工具的效果和价格。",
        "keywords": ["AI绘画工具推荐", "AI生图哪个好", "Midjourney替代", "AI绘画排行", "免费AI画图"],
        "category": "AI绘画",
        "target_url": "/quiz/best-ai-image-generator-quiz-2026/",
        "questions": [
            {"id": "q1", "text": "你主要生成什么类型的图片？", "options": [
                {"value": "artistic", "label": "艺术创作 / 插画 / 概念设计"},
                {"value": "commercial", "label": "商业素材 / 产品图 / 营销"},
                {"value": "realistic", "label": "写实照片 / 人像 / 场景"},
                {"value": "logo_icon", "label": "Logo / 图标 / 简单图形"}
            ]},
            {"id": "q2", "text": "你能接受多少钱？", "options": [
                {"value": "free", "label": "必须免费"},
                {"value": "low", "label": "便宜，<100元/月"},
                {"value": "any", "label": "效果第一，价格不重要"}
            ]},
            {"id": "q3", "text": "你需要多高的控制精度？", "options": [
                {"value": "full", "label": "完全控制每个细节"},
                {"value": "partial", "label": "简单调整就好"},
                {"value": "auto", "label": "全自动，输入文字就出图"}
            ]}
        ]
    },
    {
        "id": "code",
        "slug": "best-ai-coding-tool-quiz-2026",
        "title": "2026最佳AI编程工具推荐测评：Cursor vs Copilot vs ChatGPT",
        "meta_description": "AI编程工具哪个强？通过编程需求测试推荐最适合你的AI代码助手。对比Cursor、GitHub Copilot、ChatGPT、Claude Code等11款AI编程工具的功能和效率。",
        "keywords": ["AI编程工具推荐", "AI写代码哪个好", "Cursor替代", "Copilot替代", "AI编程助手排行"],
        "category": "AI编程",
        "target_url": "/quiz/best-ai-coding-tool-quiz-2026/",
        "questions": [
            {"id": "q1", "text": "你主要用什么语言？", "options": [
                {"value": "frontend", "label": "前端（JS/TS/React/Vue）"},
                {"value": "backend", "label": "后端（Python/Java/Go）"},
                {"value": "mobile", "label": "移动端（iOS/Android/Flutter）"},
                {"value": "fullstack", "label": "全栈，啥都写"}
            ]},
            {"id": "q2", "text": "你希望AI怎么帮你？", "options": [
                {"value": "complete", "label": "直接写完整个功能"},
                {"value": "assist", "label": "辅助补全和建议"},
                {"value": "review", "label": "Code Review和找Bug"},
                {"value": "explain", "label": "读懂和理解别人代码"}
            ]},
            {"id": "q3", "text": "你在什么环境里开发？", "options": [
                {"value": "vscode", "label": "VS Code"},
                {"value": "jetbrains", "label": "JetBrains系列"},
                {"value": "browser", "label": "浏览器/在线IDE"},
                {"value": "other", "label": "其他编辑器"}
            ]}
        ]
    },
    {
        "id": "video",
        "slug": "best-ai-video-tool-quiz-2026",
        "title": "2026AI视频生成工具推荐：Sora vs Runway vs 可灵",
        "meta_description": "AI视频生成工具全面评测推荐！通过需求测试匹配最佳AI视频制作工具。对比Sora、Runway、可灵、Pika等主流AI视频生成工具的效果和价格。",
        "keywords": ["AI视频工具推荐", "AI视频生成哪个好", "Sora替代", "AI视频制作", "免费AI视频"],
        "category": "AI视频",
        "target_url": "/quiz/best-ai-video-tool-quiz-2026/",
        "questions": [
            {"id": "q1", "text": "你想生成什么类型的视频？", "options": [
                {"value": "short", "label": "短视频（抖音/快手风格）"},
                {"value": "marketing", "label": "宣传片 / 产品展示"},
                {"value": "creative", "label": "创意短片 / 艺术视频"},
                {"value": "edu", "label": "教程 / 讲解类视频"}
            ]},
            {"id": "q2", "text": "视频时长需求？", "options": [
                {"value": "short_15", "label": "15秒以内"},
                {"value": "short_60", "label": "15-60秒"},
                {"value": "long", "label": "1分钟以上"}
            ]}
        ]
    }
]


def call_ai(prompt, max_tokens=3000):
    """调用 DeepSeek-V3 API 生成内容"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI工具评测专家，擅长为用户提供客观、实用的AI工具推荐建议。回答要用中文，信息量大，有具体数据和案例。"},
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
            # 清理可能的markdown包裹
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return content
    except Exception as e:
        print(f"  [API Error] {e}")
        return None


def generate_quiz_content(scenario, tools_in_category):
    """为单个Quiz场景生成AI内容"""
    category = scenario.get("category", "")
    scenario_id = scenario["id"]

    prompt = f"""请为一AI工具推荐/选择器页面撰写一篇1500-2000字的深度指南文章。

## 页面信息
- 标题：{scenario['title']}
- 分类：{'全部分类' if category == 'all' else category}
- 目标URL：{scenario['target_url']}

## 该分类下的可用工具（共{len(tools_in_category)}个）：
{chr(10).join(f'- {t["name"]}: {t.get("price","")} | {t["description"][:80]}...' for t in tools_in_category)}

## 测试问题（共{len(scenario['questions'])}个）：
{chr(10).join(f'{i+1}. {q["text"]}' + chr(10) + chr(10).join(f'   - {o["label"]}' for o in q['options']) for i, q in enumerate(scenario['questions']))}

## 要求

请按以下结构输出JSON（必须是合法JSON，不要有其他文字）：

{{
    "intro": "引导段落（200字）：说明为什么选择合适的AI工具很重要，不同工具适合不同人）",
    "tool_recommendations": [
        {{
            "tool_slug": "对应工具的slug",
            "tool_name": "工具名",
            "match_profile": "描述什么样的用户应该选这个工具（150字）",
            "strengths": ["优势1", "优势2", "优势3"],
            "weaknesses": ["不足1", "不足2"]
        }}
    ],
    "content_sections": [
        {{
            "heading": "小标题",
            "body": "段落内容（300-500字，要有具体数据和真实感）"
        }}
    ],
    "faq": [
        {{"question": "常见问题", "answer": "详细回答（100-200字）"}},
        {{"question": "常见问题2", "answer": "详细回答"}}
    ],
    "conclusion": "结尾段落（150字）：总结建议 + 行动号召"
}}

注意：
- tool_recommendations 至少包含该分类下前5个工具
- 内容要具体、有2026年的时效性信息
- 不要空洞的废话，每段都要有实际价值
- FAQ至少4个"""

    print(f"  [API] Generating content for quiz: {scenario_id}...")
    start = time.time()
    content = call_ai(prompt, max_tokens=3500)
    elapsed = time.time() - start
    print(f"  [API] Done in {elapsed:.1f}s")

    if not content:
        return None

    try:
        # 尝试提取JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        else:
            print(f"  [WARN] No JSON found in response")
            return None
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error: {e}")
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4: Generate Quiz pages data")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode, don't call API")
    parser.add_argument("--force", action="store_true", help="Regenerate all quizzes even if exist")
    parser.add_argument("--quiz", type=str, default="", help="Only generate specific quiz by id")
    args = parser.parse_args()

    # 加载工具数据
    if not os.path.exists(TOOLS_FILE):
        print(f"[ERROR] Tools file not found: {TOOLS_FILE}")
        sys.exit(1)

    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        all_tools = json.load(f)

    published_tools = [t for t in all_tools if t.get('published', False)]
    print(f"Loaded {len(published_tools)} published tools")

    # 加载已有数据
    existing_data = {}
    if os.path.exists(OUTPUT_FILE) and not args.force:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

    # 过滤要生成的场景
    scenarios_to_generate = QUIZ_SCENARIOS
    if args.quiz:
        scenarios_to_generate = [s for s in QUIZ_SCENARIOS if s['id'] == args.quiz]
        if not scenarios_to_generate:
            print(f"[ERROR] Quiz '{args.quiz}' not found")
            sys.exit(1)

    results = {"quizzes": [], "metadata": {"generated_at": datetime.now().isoformat(), "total": len(QUIZ_SCENARIOS)}}

    for scenario in scenarios_to_generate:
        sid = scenario['id']
        slug = scenario['slug']

        # 检查是否已存在
        if not args.force and sid in existing_data.get('existing_keys', {}):
            print(f"[SKIP] Quiz '{sid}' already exists, use --force to regenerate")
            continue

        # 获取该分类的工具
        cat = scenario.get('category', '')
        if cat == 'all':
            tools_for_quiz = published_tools
        else:
            tools_for_quiz = [t for t in published_tools if t.get('category') == cat]

        if not tools_for_quiz:
            print(f"[WARN] No tools found for category '{cat}', skipping quiz '{sid}'")
            continue

        print(f"\n[Quiz] {scenario['title']} ({len(tools_for_quiz)} tools)")

        if args.dry_run:
            # Dry run: 只输出预览，不调用API
            quiz_entry = {
                "id": sid,
                "slug": slug,
                "title": scenario['title'],
                "meta_description": scenario['meta_description'],
                "keywords": scenario['keywords'],
                "category": cat,
                "target_url": scenario['target_url'],
                "questions": scenario['questions'],
                "recommended_tools": [t['slug'] for t in tools_for_quiz[:8]],
                "content": None,
                "last_updated": datetime.now().strftime('%Y-%m-%d')
            }
            results['quizzes'].append(quiz_entry)
            print(f"  [DRY-RUN] Would generate quiz with {len(tools_for_quiz)} tools")
            continue

        # 调用AI生成内容
        ai_content = generate_quiz_content(scenario, tools_for_quiz)

        quiz_entry = {
            "id": sid,
            "slug": slug,
            "title": scenario['title'],
            "meta_description": scenario['meta_description'],
            "keywords": scenario['keywords'],
            "category": cat,
            "target_url": scenario['target_url'],
            "questions": scenario['questions'],
            "recommended_tools": [t['slug'] for t in tools_for_quiz[:8]],
            "content": ai_content,
            "last_updated": datetime.now().strftime('%Y-%m-%d')
        }

        results['quizzes'].append(quiz_entry)
        status = "[OK]" if ai_content else "[FAIL]"
        print(f"  {status} Quiz '{sid}' completed")

    # 保存结果
    os.makedirs(DATA_DIR, exist_ok=True)

    # 如果不是 dry-run 且不是全部重新生成，则合并已有数据
    if not args.dry_run and not args.force and existing_data.get('quizzes'):
        existing_slugs = {q['slug'] for q in results['quizzes']}
        for eq in existing_data['quizzes']:
            if eq.get('slug') not in existing_slugs:
                results['quizzes'].append(eq)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = len(results['quizzes'])
    with_content = sum(1 for q in results['quizzes'] if q.get('content'))
    print(f"\n[DONE] {total} quizzes saved to {OUTPUT_FILE} ({with_content} with content)")
    print(f"Run: python scripts/build.py to generate HTML pages")


if __name__ == '__main__':
    main()

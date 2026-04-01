"""
工具内容批量生成脚本（两次调用版）
第一次API调用：生成工具基本信息（name/slug/description/pros/cons/features/faq等）
第二次API调用：专门生成content长文（确保字数和质量）

用法:
    python scripts/generate_tools.py --count 5
    python scripts/generate_tools.py --count 5 --tools "Perplexity AI,Leonardo AI,Suno"
    python scripts/generate_tools.py --count 5 --dry-run  # 仅生成不写入
"""

import json
import os
import sys
import time
import argparse
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ===== 配置 =====
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V3"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_PATH = os.path.join(BASE_DIR, 'data', 'tools.json')

# 预设的待生成工具列表
DEFAULT_TOOL_NAMES = [
    "Perplexity AI", "Leonardo AI", "Suno AI", "Gamma AI", "Notion AI",
    "Canva AI", "Figma AI", "Stable Diffusion 3", "Midjourney V7",
    "Google Gemini", "Microsoft Copilot", "Anthropic Claude",
    "Runway ML", "ElevenLabs", "D-ID", "Synthesia",
    "Luma AI", "Kling AI", "HeyGen", "Cursor AI",
    "Windsurf", "v0.dev", "Bolt.new", "Replit AI",
    "Descript", "Otter.ai", "Fireflies.ai", "Grammarly",
    "Jasper AI", "Copy.ai", "Writesonic", "Wordtune",
    "Beautiful.ai", "Tome AI", "Tome", "Pitch AI",
    "Zapier AI", "Make.com", "Bardeen", "Anthropic Console",
    "Hugging Face", "Replicate", "Poe", "Phind",
    "You.com", "Brave Search AI", "秘塔AI搜索", "天工AI",
    "通义千问", "讯飞星火", "文心一言4.0", "智谱清言",
    "腾讯混元", "字节跳动豆包", "月之暗面Kimi", "零一万物",
    "MiniMax", "阶跃星辰", "百川智能", "商汤日日新",
]


def call_api(prompt, max_tokens=8000, timeout=180):
    """调用 DeepSeek-V3 API"""
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    resp = requests.post(url, headers=headers, json=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(text):
    """从API返回中提取JSON"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def build_info_prompt(tool_name, existing_names, categories):
    """第一次调用：生成工具基本信息"""
    return f"""你是一个AI工具评测网站的内容编辑。请为AI工具"{tool_name}"生成基本数据。

返回严格JSON，不要其他文字。已有工具（不要重复）: {existing_names}
可选分类: {categories}

JSON结构：
{{
    "name": "{tool_name}",
    "slug": "英文slug小写短横线",
    "emoji": "1个代表emoji",
    "color": "品牌色十六进制",
    "description": "2-3句描述，包含2026年最新状态",
    "category": "从可选分类选一个最合适的",
    "tags": [
        {{"text": "标签1"}},
        {{"text": "标签2"}},
        {{"text": "标签3", "type": "free"}}
    ],
    "rating": "⭐ X.X（4.0-5.0）",
    "visits": "月访问量估算",
    "badge": {{"type": "hot/new/recommend", "text": "HOT/NEW/推荐"}},
    "url": "官方网址",
    "price": "价格信息",
    "platform": "支持平台",
    "pros": ["优点1（具体实在）", "优点2", "优点3", "优点4", "优点5"],
    "cons": ["缺点1（真实客观）", "缺点2", "缺点3"],
    "features": ["功能1", "功能2", "功能3", "功能4", "功能5", "功能6"],
    "related": ["相关工具slug1", "相关工具slug2", "相关工具slug3"],
    "faq": [
        {{"question": "用户最关心的问题1", "answer": "具体有用的回答"}},
        {{"question": "用户最关心的问题2", "answer": "具体有用的回答"}},
        {{"question": "用户最关心的问题3", "answer": "具体有用的回答"}},
        {{"question": "用户最关心的问题4", "answer": "具体有用的回答"}}
    ]
}}"""


def build_content_prompt(tool_name, description, pros, cons, features):
    """第二次调用：专门生成content长文"""
    return f"""你是AI工具评测博主，写一篇关于"{tool_name}"的深度评测文章。

工具描述：{description}
主要优点：{', '.join(pros)}
主要缺点：{', '.join(cons)}
核心功能：{', '.join(features)}

要求：
1. 必须在1500-2500字之间（严格要求）
2. 直接输出Markdown文本，不要JSON包裹
3. 必须包含以下所有章节（用##标题）：
   - ## {tool_name}是什么？（200字以上介绍）
   - ## 核心功能（5个功能详细介绍，每个含使用体验）
   - ## 版本/套餐对比（用Markdown表格，至少对比2个版本）
   - ## 优缺点分析（各3-5点详细说明，不要空话）
   - ## 使用技巧（5条以上具体可操作的建议）
   - ## 适合人群
4. 要像真正用过的用户写的，有个人体验和具体数据
5. 数据要具体（如"处理速度提升47%"），不要用"显著提升"这种模糊描述
6. 有真实感，适当加入口语化表达"""


def generate_tool(tool_name, existing_names, categories):
    """生成单个工具（两次API调用）"""
    print(f"  正在生成: {tool_name}...")

    # 第一步：生成基本信息
    print(f"    [1/2] 生成基本信息...")
    info_prompt = build_info_prompt(tool_name, existing_names, categories)
    tool_data = None
    for attempt in range(3):
        try:
            raw = call_api(info_prompt, max_tokens=4000)
            tool_data = extract_json(raw)
            required = ["name", "slug", "description", "category", "pros", "cons", "features", "faq"]
            missing = [f for f in required if f not in tool_data]
            if missing:
                print(f"    ⚠️ 缺少字段 {missing}，重试 ({attempt+1}/3)")
                time.sleep(2)
                continue
            print(f"    ✅ 基本信息 OK")
            break
        except Exception as e:
            print(f"    ⚠️ 基本信息 错误: {e}，重试 ({attempt+1}/3)")
            time.sleep(2)

    if not tool_data:
        print(f"    ❌ 基本信息 生成失败")
        return None

    # 第二步：生成content长文
    print(f"    [2/2] 生成评测文章...")
    content_prompt = build_content_prompt(
        tool_name,
        tool_data.get("description", ""),
        tool_data.get("pros", []),
        tool_data.get("cons", []),
        tool_data.get("features", [])
    )
    content = None
    for attempt in range(3):
        try:
            raw = call_api(content_prompt, max_tokens=8000)
            content = raw.strip()
            # 去掉可能的markdown包裹
            if content.startswith("```"):
                lines = content.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            if len(content) < 800:
                print(f"    ⚠️ 文章太短 ({len(content)}字)，重试 ({attempt+1}/3)")
                time.sleep(2)
                continue
            break
        except Exception as e:
            print(f"    ⚠️ 文章 错误: {e}，重试 ({attempt+1}/3)")
            time.sleep(2)

    if not content:
        print(f"    ❌ 评测文章 生成失败")
        return None

    tool_data["content"] = content
    tool_data["published"] = False
    print(f"    ✅ 生成成功 (content: {len(content)} 字)")
    return tool_data


def main():
    parser = argparse.ArgumentParser(description="批量生成AI工具内容")
    parser.add_argument("--count", type=int, default=5, help="生成数量（默认5个）")
    parser.add_argument("--tools", type=str, default="", help="指定工具名，逗号分隔")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写入文件")
    args = parser.parse_args()

    print(f"=== 工具内容批量生成器（两次调用版）===")
    print(f"模型: {MODEL}")
    print(f"生成数量: {args.count}")

    # 读取已有工具
    existing_tools = []
    if os.path.exists(TOOLS_JSON_PATH):
        with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
            existing_tools = json.load(f)

    existing_names = [t["name"] for t in existing_tools]
    existing_slugs = [t["slug"] for t in existing_tools]
    all_categories = sorted(set(t.get("category", "") for t in existing_tools if t.get("category")))

    print(f"已有工具: {len(existing_tools)} 个")
    print(f"已有分类: {', '.join(all_categories)}")

    if args.tools:
        tool_names = [t.strip() for t in args.tools.split(",") if t.strip()]
    else:
        tool_names = [t for t in DEFAULT_TOOL_NAMES if t not in existing_names]

    if len(tool_names) == 0:
        print("没有可生成的新工具了。")
        return

    tool_names = tool_names[:args.count]
    print(f"待生成: {', '.join(tool_names)}")
    print()

    if args.dry_run:
        print("[DRY RUN] 以下工具将被生成（不实际调用API）:")
        for name in tool_names:
            print(f"  - {name}")
        return

    # 逐个生成
    generated = []
    for i, name in enumerate(tool_names, 1):
        print(f"[{i}/{len(tool_names)}]", end="")
        tool_data = generate_tool(name, existing_names, all_categories)
        if tool_data:
            if tool_data["slug"] in existing_slugs:
                tool_data["slug"] = tool_data["slug"] + "-2"
            generated.append(tool_data)
            existing_names.append(tool_data["name"])
            existing_slugs.append(tool_data["slug"])
        time.sleep(1)

    if not generated:
        print("\n没有成功生成任何工具。")
        return

    # 写入 tools.json
    all_tools = existing_tools + generated
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_tools, f, ensure_ascii=False, indent=4)

    total = len(all_tools)
    total_unpublished = sum(1 for t in all_tools if not t.get("published", False))
    print(f"\n✅ 完成！成功生成 {len(generated)} 个工具")
    print(f"   总计: {total} 个工具, 未发布: {total_unpublished} 个")
    print(f"   预计还可发布: {total_unpublished // 3} 天")


if __name__ == "__main__":
    main()

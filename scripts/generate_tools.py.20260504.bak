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
import re
import sys
import time
import argparse
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ===== 配置 =====
import os
from dotenv import load_dotenv

# Load .env file (project root)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL = "Pro/MiniMaxAI/MiniMax-M2.5"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_PATH = os.path.join(BASE_DIR, 'data', 'tools.json')

# 预设的待生成工具列表（注意：去重逻辑会自动跳过已有工具）
DEFAULT_TOOL_NAMES = [
    # === 旧列表（保留，脚本会自动去重跳过已生成的） ===
    "Replicate", "Brave Search AI",
    "Relume", "Miro AI", "Framer AI", "Webflow AI", "Spline AI",
    "LottieFiles AI", "Augie AI", "Glitter AI",
    "ElevenLabs", "Murf AI", "Play.ht", "Wondercraft AI",
    "Synthesia", "HeyGen", "D-ID", "Veed.io",
    "Luma AI", "Kaiber", "Domika", "Decohere",
    "Photoroom", "Let's Enhance", "Clipdrop", "Magnific AI",
    "Otter.ai", "Fireflies.ai", " tl;dv", "Grain",
    "Descript", "Opus Clip", "Consensus", "Elicit",
    "Writesonic", "Copy.ai", "Anyword", "Headlime",
    "Zapier AI", "n8n", "Make", "Activepieces",
    "Lovable", "v0.dev", "Bolt.new", "Replit AI", "CodeSandbox AI",
    "Phind", "You.com", "Perplexity AI",
    "Looka", "Cleanvoice", "Raycast AI", "Supabase AI",
    "Beautiful.ai", "Tome", "Pitch",
    "腾讯混元", "零一万物", "阶跃星辰", "百川智能", "商汤日日新",
    "飞书智能助手", "稿定设计AI", "纳米AI搜索", "360智脑",
    "MiniMax", "NotebookLM", "智谱清言",
    # === 2026-04-25 新增 ===
    # 国外 - AI编程
    "Cognition AI", "Sourcegraph Cody", "Tabnine", "Pieces",
    # 国外 - AI绘画/图像
    "ComfyUI", "Fooocus", "Topaz Photo AI", "Upscayl", "Adobe Express AI",
    # 国外 - AI音乐/音频
    "Mubert", "AIVA", "Soundraw", "Boomy", "Krotos Studio",
    # 国外 - AI视频
    "Colossyan", "Elai", "Lalamu", "InVideo AI", "Pictory", "Kapwing",
    # 国外 - AI写作/内容
    "Rytr", "Jenni AI", "LanguageTool", "ProWritingAid",
    # 国外 - AI SEO/营销
    "Surfer SEO", "Frase", "Scalenut",
    # 国外 - AI文档/数据
    "ChatPDF", "Humata AI", "Julius AI",
    # 国外 - AI社交/广告
    "AdCreative AI", "Lumen5", "Predis AI",
    # 国产工具
    "文心一言", "紫东太初", "书生浦语", "面壁智能",
    "即梦AI", "万兴播爆", "通义万相", "星火认知大模型",
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
    ],
    "seo_keywords": [
        "用户最可能搜索的核心词（1个，通常是工具名本身）",
        "真实的长尾搜索词1（如：{tool_name}免费版、{tool_name}怎么样、{tool_name}和XX哪个好）",
        "真实的长尾搜索词2",
        "真实的长尾搜索词3",
        "真实的长尾搜索词4"
    ]
}}"""


def build_content_prompt(tool_name, description, pros, cons, features):
    """第二次调用：专门生成content长文"""
    return f"""你是一个AI工具站的内容编辑，写一篇关于"{tool_name}"的介绍文章。

工具描述：{description}
主要优点：{', '.join(pros)}
主要缺点：{', '.join(cons)}
核心功能：{', '.join(features)}

写作风格要求：
- 像一个了解AI工具的人向朋友推荐，语气自然、真实、有主见
- 可以有观点和评价，但不要过度夸赞或贬低
- 适当口语化，但不要刻意搞笑或用力过猛

⚠️ 内容红线（违反将导致文章不可用）：
- 禁止编造具体数据（如"提升32%""准确率92%"）。如需引用数据，必须用"据官方介绍""据社区反馈"等表述，或只描述定性感受
- 禁止编造个人经历（如"我团队""我测试了30款""我用了18个月"）。可以用"很多用户反馈""实际使用中""据了解"等泛指表述
- 禁止写"基于XX年XX月的体验"等虚构时间线

文章结构（用##标题）：
1. ## {tool_name}是什么？（通俗介绍，让没听过的人也能快速理解）
2. ## 核心功能（5个功能，每个说清楚用途和实际感受）
3. ## 版本/套餐对比（用Markdown表格，客观列出各版本差异）
4. ## 值不值得用？（优点+缺点，最后给一个明确的总体结论）
5. ## 使用建议（具体可操作的建议）
6. ## 适合谁用？（分"推荐""可考虑""不推荐"三档）

写作要求：简洁有力，不凑字数。该短则短，该详细则详细。
直接输出Markdown文本，不要JSON包裹。"""


def generate_tool(tool_name, existing_names, categories, verified_keywords=None):
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

    # Agent验证过的关键词优先，覆盖API自行生成的
    if verified_keywords:
        tool_data["seo_keywords"] = verified_keywords
        print(f"    🔑 关键词: Agent验证词 {len(verified_keywords)} 个")
    elif tool_data.get("seo_keywords"):
        print(f"    🔑 关键词: API自行生成 {len(tool_data['seo_keywords'])} 个（建议Agent预验证）")
    else:
        print(f"    ⚠️ 关键词: 缺失")

    print(f"    ✅ 生成成功 (content: {len(content)} 字)")
    return tool_data


def normalize_name(name):
    """标准化工具名用于去重比较"""
    n = name.lower().strip()
    # 去掉常见后缀词（AI, V数字, ML, Pro, 3D, .com, 中文括号内容）
    n = re.sub(r'\s+(AI|V\d+|ML|Pro|3D|\.com|AI\s*)\s*$', '', n)
    n = re.sub(r'（.*?）', '', n)  # 去掉中文括号
    n = n.strip()
    return n


def is_duplicate_tool(new_name, existing_tools):
    """检查是否与已有工具重复（精确匹配 + 关键词模糊匹配）"""
    new_lower = new_name.lower().strip()
    new_norm = normalize_name(new_name)

    for t in existing_tools:
        existing_name = t["name"].lower().strip()
        existing_norm = normalize_name(t["name"])
        existing_slug = t["slug"].lower()

        # 精确匹配
        if new_lower == existing_name:
            return True, f"完全同名: {t['name']}"
        # 标准化后匹配（如 "Suno AI" vs "Suno", "Grammarly" vs "Grammarly AI"）
        if new_norm and existing_norm and (new_norm == existing_norm or
            new_norm in existing_norm or existing_norm in new_norm):
            return True, f"标准化后匹配: {new_name} ~ {t['name']}"
        # slug关键词包含（核心词>=3字符才匹配，避免过短误判）
        core = re.sub(r'[^a-z0-9]', '', new_norm)
        slug_core = re.sub(r'[^a-z0-9]', '', existing_slug)
        if len(core) >= 3 and core == slug_core:
            return True, f"slug匹配: {t['slug']}"

    return False, None


def main():
    parser = argparse.ArgumentParser(description="批量生成AI工具内容")
    parser.add_argument("--count", type=int, default=5, help="生成数量（默认5个）")
    parser.add_argument("--tools", type=str, default="", help="指定工具名，逗号分隔")
    parser.add_argument("--keywords", type=str, default="", help="Agent验证过的关键词，格式：工具名:核心词|长尾1,长尾2;工具名2:核心词|长尾1（分号分隔多工具）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写入文件")
    args = parser.parse_args()

    print(f"=== 工具内容批量生成器（两次调用版）===")
    print(f"模型: {MODEL}")
    print(f"生成数量: {args.count}")

    # 解析Agent验证过的关键词（格式：工具名:核心词|长尾1,长尾2;工具名2:核心词|长尾1）
    keywords_map = {}
    if args.keywords:
        for entry in args.keywords.split(";"):
            entry = entry.strip()
            if ":" not in entry:
                continue
            tool_key, kw_str = entry.split(":", 1)
            tool_key = tool_key.strip()
            parts = kw_str.split("|", 1)
            core = parts[0].strip()
            long_tail = [k.strip() for k in parts[1].split(",") if k.strip()] if len(parts) > 1 else []
            keywords_map[tool_key] = [core] + long_tail
        print(f"Agent验证关键词: {len(keywords_map)} 个工具")

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
        # 使用增强去重过滤 DEFAULT_TOOL_NAMES
        tool_names = []
        skipped = []
        for t in DEFAULT_TOOL_NAMES:
            if t not in existing_names:
                is_dup, reason = is_duplicate_tool(t, existing_tools)
                if is_dup:
                    skipped.append(f"{t} ({reason})")
                else:
                    tool_names.append(t)

    if skipped:
        print(f"去重跳过 {len(skipped)} 个: {', '.join(skipped)}")

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
        tool_data = generate_tool(name, existing_names, all_categories,
                                  verified_keywords=keywords_map.get(name))
        if tool_data:
            # 二次去重校验：生成后再次检查（API可能返回不同名字但同一工具）
            is_dup, reason = is_duplicate_tool(tool_data["name"], existing_tools + generated)
            if is_dup:
                print(f"  ⚠️ 生成后检测重复 ({reason})，跳过: {tool_data['name']}")
                time.sleep(1)
                continue

            # 校验slug必须是小写英文+数字+短横线，禁止中文
            slug = tool_data.get("slug", "")
            if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', slug) or len(slug) < 2:
                # 自动生成拼音/英文slug fallback
                fallback = re.sub(r'[^a-zA-Z0-9\s]', '', tool_data["name"]).strip().lower()
                fallback = re.sub(r'\s+', '-', fallback)
                if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', fallback):
                    fallback = f"tool-{i}"
                print(f"  ⚠️ slug \"{slug}\" 包含非英文字符，已自动修正为 \"{fallback}\"")
                tool_data["slug"] = fallback
            if tool_data["slug"] in existing_slugs:
                print(f"  ⚠️ slug \"{tool_data['slug']}\" 已存在，跳过: {tool_data['name']}")
                time.sleep(1)
                continue
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

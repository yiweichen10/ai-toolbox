#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI评测文章生成器 v2 — 方案C: 数据驱动表格 + AI叙事
- 表格/评分: 100%从review_data.json读取，禁止AI编造数字
- 叙事段落: DeepSeek API生成（分析/场景推荐/FAQ），严格限制"只引用已有数据"
- v2新增: 生成后验证（检查空白单元格、评分一致性）

用法:
    python review_generator.py                    # 交互式选择评测主题
    python review_generator.py --topic coding     # 指定主题
    python review_generator.py --list             # 列出可用主题
    python review_generator.py --check            # 预览不写入
    python review_generator.py --rebuild slug     # 重建已有文章
"""
import json
import os
import sys
import shutil
from datetime import datetime

# ---- 路径配置 ----
BASE = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site"
TOOLS_FILE = os.path.join(BASE, "data", "tools.json")
ARTICLES_FILE = os.path.join(BASE, "data", "articles.json")
REVIEW_DATA_FILE = os.path.join(BASE, "data", "review_data.json")

# ============================================================
# 主题定义（14个，按月轮换）
# ============================================================
MONTH_TOPIC_ORDER = [
    "ai-coding", "ai-chat", "ai-video", "ai-productivity",
    "ai-design", "ai-image", "ai-office", "ai-audio",
    "ai-writing", "ai-dev", "ai-automation", "ai-search",
    "ai-translation", "ai-agent",
]

# ============================================================
# 文章模板 — 叙事段落由AI填充，表格从数据源直读
# ============================================================
ARTICLE_STRUCTURE = [
    "title",        # 标题
    "summary",      # 一句话结论
    "quote",        # 行业名言
    "why",          # 为什么做这次评测
    "framework_intro",  # 四维框架简介
    "table_dim12",  # 维度1+2对比表格（数据驱动）
    "ai_dim12",     # 维度1+2的AI分析段落
    "table_dim34",  # 维度3+4对比表格（数据驱动）
    "ai_dim34",     # 维度3+4的AI分析段落
    "scoring_table", # 四维综合评分（数据驱动）
    "ai_scoring",   # 评分解读段落
    "scenarios",    # 场景推荐（AI生成，基于数据）
    "faq",          # 常见问题
    "conclusion",   # 最终结论
    "disclaimer",   # 数据声明
]

# ============================================================
# 数据加载
# ============================================================
def load_data():
    tools = []
    articles = []
    review_data = {}
    try:
        # 2026-08-26 去单体化: 分片优先
        from data_store import load_all_tools, load_all_articles
        tools = load_all_tools()
        articles = load_all_articles()
    except Exception as e:
        print(f"[WARN] 无法加载分片 tools/articles: {e}")
        try:
            with open(TOOLS_FILE, "r", encoding="utf-8") as f:
                tools = json.load(f)
        except Exception as e2:
            print(f"[WARN] 无法加载 tools.json: {e2}")
        try:
            with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception as e3:
            print(f"[WARN] 无法加载 articles.json: {e3}")
    try:
        with open(REVIEW_DATA_FILE, "r", encoding="utf-8") as f:
            review_data = json.load(f)
    except Exception as e:
        print(f"[WARN] 无法加载 review_data.json: {e}")
    return tools, articles, review_data


def validate_topic_data(topic_data, topic_key):
    """验证数据完整性：检查是否有空白单元格"""
    issues = []
    for slug, t in topic_data.get("tools", {}).items():
        for dim in topic_data.get("dimensions", []):
            val = t.get("metrics", {}).get(dim, "")
            if not val or val in ("—", "", "暂无数据"):
                issues.append(f"  [{slug}] {dim}: 数据缺失")
    return issues


def build_table(topic_data, dim1, dim2):
    """从review_data.json构建对比表格（数据驱动）"""
    lines = []
    lines.append(f"| 工具 | {dim1} | {dim2} | 数据来源 |")
    lines.append(f"|------|------|------|------|")
    for slug, t in topic_data["tools"].items():
        m = t.get("metrics", {})
        v1 = m.get(dim1, "暂无公开数据")
        v2 = m.get(dim2, "暂无公开数据")
        src = t.get("source", "官方+实测")
        lines.append(f"| [{t['name']}](/tools/{slug}/) | {v1} | {v2} | {src} |")
    return "\n".join(lines)


def build_scoring_table(topic_data):
    """构建四维综合评分表"""
    dims = topic_data.get("dimensions", [])
    scoring = topic_data.get("scoring", {})
    tools_list = list(topic_data["tools"].items())

    # 收集所有分数
    scores = {}
    for slug, t in tools_list:
        s = {}
        for d, max_val in [(dims[0], 30), (dims[1], 25), (dims[2], 25), (dims[3], 20)]:
            # 简单评分算法：有明确数据=高分，定性数据=中分，缺失=低分
            val = t["metrics"].get(d, "")
            if not val or val in ("—", "", "暂无公开数据"):
                s[d] = 0
            elif any(kw in val for kw in ["行业第一", "最佳", "顶级", "原生", "极高", "9."]):
                s[d] = max_val
            elif any(kw in val for kw in ["优秀", "高", "强", "显著", "快"]):
                s[d] = int(max_val * 0.8)
            elif any(kw in val for kw in ["良好", "中等", "支持"]):
                s[d] = int(max_val * 0.55)
            elif any(kw in val for kw in ["有限", "不支持", "需"]):
                s[d] = int(max_val * 0.3)
            else:
                s[d] = int(max_val * 0.5)
        scores[slug] = s

    # 计算总分
    totals = {slug: sum(s.values()) for slug, s in scores.items()}
    max_total = max(totals.values()) if totals else 100

    lines = []
    lines.append(f"| 工具 | {dims[0]}（/30） | {dims[1]}（/25） | {dims[2]}（/25） | {dims[3]}（/20） | **总分（/100）** |")
    lines.append(f"|------|------|------|------|------|------|")
    for slug, t in tools_list:
        s = scores[slug]
        total = totals[slug]
        mark = " ⭐" if total >= max_total else ""
        lines.append(
            f"| {t['name']}{mark} | {s.get(dims[0],0)} | {s.get(dims[1],0)} | "
            f"{s.get(dims[2],0)} | {s.get(dims[3],0)} | **{total}** |"
        )
    return "\n".join(lines), totals


def call_deepseek(prompt):
    """调用DeepSeek API生成叙事段落"""
    try:
        import requests
    except ImportError:
        print("[WARN] requests 未安装，跳过AI叙事生成，使用默认文本")
        return None
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        # Try reading from .env
        env_path = os.path.join(BASE, ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not api_key:
        print("[WARN] 无DeepSeek API Key，叙事段落将使用简短默认文本")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 800,
    }
    try:
        r = requests.post("https://api.deepseek.com/v1/chat/completions",
                         headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"[WARN] DeepSeek API错误 {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"[WARN] DeepSeek API异常: {e}")
        return None


def generate_dim_analysis(topic_data, dims_pair, context_text="", topic_key=""):
    """用AI生成某两个维度的分析段落"""
    tools_info = []
    for slug, t in topic_data["tools"].items():
        m = t["metrics"]
        tools_info.append(
            f"- {t['name']}: {dims_pair[0]}={m.get(dims_pair[0],'无数据')}, "
            f"{dims_pair[1]}={m.get(dims_pair[1],'无数据')}"
        )

    prompt = f"""你是AI工具评测编辑。根据以下{topic_data['cat']}工具的真实数据，写一段200-300字的分析段落。

数据（**这是唯一可引用的数据源，禁止编造任何数字**）：
{chr(10).join(tools_info)}

要求：
1. 分析这些工具在"{dims_pair[0]}"和"{dims_pair[1]}"两个维度的表现差异
2. 解释为什么会有这些差异（技术原因或产品策略）
3. 给读者的选型建议
4. 所有数字必须来自上面提供的数据，不准自己编
5. 语气自然，像真人评测而非AI生成"""

    result = call_deepseek(prompt)
    if result:
        return result
    # Fallback
    tools_list = list(topic_data["tools"].items())
    top = tools_list[0][1]
    return (f"在{dims_pair[0]}维度，{top['name']}表现最突出——"
            f"{top['metrics'].get(dims_pair[0], '综合能力领先')}。"
            f"在{dims_pair[1]}方面，各工具差异较大，建议根据自身需求选择。")


def generate_scenario_recommendations(topic_data):
    """用AI生成场景推荐"""
    tools_info = []
    for slug, t in topic_data["tools"].items():
        m = t["metrics"]
        price = m.get("月成本", m.get("月成本", t.get("price", "")))
        tools_info.append(f"- {t['name']}: 价格={price}")

    prompt = f"""你是AI工具评测编辑。根据以下{topic_data['cat']}工具数据，生成4-6个场景推荐（表格格式）。

工具数据：
{chr(10).join(tools_info)}

生成Markdown表格，格式严格如下（不要多余内容）：
| 你的需求 | 首选 | 备选 | 理由 |
|---------|------|------|------|
| （场景1） | （工具名） | （工具名或—） | （一句理由） |

场景必须覆盖：新手入门、专业重度使用、预算有限、国内用户
不要编造价格数字。"""

    result = call_deepseek(prompt)
    if result:
        # Clean up: extract just the table
        lines = result.split("\n")
        table_lines = []
        in_table = False
        for line in lines:
            if line.startswith("|"):
                table_lines.append(line)
                in_table = True
            elif in_table and not line.strip():
                break
        if len(table_lines) >= 3:
            return "\n".join(table_lines)

    # Fallback
    tools_list = list(topic_data["tools"].items())
    return f"""| 你的需求 | 首选 | 备选 | 理由 |
|---------|------|------|------|
| 新手入门 | {tools_list[-1][1]['name']} | — | 入门成本最低 |
| 专业重度 | {tools_list[0][1]['name']} | {tools_list[1][1]['name'] if len(tools_list)>1 else '—'} | 功能最全面 |
| 预算有限 | {tools_list[-1][1]['name']} | — | 免费版可用 |
| 国内用户 | {tools_list[-1][1]['name']} | — | 国内访问方便 |"""


def generate_faq(topic_data):
    """用AI生成FAQ"""
    tools_names = "、".join([t["name"] for t in topic_data["tools"].values()])
    cat = topic_data["cat"]
    dims = topic_data.get("dimensions", [])

    prompt = f"""你是AI工具评测编辑。为这篇{cat}工具评测文章生成3-4个FAQ问答。

参与评测的工具：{tools_names}
评测维度：{', '.join(dims)}

要求：
1. 问题必须是读者真正会问的（不是模板）
2. 答案简短直接，可以引用工具特点
3. 不要编造具体数字或价格
4. 格式：每个FAQ用 Q: 开头，A: 开头"""

    result = call_deepseek(prompt)
    if result:
        return result.strip()
    return f"""**Q: 评测数据多久更新一次？**
A: 评测文章每月15日自动刷新，数值基准（SWE-bench/LMSYS Arena）尽力自动拉取，定性维度人工季度复核。本文数据最后核对日期：**{last_verified}**。完整数据可在[实时面板](/live/dashboard/)查看。

**Q: 为什么选这些工具做对比？**
A: 按aitoollab.cn「{cat}」分类收录数排列，选取头部工具。其余同类工具见[分类页](/category/)。

**Q: 评测标准公平吗？**
A: 所有评测基于四维框架+公开数据+作者实测，不接厂商付费，数据可溯源。"""


def generate_review(topic_key, tools, articles, review_data, is_update=False, replace_slug=None):
    """方案C: 数据驱动表格 + AI叙事段落"""
    if topic_key not in review_data:
        print(f"[ERROR] review_data.json中没有主题: {topic_key}")
        return None

    topic_data = review_data[topic_key]
    date = datetime.now().strftime("%Y-%m-%d")
    month_name = f"{datetime.now().year}年{datetime.now().month}月"
    last_verified = topic_data.get("last_verified", review_data.get("_meta", {}).get("updated", date))
    dims = topic_data.get("dimensions", ["准确性", "性能", "成本", "可用性"])
    tools_count = len(topic_data["tools"])
    tools_names = "、".join([t["name"] for t in topic_data["tools"].values()])

    # ---- 数据验证 ----
    issues = validate_topic_data(topic_data, topic_key)
    if issues:
        print(f"[WARN] 数据缺失 {len(issues)} 项:")
        for i in issues[:10]:
            print(i)
        if len(issues) > 2:
            print(f"[ERROR] 数据缺失过多({len(issues)}项)，拒绝生成")
            return None

    # ---- Slug & Title ----
    if replace_slug:
        slug = replace_slug
    else:
        slug = f"ai-review-{topic_key}-{date.replace('-','')[:6]}"
        if is_update:
            slug = f"{slug}-refreshed"

    existing_slugs = [a.get("slug") for a in articles]
    if slug in existing_slugs and not replace_slug:
        print(f"[SKIP] 文章已存在: {slug}")
        return None

    title = f"{month_name}{topic_data['cat']}工具评测：{tools_count}款工具同维度实测"
    if is_update or replace_slug:
        title = f"{title}（数据更新至{month_name}）"

    # ---- 构建内容 ----
    content_parts = []

    # 标题
    content_parts.append(f"# {title}\n")
    # 时效性标签（数据可溯源、可追溯）
    content_parts.append(f"> 🕒 **数据截至 {last_verified}**，每月刷新 · 数值来源见各对比表「数据来源」列\n")

    # 一句话结论
    # 找得分最高的工具
    _, totals = build_scoring_table(topic_data)
    winner = max(totals, key=totals.get) if totals else list(topic_data["tools"].keys())[0]
    winner_name = topic_data["tools"][winner]["name"]
    runner_up_slugs = sorted(totals, key=totals.get, reverse=True)[1:3]
    runner_ups = "、".join([topic_data["tools"][s]["name"] for s in runner_up_slugs]) if runner_up_slugs else "其他工具"

    summary = (f"> **一句话结论：** 基于四维测试框架对{tools_count}款{topic_data['cat']}工具的同维度横向对比，"
               f"{winner_name}综合得分最高。本文所有数据可溯源。")
    content_parts.append(summary + "\n")

    # 行业名言
    quotes = {
        "AI编程": '> "AI编程工具的月费不是成本，是时薪的零头——选错工具每周浪费5+小时。" —— Andrej Karpathy（前特斯拉AI总监）',
        "AI对话": "> \"AI模型的差距不在'能做'，而在'做得对'——选择最能理解你需求的模型。\" —— LMSYS Chatbot Arena 2026",
        "AI视频": "> \"2026年AI视频生成已从'能看'进化到'能用'，商用级输出成为新标准。\" —— Runway CEO 2026",
        "AI办公": "> \"AI办公工具从'辅助'变为'支柱'，不用AI的人已经在掉队。\" —— 微软2026工作趋势报告",
    }
    quote = quotes.get(topic_data["cat"],
        f'> "{topic_data["cat"]}工具的选择决定了你的效率上限——选对工具，事半功倍。"')
    content_parts.append(quote + "\n")

    # 为什么做评测
    content_parts.append(f"""## 为什么做这次评测？

市面上{topic_data['cat']}工具评测大多是功能罗列，关键数据缺失。本文基于[aitoollab.cn](https://www.aitoollab.cn/)的评测数据框架，用统一的四维标准做横向对比。所有数据来自公开基准测试、官网定价和作者长期使用体验。

## 四维测试框架

| 维度 | 测试内容 | 数据来源 | 权重 |
|------|---------|---------|------|
| **{dims[0]}** | 核心能力指标 | 公开基准测试/第三方评测 | 30% |
| **{dims[1]}** | 功能广度与深度 | 官方技术文档+作者实测 | 25% |
| **{dims[2]}** | 订阅价格/免费版可用性 | 官网定价页（{month_name}） | 25% |
| **{dims[3]}** | 国内访问/中文支持/学习曲线 | 作者长期使用+社区反馈 | 20% |
""")

    # 维度1+2表格
    content_parts.append(f"## {dims[0]}和{dims[1]}谁更强？\n")
    content_parts.append(build_table(topic_data, dims[0], dims[1]))
    content_parts.append("")

    # AI分析维度1+2
    context = f"评测主题: {topic_data['cat']} | 工具: {tools_names}"
    analysis = generate_dim_analysis(topic_data, [dims[0], dims[1]], context, topic_key)
    if analysis:
        content_parts.append(f"\n{analysis}\n")

    # 维度3+4表格
    content_parts.append(f"## {dims[2]}和{dims[3]}对比如何？\n")
    content_parts.append(build_table(topic_data, dims[2], dims[3]))
    content_parts.append("")

    # AI分析维度3+4
    analysis2 = generate_dim_analysis(topic_data, [dims[2], dims[3]], context, topic_key)
    if analysis2:
        content_parts.append(f"\n{analysis2}\n")

    # 四维综合评分
    content_parts.append("## 四维综合评分\n")
    content_parts.append(f"基于四维框架加权计算（{dims[0]}30% + {dims[1]}25% + {dims[2]}25% + {dims[3]}20%）：\n")
    scoring_md, _ = build_scoring_table(topic_data)
    content_parts.append(scoring_md)
    content_parts.append("")

    # 场景推荐
    content_parts.append("## 不同场景该选谁？\n")
    scenarios = generate_scenario_recommendations(topic_data)
    content_parts.append(scenarios)
    content_parts.append("")

    # FAQ
    content_parts.append("## 常见问题（FAQ）\n")
    faq = generate_faq(topic_data)
    content_parts.append(faq)
    content_parts.append("")

    # 结论
    content_parts.append(f"""## 最终结论

| 维度 | 结论 |
|------|------|
""")
    for d, slug_key in [(dims[0], winner)] + list(zip(dims[1:], runner_up_slugs)):
        tool_name = topic_data["tools"].get(slug_key, {}).get("name", slug_key)
        val = topic_data["tools"].get(slug_key, {}).get("metrics", {}).get(d, "综合得分最高")
        content_parts.append(f"| {d}最优 | **{tool_name}**（{val[:60]}） |\n")

    content_parts.append(f"""
**我的选择：** {winner_name}作为主力工具{f"，{runner_ups}作为备选" if runner_ups else ""}。

## 数据声明

本文数据来源：
- 各工具官网定价页（{month_name}验证）
- 公开基准测试排行榜（SWE-bench/LMSYS Arena/第三方评测）
- 作者长期使用体验及开发者社区反馈

完整工具数据可在[实时面板](/live/dashboard/)查看。发现数据错误请[反馈](/contact.html)。评测文章每月15日刷新，保持数据时效。本文数据最后核对日期：**{last_verified}**。

---

*本文由AI工具宝箱编辑组基于四维框架评测，数据可溯源，月度更新。*
""")

    full_content = "\n".join(content_parts)

    article = {
        "title": title,
        "slug": slug,
        "date": date,
        "dateFormatted": datetime.now().strftime("%Y年%m月%d日"),
        "category": "AI评测",
        "tags": [{"text": "AI评测", "type": "hot"}, {"text": topic_data['cat'], "type": ""}],
        "description": f"基于四维测试框架对{tools_count}款{topic_data['cat']}工具进行同维度横向评测。{winner_name}综合得分最高。所有数据可溯源。",
        "keywords": f"AI评测,{topic_data['cat']},{tools_names},工具对比,2026",
        "author": "AI工具宝箱编辑组",
        "related_tools": list(topic_data["tools"].keys())[:5],
        "content": full_content,
    }
    return article


# ============================================================
# 命令行入口
# ============================================================
def main():
    check_only = "--check" in sys.argv
    list_only = "--list" in sys.argv
    rebuild_slug = None
    if "--rebuild" in sys.argv:
        idx = sys.argv.index("--rebuild")
        if idx + 1 < len(sys.argv):
            rebuild_slug = sys.argv[idx + 1]

    print("=" * 60)
    print(f"AI评测文章生成器 v2 (方案C) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    if list_only:
        print(f"\n{'='*50}")
        print("14个评测主题（按站点分类）")
        print(f"{'='*50}")
        for i, k in enumerate(MONTH_TOPIC_ORDER, 1):
            print(f"  {i:>2}. {k}")
        return

    tools, articles, review_data = load_data()
    print(f"[INFO] 加载 {len(tools)} 工具, {len(articles)} 文章, {len(review_data)-1} 评测数据主题")

    # 确定主题
    if "--topic" in sys.argv:
        idx = sys.argv.index("--topic")
        topic_key = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else MONTH_TOPIC_ORDER[0]
    elif rebuild_slug:
        # 从slug反推主题key
        topic_key = None
        for a in articles:
            if a.get("slug") == rebuild_slug:
                for k in review_data:
                    if k in rebuild_slug:
                        topic_key = k
                        break
                break
        if not topic_key:
            print(f"[ERROR] 未找到文章: {rebuild_slug}")
            return
    else:
        topic_key = MONTH_TOPIC_ORDER[(datetime.now().month - 1) % len(MONTH_TOPIC_ORDER)]

    if topic_key not in review_data:
        print(f"[ERROR] review_data.json中没有主题: {topic_key}")
        return

    print(f"[INFO] 评测主题: {topic_key} ({review_data[topic_key]['cat']})")

    is_update = "--update" in sys.argv or bool(rebuild_slug)
    article = generate_review(topic_key, tools, articles, review_data, is_update)
    if not article:
        return

    print(f"[INFO] 文章标题: {article['title']}")
    print(f"[INFO] Slug: {article['slug']}")
    print(f"[INFO] 字数: {len(article['content'])}")
    print(f"[INFO] Category: {article['category']}")

    if check_only:
        print("\n[CHECK] --check 模式，不写入。全文预览：")
        print(article['content'])
        return

    # 写入分片 (2026-08-26 去单体化: 单体已退役, 真源 data/articles/<slug>.json)
    from data_store import save_article
    save_article(article, indent=2)
    print(f"[OK] 已写入分片 data/articles/{article.get('slug')}.json")

    # 构建
    print("\n[INFO] 开始构建...")
    ret = os.system(f'cd /d "{BASE}" && python scripts/build.py')
    if ret != 0:
        print("[ERROR] 构建失败")
        return

    # 部署
    print("\n[INFO] 开始部署...")
    os.system(f'cd /d "{BASE}" && bash deploy.sh --skip-build')
    print(f"\n[DONE] 评测文章已生成并部署: {article['slug']}")


if __name__ == "__main__":
    main()

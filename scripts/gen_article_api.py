#!/usr/bin/env python3
"""
gen_article_api.py — 调用硅基流动 MiniMax-M2.5 生成SEO文章（完整版）
基于旧版自动化任务prompt全面升级，包含：
  - 原创性测试 + 质量检查清单
  - 完整去AI味规则 + 后处理
  - 强制内链验证
  - OG图片生成
  - 一键发布 pipeline

用法:
    python gen_article_api.py --auto --publish   # 全自动：生成+发布+OG图+构建+推送
    python gen_article_api.py --auto              # 只生成不发布
    python gen_article_api.py --topic "主题"       # 指定主题
    python gen_article_api.py --type A             # 指定类型
    python gen_article_api.py --keywords "AI编程工具|AI编程工具推荐,AI写代码,免费AI编程"  # Agent核实的关键词
    python gen_article_api.py --auto --dry-run     # 只选主题不生成
    python gen_article_api.py --list               # 查看轮换状态

输出文件: data/_api_article_draft.json
"""

import json, sys, os, time, random, re, argparse, subprocess, shutil
from datetime import datetime
from openai import OpenAI

sys.stdout.reconfigure(encoding='utf-8')

# ===== API 配置 =====
import os
from dotenv import load_dotenv

# Load .env file (project root)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL = "Pro/MiniMaxAI/MiniMax-M2.5"
MAX_TOKENS = 8000
TEMPERATURE = 0.8

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARTICLES_FILE = os.path.join(DATA_DIR, 'articles.json')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')
STATE_FILE = os.path.join(DATA_DIR, '_article_api_state.json')
DRAFT_FILE = os.path.join(DATA_DIR, '_api_article_draft.json')
OG_DIR = os.path.join(BASE_DIR, 'images', 'og')

# ===== 文章类型定义 =====
ARTICLE_TYPES = {
    'A': {
        'label': '实测数据型',
        'description': '亲自使用某个AI工具，记录真实体验数据',
        'structure': '开头 + 为什么写这篇 + 3个实测段落 + 对比表格 + 踩坑经验 + FAQ(3个问答) + 总结',
        'requirements': [
            '必须有具体的实测数据（数字、百分比、耗时、翻车率等）',
            '必须有对比表格（至少1个Markdown表格）',
            '有个人真实使用体验和踩坑经历',
            '有明确的推荐结论（不是"各有优劣看你需求"）',
            '内容简洁有力，不啰嗦，写完觉得没啥可补充的就收',
        ],
    },
    'B': {
        'label': '观点对比型',
        'description': '深度对比两个或多个工具，给出明确推荐',
        'structure': '开头 + 为什么写这篇 + 3个对比段落 + 评分表格 + 踩坑经验 + FAQ(3个问答) + 总结',
        'requirements': [
            '必须给出明确推荐，不是"各有优劣看你需求"',
            '必须有对比表格（维度打分，至少1个Markdown表格）',
            '有个人使用经验和偏好',
            '有场景化推荐（什么人用什么）',
            '内容简洁有力，不啰嗦，写完觉得没啥可补充的就收',
        ],
    },
    'C': {
        'label': '资源汇总型',
        'description': '整合网上分散但高价值的资源，做一站式参考',
        'structure': '开头 + 筛选标准说明 + 分类推荐(3-4个分类) + 对比表格 + FAQ(3个问答) + 总结',
        'requirements': [
            '分类清晰，每个分类有筛选标准说明',
            '必须有对比表格',
            '有使用建议和个人推荐',
            '开头要有"持续更新"承诺（增强SEO长期价值）',
            '内容简洁有力，不啰嗦，写完觉得没啥可补充的就收',
        ],
    },
    'D': {
        'label': '操作指南型',
        'description': '针对具体AI工具的使用教程，解决"如何xxx"类搜索需求',
        'structure': '开头 + 前置准备 + 3-4个步骤段落 + 踩坑经验 + FAQ(3个问答) + 总结',
        'requirements': [
            '以"老用户带新手"视角，语气像朋友教你',
            '步骤具体到"点击哪个按钮""在哪找到这个选项"',
            '有常见问题和踩坑经验',
            '有真实操作案例（不是抽象描述）',
            '内容简洁有力，不啰嗦，写完觉得没啥可补充的就收',
        ],
    },
}

# ===== 去AI味规则（完整版） =====
AI_SMELL_RULES = """
## 去AI味铁律（必须严格遵守）

### 禁用词汇表
"强大的""智能的""高效的""全面的""不可或缺的""革命性的""颠覆性的""一键生成""轻松实现""极大地""显著提升""大幅优化""无疑""显而易见"

### 禁用句式
- "首先...其次...最后..."（改成自然过渡）
- "不仅...而且...更是..."（太啰嗦）
- "众所周知""不言而喻""毋庸置疑"（说教味）
- "此外""另外""值得一提的是"（每个段落都用就很假）
- "本文将""这篇文章"（不要自指）
- "让我们一起来看看"（废话）

### 禁用标题格式
"全面解析""深度解读""一文读懂""终极指南""完整攻略""保姆级教程""最全汇总"

### 必须遵守的风格规则
1. 观点要有明确立场，禁止"各有优劣看你需求""取决于你的具体场景"这种和稀泥结论
2. 数据要具体，禁止"显著提升""大幅优化"等模糊描述，必须是"从47%提升到63%"这种
3. 适当使用口语化表达："说实话""我测了一下""别小看这个""踩了个大坑""没想到"
4. 标题要有信息增量，让人一看就知道这篇文章有什么不一样
5. 每段开头不能都是同一个句式，要有变化
6. 禁止每段都用总结性句子结尾，让人看着像教科书
"""

# ===== 禁止的内容类型 =====
BANNED_CONTENT_TYPES = """
## 禁止的内容类型（绝对不能写）
1. 纯盘点列举（"10个最好的AI工具"——没有实测数据就是水文章）
2. 官网信息搬运（功能介绍堆砌，没有个人观点）
3. 无观点的中立比较（"各有优劣，看你需求"）
4. 没有数据支撑的主观评价（"我觉得很好用"）
5. 重复已有角度的内容（如果网上已经有100篇类似的，你的角度必须不同）
"""

# ===== 质量检查清单 =====
QUALITY_CHECKLIST = """
## 质量检查清单（生成文章前自问自检）
- [ ] 这篇文章有没有网上找不到的信息？（实测数据、独家观点、一手经验）
- [ ] 有没有具体数据或个人经验支撑？（数字、百分比、耗时）
- [ ] 结论是否明确，不是模棱两可？（推荐X而不是"看需求"）
- [ ] 是否有结构化表格方便读者理解？（至少1个Markdown表格）
- [ ] 内链是否自然，不是硬塞的？（3-5个工具页链接）
- [ ] 措辞是否自然，没有AI腔？（检查禁用词汇表）
- [ ] 是否包含FAQ部分？（3-5个问答）
- [ ] 是否有"踩坑经验"段落？（增强可信度）
- [ ] 是否有"为什么写这篇"段落？（展示E-E-A-T的"经验"维度）
"""

# ===== 主题库（按类型，每种7个） =====
TOPIC_POOL = {
    'A': [
        "我用Cursor和Claude Code各写了50个完整项目，从启动到部署全流程对比",
        "实测Gemini 3 Pro处理200万token超长文档：30篇论文同时分析，哪些场景真有用",
        "DeepSeek V3.2免费API跑10000次请求的真实成本和速度数据",
        "Midjourney V7 vs Flux Pro vs 可灵：同一个prompt跑200次，统计翻车率",
        "我用AI工具从零做了10个网站，记录每个工具的真实耗时和成本",
        "ChatGPT Plus vs Claude Pro vs DeepSeek：连续30天每天写一篇文章，记录每日体验差异",
        "实测5款AI编程工具重构同一个10000行项目：代码质量、速度、成本全面对比",
    ],
    'B': [
        "Claude Code vs Cursor Pro：2026年AI编程工具到底选哪个（附实测数据）",
        "DeepSeek V3.2 vs ChatGPT GPT-5.4：中文场景谁更强？100道题实测",
        "Midjourney vs 可灵 vs 豆包：中国用户最该用哪个AI画图工具",
        "Notion AI vs 飞书AI vs 语雀AI：国产办公AI能不能替代Notion",
        "n8n vs Coze vs Dify：AI工作流搭建，哪个最不折腾",
        "HeyGen vs 剪映 vs CapCut：AI视频制作工具2026年该选谁",
        "Perplexity vs 秘塔 vs 博查：AI搜索引擎中文效果实测",
    ],
    'C': [
        "2026年完全免费的AI工具清单（持续更新，已测试70+款）",
        "国内AI工具替代方案大全：ChatGPT/Claude/Midjourney的国产平替",
        "AI编程工具从入门到精通：一份保姆级工具地图",
        "2026年AI副业赚钱的20种方式（附真实案例和收入数据）",
        "AI自学编程完整路径：从零基础到能接单，需要什么工具和多久",
        "小团队AI工具栈推荐：5人以下团队的最佳AI工具组合",
        "内容创作者的AI工具箱：从选题到变现全流程覆盖",
    ],
    'D': [
        "如何用Claude Code从零开发一个完整网站（2026最新教程）",
        "国内如何使用Cursor AI编程工具：注册、配置、使用全流程",
        "如何用DeepSeek API搭建自己的AI助手（Python教程）",
        "Midjourney新手入门指南：从注册到画出第一张满意的作品",
        "如何用n8n搭建自动化工作流：5个实用案例手把手教",
        "AI配音工具使用教程：从文字到专业级语音的完整流程",
        "如何用AI工具做小红书爆款图文（2026版实战教程）",
    ],
}


# ===== 工具数据（从tools.json动态加载） =====
def load_tool_slugs():
    """从tools.json加载所有工具slug和名称"""
    if os.path.exists(TOOLS_FILE):
        with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        return [(t['slug'], t['name']) for t in tools]
    return [
        ("chatgpt", "ChatGPT"), ("claude", "Claude"), ("deepseek", "DeepSeek"),
        ("gemini", "Gemini"), ("cursor", "Cursor"), ("midjourney", "Midjourney"),
        ("kimi", "Kimi"), ("doubao", "豆包"), ("notion-ai", "Notion AI"),
        ("runway", "Runway"), ("stable-diffusion", "Stable Diffusion"),
        ("suno", "Suno"), ("perplexity", "Perplexity"),
        ("github-copilot", "GitHub Copilot"), ("bolt.new", "Bolt.new"),
        ("windsurf", "Windsurf"), ("dall-e-3", "DALL-E 3"),
        ("kling-ai", "可灵AI"), ("claude-code", "Claude Code"),
        ("coze", "Coze"), ("dify", "Dify"), ("flux", "Flux"),
        ("canva-ai", "Canva AI"), ("heygen", "HeyGen"),
        ("elevenlabs", "ElevenLabs"), ("notebooklm", "NotebookLM"),
        ("poe", "Poe"), ("v0.dev", "v0.dev"), ("lovable", "Lovable"),
        ("grammarly-ai", "Grammarly AI"), ("microsoft-copilot", "Microsoft Copilot"),
        ("sora", "Sora"), ("descript", "Descript"), ("capcut-ai", "CapCut AI"),
        ("ideogram", "Ideogram"),
    ]


def pick_tool_links(count=4, topic_hint=None):
    """智能选择内链工具：优先选与主题相关的"""
    tools = load_tool_slugs()
    topic_lower = (topic_hint or '').lower()

    # 相关工具优先
    relevant = []
    unrelated = []
    for slug, name in tools:
        if any(part in topic_lower for part in slug.split('-') + [name.lower()]):
            relevant.append((slug, name))
        else:
            unrelated.append((slug, name))

    # 优先相关工具，不够再补随机的
    random.shuffle(relevant)
    random.shuffle(unrelated)
    selected = relevant[:min(count, len(relevant))]
    remaining = count - len(selected)
    if remaining > 0:
        selected += unrelated[:remaining]

    return selected


def make_tool_link(slug, name):
    """生成工具内链Markdown"""
    return f"[{name}](https://www.aitoolbox.hk/tools/{slug}/)"


# ===== API调用 =====
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def call_api(system_prompt, user_prompt, max_retries=3):
    """调用硅基流动API，带重试"""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"  API error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                return None


# ===== 读取现有数据 =====
def load_articles():
    with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_type': 'D', 'article_count': 0, 'used_topics': []}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===== 去AI味后处理 =====
def de_ai_process(content):
    """对生成内容做去AI味后处理"""
    replacements = [
        # 禁用词替换
        ('强大的', '不错的'), ('智能的', '好用的'), ('高效的', '省时的'),
        ('全面的', '覆盖面广的'), ('不可或缺的', '很实用的'),
        ('革命性的', '有突破的'), ('颠覆性的', '有创新的'),
        ('一键生成', '快速生成'), ('轻松实现', '方便做到'),
        ('极大地', '很明显地'), ('显著提升', '提升了'),
        ('大幅优化', '优化了'), ('无疑', '确实'),
        ('显而易见', '很明显'), ('毋庸置疑', '不可否认'),
        # 禁用句式替换
        ('首先，', ''), ('其次，', ''), ('最后，', ''),
        ('此外，', ''), ('另外，', ''), ('值得一提的是，', ''),
        ('众所周知，', ''), ('不言而喻，', ''), ('综上所述，', ''),
        ('让我们一起来看看', ''),
        ('本文将', ''), ('这篇文章将', ''),
    ]
    for old, new in replacements:
        content = content.replace(old, new)

    # 清理替换后可能出现的多余空格
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'  +', ' ', content)

    return content


# ===== 内链验证 =====
def validate_links(content, expected_links):
    """验证文章中的内链数量和质量"""
    link_pattern = r'\[([^\]]+)\]\(https://www\.aitoolbox\.hk/tools/([^/]+)/\)'
    found_links = re.findall(link_pattern, content)
    count = len(found_links)

    warnings = []
    if count < 3:
        warnings.append(f"内链只有{count}个，要求至少3个")
    if count > 6:
        warnings.append(f"内链有{count}个，建议不超过6个（过多影响阅读）")

    return count, warnings


# ===== 质量检查 =====
def quality_check(article):
    """对文章做质量检查，返回通过/警告/失败"""
    content = article['content']
    warnings = []
    passes = []

    # 1. 字数检查
    word_count = len(content)
    if word_count >= 1500:
        passes.append(f"字数: {word_count}字")
    else:
        warnings.append(f"字数: {word_count}字（偏短，建议1500字以上）")

    # 2. 表格检查
    table_count = content.count('|---')
    if table_count >= 1:
        passes.append(f"表格: {table_count}个")
    else:
        warnings.append("表格: 缺少结构化表格（至少1个）")

    # 3. FAQ检查
    faq_count = len(re.findall(r'#{2,3}\s*(?:FAQ|常见问题)', content, re.IGNORECASE))
    if faq_count >= 1:
        passes.append(f"FAQ: 有")
    else:
        warnings.append("FAQ: 缺少FAQ部分")

    # 4. 踩坑经验检查
    if any(kw in content for kw in ['踩坑', '坑点', '避坑', '翻车', '教训', '注意', '别犯']):
        passes.append("踩坑经验: 有")
    else:
        warnings.append("踩坑经验: 缺少踩坑经验段落")

    # 5. 为什么写这篇检查
    if any(kw in content for kw in ['为什么写', '为什么做', '起因', '初衷', '动机', '背景']):
        passes.append('\u201c为什么写这篇\u201d: 有')
    else:
        warnings.append('\u201c为什么写这篇\u201d: 缺少（E-E-A-T经验维度）')

    # 6. 结论检查
    if any(kw in content for kw in ['推荐', '建议用', '建议选', '我的选择']):
        passes.append('明确结论: 有')
    else:
        warnings.append('明确结论: 缺少（禁止和稀泥）')

    # 7. AI味检查
    ai_words = ['强大的', '智能的', '革命性的', '颠覆性的', '一键生成', '显著提升', '大幅优化']
    found_ai = [w for w in ai_words if w in content]
    if found_ai:
        warnings.append(f'AI味词汇: {", ".join(found_ai)}（建议替换）')
    else:
        passes.append('AI味词汇: 0个')

    # 8. 内链检查
    link_count, link_warnings = validate_links(content, None)
    if link_count >= 3:
        passes.append(f"内链: {link_count}个")
    else:
        warnings.append(f"内链: 只有{link_count}个（至少3个）")
    warnings.extend(link_warnings)

    return passes, warnings


# ===== 生成文章 =====
def generate_article(topic, article_type, existing_titles, seo_keywords=None):
    """调用API生成文章
    seo_keywords: tuple(main_keyword, [longtail_list]) 由Agent核实过的真实关键词
    """
    type_info = ARTICLE_TYPES[article_type]
    tools = pick_tool_links(random.randint(3, 5), topic_hint=topic)
    link_md = "、".join([make_tool_link(s, n) for s, n in tools])
    tool_names = [n for _, n in tools]

    today = datetime.now()
    date_str = today.strftime('%m/%d')
    date_full = today.strftime('%Y年%m月%d日')

    # 已有标题列表
    existing_titles_str = '\n'.join([f'- {t}' for t in existing_titles[:50]])

    # 构建需求列表
    requirements_str = '\n'.join([f'  - {r}' for r in type_info['requirements']])

    system_prompt = f"""你是AI工具评测博主，运营网站www.aitoolbox.hk。你每天使用各种AI工具，有大量真实使用经验和踩坑经历。你的文章有信息增量，不是网上能搜到的泛泛而谈。

## 核心原则：发不一样的，不发别人都有的

Google不缺内容，缺的是有增量的内容。每篇文章必须通过"原创性测试"：
- 这篇文章有没有网上找不到的信息？（实测数据、独家观点、一手经验）
- 如果用ChatGPT能生成一样的，这篇内容就没有存在价值

## 你的写作风格
- 像朋友在聊天，不像在写报告
- 有明确立场，敢于说"推荐用X"而不是"各有优劣"
- 数据具体，不说"显著提升"，说"从47%提升到63%"
- 有个人经历和真实案例
- 适当口语化："说实话""我测了一下""别小看这个""踩了个大坑""没想到"

{AI_SMELL_RULES}

{BANNED_CONTENT_TYPES}

{QUALITY_CHECKLIST}

## 文章类型：{article_type}. {type_info['label']}
{type_info['description']}
段落结构：{type_info['structure']}
具体要求：
{requirements_str}

## ⚠️ 风格要求
不要凑字数，不要注水。写完觉得该说的都说了就收，读者不会因为你多写了1000字就多给你点赞。
内容有信息量比字数重要。一个有数据的短段比一段废话长段有价值得多。

## 内链要求（必须遵守）
文章中必须自然地插入3-5个工具内链。内链必须在正文中自然出现，不是硬塞的。
格式：[工具名](https://www.aitoolbox.hk/tools/工具slug/)
本篇可用内链工具：{link_md}

## 已有文章标题（不能重复，角度必须不同）
{existing_titles_str}"""

    # 如果有Agent核实过的关键词，注入到prompt中
    if seo_keywords and seo_keywords[0]:
        main_kw, longtail_list = seo_keywords
        longtail_str = '、'.join(longtail_list) if longtail_list else '（无）'
        system_prompt += f"""

## SEO关键词（已通过搜索数据核实，文章必须围绕这些词展开）
核心关键词：{main_kw}
长尾关键词：{longtail_str}
要求：核心关键词必须出现在标题和开头第一段。长尾词要自然分布在不同段落中，不要堆砌。"""

    # 不同类型的user prompt
    structure = """
结构模板（必须包含以下所有部分）：

# [包含核心关键词的标题]

[开头：直接给出核心结论/数据亮点，100字内，让读者一秒知道值不值得看]

## 为什么写这篇
[个人动机/痛点，展示E-E-A-T的"经验"维度。不要写成"因为XX很重要"，要写成"上周我在做XX的时候遇到了XX问题..."这种有场景的]

## [正文主体]
[根据内容类型展开，包含H2/H3层级，每段有实际内容不是废话]

### [对比/数据表格]
[必须有结构化Markdown表格，Google喜欢表格。不是简单罗列，是有维度的对比]

## 踩坑经验
[个人真实经历，增强可信度。具体场景+具体问题+具体解决方法]

## FAQ
[3-5个读者最可能问的问题，答案简洁有信息量。Q用粗体]

## 总结
[明确结论+具体推荐+下一步建议。不是"各有优劣"，是"如果你是XX，推荐用XX"]"""

    if article_type == 'A':
        user_prompt = f"""写一篇实测数据型文章，主题：{topic}

核心要求：必须有真实的实测数据支撑（数字、百分比、耗时、翻车率等），这些数据要让读者觉得"这个人真的用过"。
{structure}

请在文章最后（总结之后）附加以下信息块（不要混入正文中）：

---
KEYWORDS: [1个核心关键词]
LONGTAIL: [3-5个长尾关键词，用逗号分隔]
---

不需要输出slug、日期等元数据。只输出Markdown文章+关键词块。"""

    elif article_type == 'B':
        user_prompt = f"""写一篇观点对比型文章，主题：{topic}

核心要求：必须给出明确的推荐结论。读者看完要知道"该选哪个"，而不是"各有优劣你自己想"。
每个工具要有具体的评分数据（不是5星这种虚的，是"我测了50道题，X对了42道"这种）。
{structure}

请在文章最后（总结之后）附加以下信息块（不要混入正文中）：

---
KEYWORDS: [1个核心关键词]
LONGTAIL: [3-5个长尾关键词，用逗号分隔]
---

不需要输出slug、日期等元数据。只输出Markdown文章+关键词块。"""

    elif article_type == 'C':
        user_prompt = f"""写一篇资源汇总型文章，主题：{topic}

核心要求：不是简单罗列，每个推荐都要有"为什么选它"的理由。要有筛选标准说明——"这70个工具我是怎么从200+个里筛出来的"。
开头要有"持续更新"承诺。
{structure}

请在文章最后（总结之后）附加以下信息块（不要混入正文中）：

---
KEYWORDS: [1个核心关键词]
LONGTAIL: [3-5个长尾关键词，用逗号分隔]
---

不需要输出slug、日期等元数据。只输出Markdown文章+关键词块。"""

    elif article_type == 'D':
        user_prompt = f"""写一篇操作指南型文章，主题：{topic}

核心要求：以"老用户带新手"视角，像朋友手把手教你。步骤要具体到"点击左上角的XX按钮""在设置里找到XX选项"。
要有"我当初第一次用的时候踩了个坑：XX"这种真实经验。
{structure}

请在文章最后（总结之后）附加以下信息块（不要混入正文中）：

---
KEYWORDS: [1个核心关键词]
LONGTAIL: [3-5个长尾关键词，用逗号分隔]
---

不需要输出slug、日期等元数据。只输出Markdown文章+关键词块。"""

    print(f"  调用 {MODEL} 生成文章...")
    print(f"  主题: {topic}")
    print(f"  类型: {type_info['label']}")

    start = time.time()
    content = call_api(system_prompt, user_prompt)
    elapsed = time.time() - start

    if content is None:
        print("  ❌ API调用失败")
        return None

    print(f"  ✅ 生成成功 ({elapsed:.1f}秒)")

    # ===== 后处理 =====
    # 0. 提取关键词块（在去AI味和标题提取之前）
    main_keyword, longtail_keywords = extract_seo_keywords(content)
    # 去掉关键词块（不放入正文）
    content = re.sub(r'\n---\nKEYWORDS:.*?LONGTAIL:.*?\n---', '', content, flags=re.DOTALL).strip()

    # 1. 去AI味
    content = de_ai_process(content)

    # 2. 提取标题（第一行#开头的）
    lines = content.strip().split('\n')
    title = topic
    for line in lines:
        if line.startswith('# ') and not line.startswith('## '):
            title = line.lstrip('# ').strip()
            break

    # 3. 如果内容里有标题行，去掉它（metadata里已经有title了）
    content_lines = []
    for line in lines:
        if line.startswith('# ') and not line.startswith('## '):
            continue
        content_lines.append(line)
    content = '\n'.join(content_lines).strip()

    # 4. 生成slug
    slug = generate_slug(title)

    # 5. 自动推断分类
    categories = {
        'AI趋势': ['裁员', '失业', '行业', '趋势', '副业', '赚钱'],
        'AI对话': ['chatgpt', 'claude', 'deepseek', 'gemini', 'kimi', '对话', '大模型', '豆包', '通义'],
        'AI编程': ['cursor', 'claude code', '编程', '代码', '开发', 'github', 'copilot'],
        'AI绘画': ['midjourney', 'stable diffusion', 'flux', '可灵', '画图', '绘画', '图像'],
        'AI视频': ['runway', 'sora', 'pika', 'kling', '视频', 'heygen'],
        'AI写作': ['写作', '文案', '文章', '内容', 'notion'],
        'AI工具': ['免费', '工具', '推荐', '替代', '清单', '效率'],
    }
    category = 'AI工具'
    topic_lower = topic.lower() + title.lower()
    for cat, keywords in categories.items():
        if any(k in topic_lower for k in keywords):
            category = cat
            break

    # 6. 生成description（取前200字，优化截断）
    desc = content[:200].replace('\n', ' ').strip()
    # 在句号处截断
    if '。' in desc and len(desc) > 100:
        desc = desc[:desc.rfind('。') + 1]
    elif '！' in desc and len(desc) > 100:
        desc = desc[:desc.rfind('！') + 1]
    if len(desc) < 50:
        desc = content[:150].replace('\n', ' ').strip()
    if len(desc) > 200:
        desc = desc[:197] + '...'

    # 7. 生成关键词（Agent预置 > API输出 > fallback提取）
    if seo_keywords and seo_keywords[0]:
        # Agent核实过的关键词优先
        main_keyword = seo_keywords[0]
        longtail_keywords = seo_keywords[1] or []
        keywords = ','.join([main_keyword] + longtail_keywords[:5])
    elif main_keyword and longtail_keywords:
        keywords = ','.join([main_keyword] + longtail_keywords[:5])
    else:
        keywords = extract_keywords(topic, title, content)

    article = {
        "title": title,
        "slug": slug,
        "date": date_str,
        "dateFull": date_full,
        "category": category,
        "description": desc,
        "keywords": keywords,
        "_main_keyword": main_keyword or topic,  # 内部标记
        "_longtail": longtail_keywords or [],       # 内部标记
        "content": content,
        "_type": article_type,  # 内部标记，不插入JSON
    }

    return article


def generate_slug(title):
    """从标题生成英文slug"""
    replacements = {
        'ChatGPT': 'chatgpt', 'Claude': 'claude', 'DeepSeek': 'deepseek',
        'Gemini': 'gemini', 'Cursor': 'cursor', 'Midjourney': 'midjourney',
        'GPT': 'gpt', 'AI': 'ai', 'n8n': 'n8n', 'Coze': 'coze',
        'Dify': 'dify', 'Flux': 'flux', 'HeyGen': 'heygen',
        'Notion': 'notion', 'Perplexity': 'perplexity', 'Kimi': 'kimi',
        '豆包': 'doubao', '可灵': 'kling', '通义': 'tongyi',
        'Sora': 'sora', 'Stable Diffusion': 'stable-diffusion',
        'Runway': 'runway', 'Suno': 'suno', 'DALL-E': 'dall-e',
        'GitHub Copilot': 'github-copilot', 'ElevenLabs': 'elevenlabs',
        'vs': 'vs', 'VS': 'vs', '对比': 'vs', '对标': 'vs',
        '评测': 'review', '测评': 'review', '实测': 'test',
        '指南': 'guide', '教程': 'tutorial', '推荐': 'recommendation',
        '大全': 'list', '清单': 'list', '入门': 'beginner',
        '使用': 'use', '如何': 'how-to', '免费': 'free',
        '工具': 'tools', '副业': 'side-hustle', '赚钱': 'make-money',
        '编程': 'coding', '画图': 'image-gen', '视频': 'video',
        '写作': 'writing', '搜索': 'search', '配音': 'voiceover',
        '2026': '2026', '2026年': '2026',
    }

    # 按长度排序，先替换长的避免冲突
    sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)
    parts = []
    remaining = title
    for cn, en in sorted_replacements:
        if cn in remaining:
            parts.append(en)
            remaining = remaining.replace(cn, ' ', 1)

    slug = '-'.join(parts)
    date_suffix = datetime.now().strftime('%m%d')
    if slug:
        slug = f"{slug}-{date_suffix}"
    else:
        slug = f"article-{date_suffix}"
    return slug.lower().strip('-').replace('---', '-').replace('--', '-')


def extract_seo_keywords(content):
    """从文章末尾的关键词块中提取核心关键词和长尾词"""
    main_keyword = ''
    longtail = []

    # 匹配 KEYWORDS: xxx / LONGTAIL: xxx 块
    kw_match = re.search(r'KEYWORDS:\s*(.+)', content)
    lt_match = re.search(r'LONGTAIL:\s*(.+)', content)

    if kw_match:
        main_keyword = kw_match.group(1).strip().strip('"\'')
    if lt_match:
        raw = lt_match.group(1).strip()
        # 支持逗号、顿号、中文逗号分隔
        longtail = [w.strip().strip('"\'') for w in re.split(r'[,，、]', raw) if 2 <= len(w.strip()) <= 30]

    return main_keyword, longtail


def extract_keywords(topic, title, content):
    """从主题和内容中提取关键词（fallback方案）"""
    words = []
    for word in (topic + ' ' + title).split('、，, '):
        word = word.strip('：:,。.vs VS！!？?/／（）()【】[]')
        if 2 <= len(word) <= 20:
            words.append(word)

    generic = ['AI工具', '2026']
    all_kw = list(dict.fromkeys(words + generic))[:12]  # 去重保序
    return ','.join(all_kw)


# ===== 轮换逻辑 =====
def get_next_type(state):
    """A/B/C/D轮换"""
    order = ['A', 'B', 'C', 'D']
    idx = order.index(state['last_type'])
    return order[(idx + 1) % len(order)]


def get_next_topic(article_type, existing_titles, used_topics):
    """从主题库选一个没写过的主题"""
    pool = TOPIC_POOL.get(article_type, TOPIC_POOL['B'])
    available = [t for t in pool if not any(similar(t, et) for et in existing_titles)]
    # 排除最近用过的（避免连续重复）
    available = [t for t in available if t not in (used_topics or [])[-5:]]
    if not available:
        available = pool
    return random.choice(available)


def similar(a, b):
    """简单相似度判断"""
    a_set = set(a)
    b_set = set(b)
    overlap = len(a_set & b_set) / max(len(a_set), 1)
    return overlap > 0.5


# ===== 发布流程 =====
def insert_article_to_json(article, articles_file):
    """将文章插入到articles.json头部"""
    with open(articles_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    # 移除内部标记
    clean_article = {k: v for k, v in article.items() if not k.startswith('_')}

    # 检查slug是否重复
    existing_slugs = [a['slug'] for a in articles]
    if clean_article['slug'] in existing_slugs:
        i = 2
        while f"{clean_article['slug']}-{i}" in existing_slugs:
            i += 1
        clean_article['slug'] = f"{clean_article['slug']}-{i}"

    articles.insert(0, clean_article)

    with open(articles_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 已插入 articles.json（第1篇，共{len(articles)}篇）")
    return True


def generate_og_image(article, seo_dir):
    """为新文章生成OG图片"""
    og_script = os.path.join(seo_dir, 'gen_single_og.py')
    if not os.path.exists(og_script):
        print(f"  ⚠️ gen_single_og.py 不存在，跳过OG图片生成")
        return False

    print(f"  生成OG图片...")
    result = subprocess.run(
        [sys.executable, og_script, article['slug']],
        capture_output=True, timeout=120,
        cwd=seo_dir
    )
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''

    if '成功' in stdout or result.returncode == 0:
        print(f"  ✅ OG图片生成成功")
        return True
    else:
        # 可能已存在
        if '已存在' in stdout:
            print(f"  ⏭️ OG图片已存在，跳过")
            return True
        print(f"  ⚠️ OG图片生成可能失败: {(stdout + stderr)[-200:]}")
        return False


def run_build(seo_dir):
    """执行build.py构建"""
    build_script = os.path.join(seo_dir, 'scripts', 'build.py')
    if not os.path.exists(build_script):
        print(f"  ❌ build.py 不存在: {build_script}")
        return False

    print(f"  构建站点...")
    result = subprocess.run(
        [sys.executable, build_script, '--target', 'all'],
        capture_output=True, timeout=300,
        cwd=seo_dir
    )

    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
    output = (stdout + stderr).strip()
    lines = output.split('\n')
    for line in lines[-5:]:
        if line.strip():
            print(f"    {line}")

    if result.returncode != 0:
        print(f"  ❌ 构建失败 (exit code: {result.returncode})")
        return False

    print(f"  ✅ 构建成功")
    return True


def git_commit_push(article, seo_dir):
    """git commit + push"""
    if not shutil.which('git'):
        print("  ⚠️ git不可用，跳过推送")
        return False

    short_title = article['title'][:40].replace('"', "'")

    try:
        subprocess.run(['git', 'add', '-A'], cwd=seo_dir, capture_output=True, timeout=30)
        subprocess.run(
            ['git', 'commit', '-m', f'文章: {short_title}'],
            cwd=seo_dir, capture_output=True, timeout=30
        )
        result = subprocess.run(
            ['git', 'push'],
            cwd=seo_dir, capture_output=True, timeout=60
        )
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        if result.returncode == 0:
            print(f"  ✅ 已推送到GitHub")
            return True
        else:
            print(f"  ⚠️ push可能失败: {stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ git操作超时")
        return False
    except Exception as e:
        print(f"  ⚠️ git操作异常: {e}")
        return False


# ===== 主流程 =====
def main():
    parser = argparse.ArgumentParser(description='SEO文章API生成器（完整版）')
    parser.add_argument('--topic', type=str, help='指定文章主题')
    parser.add_argument('--type', type=str, choices=['A', 'B', 'C', 'D'], help='指定文章类型')
    parser.add_argument('--auto', action='store_true', help='自动选下一篇（按轮换）')
    parser.add_argument('--dry-run', action='store_true', help='只选主题不生成')
    parser.add_argument('--list', action='store_true', help='查看轮换状态')
    parser.add_argument('--publish', action='store_true', help='生成后自动发布（插入JSON+OG图+构建+推送）')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    parser.add_argument('--no-de-ai', action='store_true', help='跳过去AI味后处理')
    parser.add_argument('--keywords', type=str, default=None, help='Agent核实过的关键词，格式: 核心词|长尾词1,长尾词2,长尾词3')
    args = parser.parse_args()

    # 加载状态
    state = load_state()
    articles = load_articles()
    existing_titles = [a['title'] for a in articles]

    print(f"📰 已有 {len(articles)} 篇文章")
    print(f"📋 上次类型: {state['last_type']} ({ARTICLE_TYPES[state['last_type']]['label']})")

    if args.list:
        next_type = get_next_type(state)
        print(f"\n轮换顺序: A → B → C → D → A ...")
        print(f"下一篇类型: {next_type} ({ARTICLE_TYPES[next_type]['label']})")
        for t, info in ARTICLE_TYPES.items():
            marker = " ← 下一个" if t == next_type else ""
            pool = TOPIC_POOL.get(t, [])
            used = sum(1 for p in pool if any(similar(p, et) for et in existing_titles))
            print(f"  {t}. {info['label']}: {len(pool)}个主题, {used}个已用{marker}")
        return

    # 确定类型和主题
    if args.auto:
        article_type = args.type or get_next_type(state)
        topic = get_next_topic(article_type, existing_titles, state.get('used_topics', []))
    elif args.topic:
        article_type = args.type or guess_type(args.topic)
        topic = args.topic
    else:
        parser.print_help()
        return

    print(f"\n{'='*60}")
    print(f"类型: {article_type} ({ARTICLE_TYPES[article_type]['label']})")
    print(f"主题: {topic}")
    print(f"{'='*60}")

    if args.dry_run:
        return

    # 解析Agent预置关键词
    seo_keywords = None
    if args.keywords:
        parts = args.keywords.split('|', 1)
        main_kw = parts[0].strip() if parts[0].strip() else None
        longtail = []
        if len(parts) > 1 and parts[1].strip():
            longtail = [w.strip() for w in parts[1].split(',') if w.strip()]
        seo_keywords = (main_kw, longtail) if main_kw else None
        if seo_keywords:
            print(f"🔑 SEO关键词（Agent核实）: {main_kw} + {len(longtail)}个长尾词")

    # 生成文章
    article = generate_article(topic, article_type, existing_titles, seo_keywords=seo_keywords)
    if article is None:
        print("❌ 生成失败，退出")
        sys.exit(1)

    # 质量检查
    print(f"\n📊 质量检查:")
    passes, warnings = quality_check(article)
    for p in passes:
        print(f"  ✅ {p}")
    for w in warnings:
        print(f"  ⚠️ {w}")

    # 保存草稿
    output_path = args.output or DRAFT_FILE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(article, f, ensure_ascii=False, indent=2)
    print(f"\n📄 草稿已保存: {output_path}")

    # 更新状态
    state['last_type'] = article_type
    state['article_count'] = state.get('article_count', 0) + 1
    used = state.get('used_topics', [])
    used.append(topic)
    state['used_topics'] = used[-30:]  # 只保留最近30个
    save_state(state)
    print(f"🔄 轮换状态已更新: 下次类型 {get_next_type(state)}")

    # 打印统计
    print(f"\n{'='*60}")
    print(f"标题: {article['title']}")
    print(f"Slug: {article['slug']}")
    print(f"分类: {article['category']}")
    print(f"日期: {article['dateFull']}")
    print(f"字数: {len(article['content'])}字")
    print(f"核心关键词: {article.get('_main_keyword', '-')}")
    print(f"长尾词: {', '.join(article.get('_longtail', []))}")
    print(f"内链数: {article['content'].count('](https://www.aitoolbox.hk/tools/')}")
    print(f"表格数: {article['content'].count('|---')}")
    print(f"FAQ: {'有' if re.search(r'#{2,3}\s*(?:FAQ|常见问题)', article['content'], re.IGNORECASE) else '无'}")
    print(f"{'='*60}")

    # --publish 模式
    if args.publish:
        seo_dir = BASE_DIR
        print(f"\n🚀 开始发布流程...")

        # 1. 插入articles.json
        print("\n[1/4] 插入 articles.json")
        if not insert_article_to_json(article, ARTICLES_FILE):
            print("  ❌ 发布中止：插入JSON失败")
            sys.exit(1)

        # 2. 生成OG图片
        print("\n[2/4] 生成OG图片")
        generate_og_image(article, seo_dir)

        # 3. 构建
        print("\n[3/4] 构建站点")
        if not run_build(seo_dir):
            print("  ❌ 发布中止：构建失败")
            sys.exit(1)

        # 4. git push
        print("\n[4/4] Git推送")
        git_commit_push(article, seo_dir)

        print(f"\n{'='*60}")
        print(f"🎉 发布完成！")
        print(f"   文章: {article['title']}")
        print(f"   Slug: {article['slug']}")
        print(f"   URL: https://www.aitoolbox.hk/articles/{article['slug']}/")
        print(f"{'='*60}")
    else:
        print(f"\n💡 提示: 加 --publish 参数可自动发布（插入JSON+OG图+构建+推送）")


def guess_type(topic):
    """根据主题猜测文章类型"""
    topic_lower = topic.lower()
    if any(w in topic_lower for w in ['实测', '测试', '数据', '跑', '对比数据']):
        return 'A'
    if any(w in topic_lower for w in ['vs', '对比', '谁更强', '选哪个']):
        return 'B'
    if any(w in topic_lower for w in ['大全', '清单', '汇总', '推荐', '合集']):
        return 'C'
    if any(w in topic_lower for w in ['如何', '教程', '指南', '入门', '使用方法']):
        return 'D'
    return 'B'


if __name__ == '__main__':
    main()

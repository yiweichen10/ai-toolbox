#!/usr/bin/env python3
"""
gen_article_api.py — 调用硅基流动 DeepSeek V3.2 生成SEO文章
输入：topic（主题）或 --auto（自动选下一篇）
输出：文章JSON（可直接插入 articles.json）

用法:
    python gen_article_api.py --topic "主题"           # 指定主题
    python gen_article_api.py --type A                  # 指定类型+自动选主题
    python gen_article_api.py --auto                    # 自动选下一篇（按A/B/C/D轮换）
    python gen_article_api.py --auto --dry-run          # 只选主题不生成
    python gen_article_api.py --list                    # 查看轮换状态

输出文件: data/_api_article_draft.json
"""

import json, sys, os, time, random, argparse, subprocess, shutil
from datetime import datetime
from openai import OpenAI

sys.stdout.reconfigure(encoding='utf-8')

# ===== API 配置 =====
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"
MAX_TOKENS = 8000
TEMPERATURE = 0.8

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARTICLES_FILE = os.path.join(DATA_DIR, 'articles.json')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')
STATE_FILE = os.path.join(DATA_DIR, '_article_api_state.json')
DRAFT_FILE = os.path.join(DATA_DIR, '_api_article_draft.json')

# ===== 工具slug列表（用于内链） =====
TOOL_SLUGS = [
    "chatgpt", "claude", "deepseek", "gemini", "cursor", "midjourney",
    "kimi", "doubao", "notion-ai", "runway", "stable-diffusion", "suno",
    "perplexity", "github-copilot", "bolt.new", "windsurf", "dall-e-3",
    "kling-ai", "claude-code", "openai-codex", "n8n", "coze", "dify",
    "flux", "canva-ai", "heygen", "elevenlabs", "notebooklm", "poe",
    "v0.dev", "lovable", "grammarly-ai", "microsoft-copilot",
    "sora", "descript", "capcut-ai", "ideogram",
]

# ===== 文章类型定义 =====
ARTICLE_TYPES = {
    'A': {
        'label': '实测数据型',
        'description': '亲自使用某个AI工具，记录真实体验数据',
    },
    'B': {
        'label': '观点对比型',
        'description': '深度对比两个或多个工具，给出明确推荐',
    },
    'C': {
        'label': '资源汇总型',
        'description': '整合分散但高价值的资源，做一站式参考',
    },
    'D': {
        'label': '操作指南型',
        'description': '针对具体AI工具的使用教程，解决"如何xxx"类搜索需求',
    },
}

# ===== 去AI味规则 =====
AI_SMELL_RULES = """
## 去AI味铁律（必须遵守）
1. 禁止使用以下词汇："强大的""智能的""高效的""全面的""不可或缺的""革命性的""颠覆性的""一键生成""轻松实现""极大地"
2. 禁止使用以下句式："首先...其次...最后""不仅...而且...更是""众所周知""不言而喻""毋庸置疑"
3. 禁止每个段落都用"此外""另外""值得一提的是"开头
4. 不要用"本文将""这篇文章"指代自己
5. 观点要明确有立场，禁止"各有优劣看你需求""取决于你的具体场景"这种和稀泥结论
6. 数据要具体，禁止"显著提升""大幅优化"等模糊描述，必须是"从47%提升到63%"这种
7. 适当使用口语化表达："说实话""我测了一下""别小看这个""踩了个大坑"
8. 标题禁止AI腔，禁止"全面解析""深度解读""一文读懂""终极指南"
"""

# ===== 内链工具 =====
def pick_tool_links(count=3, exclude=None):
    """随机挑选工具slug用于内链"""
    available = [s for s in TOOL_SLUGS if s != exclude]
    return random.sample(available, min(count, len(available)))


def make_tool_link(slug, text=None):
    """生成工具内链Markdown"""
    name = slug.replace('-', ' ').title()
    if text is None:
        text = name
    return f"[{text}](https://www.aitoolbox.hk/tools/{slug}/index.html)"


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

def load_tools():
    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_type': 'D', 'article_count': 0}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===== 主题库（按类型） =====
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


# ===== 生成文章 =====
def generate_article(topic, article_type, existing_titles):
    """调用API生成文章"""
    type_info = ARTICLE_TYPES[article_type]
    links = pick_tool_links(random.randint(3, 5))
    link_md = "、".join([make_tool_link(s) for s in links])
    today = datetime.now()
    date_str = today.strftime('%m/%d')
    date_full = today.strftime('%Y年%m月%d日')

    # 构建已有标题列表，避免重复
    existing_titles_str = '\n'.join([f'- {t}' for t in existing_titles[:50]])

    system_prompt = f"""你是一位资深AI工具评测博主，运营着www.aitoolbox.hk这个网站。你每天使用各种AI工具，积累了大量真实的使用经验和踩坑经历。

你的写作风格：
- 像朋友在聊天，不像在写报告
- 有明确立场，敢于说"推荐用X"而不是"各有优劣"
- 数据具体，不说"显著提升"，说"从47%提升到63%"
- 有个人经历和真实案例
- 适当口语化："说实话""我测了一下""别小看这个"

{AI_SMELL_RULES}

## 文章类型：{type_info['label']}
{type_info['description']}

## 内链要求
文章中必须自然地插入3-5个工具内链，格式：
[工具名](https://www.aitoolbox.hk/tools/工具slug/index.html)

可用工具slug：{', '.join(links)}
内链工具：{link_md}

## 已有文章标题（不能重复，角度必须不同）
{existing_titles_str}"""

    if article_type == 'A':
        user_prompt = f"""写一篇实测数据型文章，主题：{topic}

要求：
1. 2500-4000字
2. 必须有具体的实测数据（数字、百分比、耗时等）
3. 必须有对比表格
4. 有个人真实使用体验和踩坑经历
5. 有明确的推荐结论
6. 必须包含3-5个FAQ问答
7. 结构：前言（直接给结论）→ 为什么写这篇 → 正文（含表格）→ 踩坑经验 → FAQ → 总结

请直接输出Markdown格式的文章正文（##开头），不需要输出标题、slug、日期等元数据。"""

    elif article_type == 'B':
        user_prompt = f"""写一篇观点对比型文章，主题：{topic}

要求：
1. 2500-3500字
2. 必须给出明确推荐，不是"各有优劣看你需求"
3. 必须有对比表格（维度打分）
4. 有个人使用经验和偏好
5. 必须包含3-5个FAQ问答
6. 结构：前言（直接给结论表格）→ 为什么写这篇 → 各工具逐一分析 → 对比表格 → 场景化推荐 → 踩坑经验 → FAQ → 总结

请直接输出Markdown格式的文章正文（##开头），不需要输出标题、slug、日期等元数据。"""

    elif article_type == 'C':
        user_prompt = f"""写一篇资源汇总型文章，主题：{topic}

要求：
1. 2500-3500字
2. 分类清晰，每个分类有筛选标准说明
3. 必须有对比表格
4. 有使用建议和个人推荐
5. 必须包含3-5个FAQ问答
6. 结构：前言（核心结论）→ 为什么写这篇 → 资源分类展示（含表格）→ 使用建议 → 踩坑经验 → FAQ → 总结

请直接输出Markdown格式的文章正文（##开头），不需要输出标题、slug、日期等元数据。"""

    elif article_type == 'D':
        user_prompt = f"""写一篇操作指南型文章，主题：{topic}

要求：
1. 1500-3000字
2. 以"老用户带新手"视角，像朋友教你
3. 步骤具体，有截图描述位置（虽然不能真截图）
4. 有常见问题和踩坑经验
5. 必须包含3-5个FAQ问答
6. 结构：前言（这篇文章帮你解决什么）→ 为什么值得学 → 详细步骤 → 踩坑经验 → FAQ → 总结

请直接输出Markdown格式的文章正文（##开头），不需要输出标题、slug、日期等元数据。"""

    print(f"  调用 {MODEL} 生成文章...")
    print(f"  主题: {topic}")
    print(f"  类型: {type_info['label']}")

    start = time.time()
    content = call_api(system_prompt, user_prompt)
    elapsed = time.time() - start

    if content is None:
        print("  ❌ API调用失败")
        return None

    print(f"  ✅ 生成成功 ({elapsed:.1f}秒, {len(content)}字)")

    # 生成元数据
    title = topic  # 用主题做标题，可以后续优化
    slug = generate_slug(topic)

    # 自动推断分类
    categories = {
        'AI趋势': ['裁员', '失业', '行业', '趋势', '副业', '赚钱'],
        'AI对话': ['chatgpt', 'claude', 'deepseek', 'gemini', 'kimi', '对话', '大模型', '豆包', '通义'],
        'AI编程': ['cursor', 'claude code', '编程', '代码', '开发', 'github', 'copilot'],
        'AI绘画': ['midjourney', 'stable diffusion', 'flux', '可灵', '画图', '绘画', '图像', '豆包画图'],
        'AI视频': ['runway', 'sora', 'pika', 'kling', '视频', 'heygen'],
        'AI写作': ['写作', '文案', '文章', '内容', 'jasper', 'notion'],
        'AI工具': ['免费', '工具', '推荐', '替代', '清单', '效率'],
    }
    category = 'AI工具'  # 默认
    topic_lower = topic.lower()
    for cat, keywords in categories.items():
        if any(k in topic_lower for k in keywords):
            category = cat
            break

    # 生成关键词
    keywords = extract_keywords(topic, content)

    article = {
        "title": title,
        "slug": slug,
        "date": date_str,
        "dateFull": date_full,
        "category": category,
        "description": content[:150].replace('\n', ' ').strip() + '...',
        "keywords": keywords,
        "content": content,
    }

    return article


def generate_slug(topic):
    """从中文主题生成英文slug"""
    # 简单的slug生成：提取中文关键词，用常见翻译映射
    replacements = {
        'ChatGPT': 'chatgpt', 'Claude': 'claude', 'DeepSeek': 'deepseek',
        'Gemini': 'gemini', 'Cursor': 'cursor', 'Midjourney': 'midjourney',
        'GPT': 'gpt', 'AI': 'ai', 'n8n': 'n8n', 'Coze': 'coze',
        'Dify': 'dify', 'Flux': 'flux', 'HeyGen': 'heygen',
        'Notion': 'notion', 'Perplexity': 'perplexity', 'Kimi': 'kimi',
        '豆包': 'doubao', '可灵': 'kling', '通义': 'tongyi',
        '对标': 'vs', '对比': 'vs', '评测': 'review', '测评': 'review',
        '指南': 'guide', '教程': 'tutorial', '推荐': 'recommendation',
        '实测': 'test', '大全': 'list', '清单': 'list',
        '入门': 'beginner', '入门指南': 'beginner-guide',
        '使用': 'use', '如何': 'how-to', '免费': 'free',
        '工具': 'tools', '副业': 'side-hustle',
    }
    parts = []
    for cn, en in replacements.items():
        if cn in topic:
            parts.append(en)
            topic = topic.replace(cn, '')

    slug = '-'.join(parts)
    # 添加日期后缀避免重复
    date_suffix = datetime.now().strftime('%m%d')
    if slug:
        slug = f"{slug}-{date_suffix}"
    else:
        slug = f"article-{date_suffix}"
    return slug.lower().strip('-')


def extract_keywords(topic, content):
    """从主题和内容中提取关键词"""
    # 从主题中提取
    words = []
    for word in topic.split('、') + topic.split(' '):
        word = word.strip('：:,，。.vs VS！!？?/／（）()')
        if 2 <= len(word) <= 20:
            words.append(word)

    # 添加通用关键词
    generic = ['AI工具', '2026']
    all_kw = list(set(words + generic))[:12]
    return ','.join(all_kw)


# ===== 轮换逻辑 =====
def get_next_type(state):
    """A/B/C/D轮换"""
    order = ['A', 'B', 'C', 'D']
    idx = order.index(state['last_type'])
    return order[(idx + 1) % len(order)]


def get_next_topic(article_type, existing_titles):
    """从主题库选一个没写过的主题"""
    pool = TOPIC_POOL.get(article_type, TOPIC_POOL['B'])
    available = [t for t in pool if not any(similar(t, et) for et in existing_titles)]
    if not available:
        available = pool
    return random.choice(available)


def similar(a, b):
    """简单相似度判断"""
    a_set = set(a)
    b_set = set(b)
    overlap = len(a_set & b_set) / max(len(a_set), 1)
    return overlap > 0.5


# ===== 主流程 =====
def insert_article_to_json(article, articles_file):
    """将文章插入到articles.json头部"""
    with open(articles_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    # 检查slug是否重复
    existing_slugs = [a['slug'] for a in articles]
    if article['slug'] in existing_slugs:
        # 加数字后缀
        i = 2
        while f"{article['slug']}-{i}" in existing_slugs:
            i += 1
        article['slug'] = f"{article['slug']}-{i}"
    
    articles.insert(0, article)  # 插入头部（最新文章在前）
    
    with open(articles_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 已插入 articles.json（第1篇，共{len(articles)}篇）")
    return True


def run_build():
    """执行build.py构建"""
    build_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build.py')
    if not os.path.exists(build_script):
        print(f"  ❌ build.py 不存在: {build_script}")
        return False
    
    print(f"  执行构建...")
    result = subprocess.run(
        [sys.executable, build_script, '--target', 'all'],
        capture_output=True, timeout=300,
        cwd=os.path.dirname(build_script)
    )
    
    # 输出最后几行（兼容Windows GBK编码）
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
    output = (stdout + stderr).strip()
    lines = output.split('\n')
    for line in lines[-5:]:
        print(f"    {line}")
    
    if result.returncode != 0:
        print(f"  ❌ 构建失败 (exit code: {result.returncode})")
        return False
    
    print(f"  ✅ 构建成功")
    return True


def git_commit_push(article):
    """git commit + push"""
    seo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 检查是否有git
    if not shutil.which('git'):
        print("  ⚠️ git不可用，跳过推送")
        return False
    
    # 短标题（用于commit message）
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


def main():
    parser = argparse.ArgumentParser(description='SEO文章API生成器')
    parser.add_argument('--topic', type=str, help='指定文章主题')
    parser.add_argument('--type', type=str, choices=['A', 'B', 'C', 'D'], help='指定文章类型')
    parser.add_argument('--auto', action='store_true', help='自动选下一篇（按轮换）')
    parser.add_argument('--dry-run', action='store_true', help='只选主题不生成')
    parser.add_argument('--list', action='store_true', help='查看轮换状态')
    parser.add_argument('--publish', action='store_true', help='生成后自动发布（插入JSON+构建+推送）')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径（默认：data/_api_article_draft.json）')
    args = parser.parse_args()

    # 加载状态
    state = load_state()
    articles = load_articles()
    existing_titles = [a['title'] for a in articles]

    print(f"已有 {len(articles)} 篇文章")
    print(f"上次类型: {state['last_type']} ({ARTICLE_TYPES[state['last_type']]['label']})")

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
        topic = get_next_topic(article_type, existing_titles)
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

    # 生成文章
    article = generate_article(topic, article_type, existing_titles)
    if article is None:
        print("生成失败，退出")
        sys.exit(1)

    # 保存草稿
    output_path = args.output or DRAFT_FILE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(article, f, ensure_ascii=False, indent=2)
    print(f"\n📄 草稿已保存: {output_path}")

    # 更新状态
    state['last_type'] = article_type
    state['article_count'] = state.get('article_count', 0) + 1
    save_state(state)
    print(f"📊 轮换状态已更新: 下次类型 {get_next_type(state)}")

    # 打印统计
    print(f"\n{'='*60}")
    print(f"标题: {article['title']}")
    print(f"Slug: {article['slug']}")
    print(f"分类: {article['category']}")
    print(f"日期: {article['dateFull']}")
    print(f"字数: {len(article['content'])}字")
    print(f"关键词: {article['keywords']}")
    print(f"内链数: {article['content'].count('](https://www.aitoolbox.hk/tools/')}")
    print(f"表格数: {article['content'].count('|---')}")
    print(f"FAQ数: {article['content'].count('**Q')}")
    print(f"{'='*60}")

    # --publish 模式：插入 → 构建 → 推送
    if args.publish:
        print(f"\n🚀 开始发布流程...")
        
        # 1. 插入articles.json
        print("\n[1/3] 插入 articles.json")
        if not insert_article_to_json(article, ARTICLES_FILE):
            print("  ❌ 发布中止：插入JSON失败")
            sys.exit(1)
        
        # 2. 构建
        print("\n[2/3] 构建站点")
        if not run_build():
            print("  ❌ 发布中止：构建失败")
            sys.exit(1)
        
        # 3. git push
        print("\n[3/3] Git推送")
        git_commit_push(article)
        
        print(f"\n{'='*60}")
        print(f"🎉 发布完成！")
        print(f"   文章: {article['title']}")
        print(f"   Slug: {article['slug']}")
        print(f"   URL: https://www.aitoolbox.hk/articles/{article['slug']}/index.html")
        print(f"{'='*60}")
    else:
        print(f"\n💡 提示: 加 --publish 参数可自动发布（插入JSON+构建+推送）")


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

"""
工具内容批量生成脚本（两次调用版）
第一次API调用：生成工具基本信息（name/slug/description/pros/cons/features/faq等）
第二次API调用：专门生成content长文（确保字数和质量）

用法:
    python scripts/generate_tools.py --count 5
    python scripts/generate_tools.py --count 5 --tools "Perplexity AI,Leonardo AI,Suno"
    python scripts/generate_tools.py --count 5 --tools-file data/new_tools.json
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

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# 全部分类（即使 tools.json 中没有对应工具，API 也可为新增分类生成工具）
# 与 classification_rules.json 的 19 个顶层类目保持一致（2026-08-19 补齐 AI学习/AI检测/AI提示词/去中心化AI）
ALL_CATEGORIES = [
    "AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频",
    "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率",
    "AI智能体", "AI开发", "AI行业应用", "AI学习", "AI检测", "AI提示词", "去中心化AI",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_PATH = os.path.join(BASE_DIR, 'data', 'tools.json')
SUBMISSION_LOG_PATH = os.path.join(BASE_DIR, 'data', 'tool_submission_log.json')  # 提交记录，防重复提交

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
    "Cognition AI", "Sourcegraph Cody", "Tabnine", "Pieces",
    "ComfyUI", "Fooocus", "Topaz Photo AI", "Upscayl", "Adobe Express AI",
    "Mubert", "AIVA", "Soundraw", "Boomy", "Krotos Studio",
    "Colossyan", "Elai", "Lalamu", "InVideo AI", "Pictory", "Kapwing",
    "Rytr", "Jenni AI", "LanguageTool", "ProWritingAid",
    "Surfer SEO", "Frase", "Scalenut",
    "ChatPDF", "Humata AI", "Julius AI",
    "AdCreative AI", "Lumen5", "Predis AI",
    "文心一言", "紫东太初", "书生浦语", "面壁智能",
    "即梦AI", "万兴播爆", "通义万相", "星火认知大模型",
    # === 2026-05-05 新增 ===
    "Perplexity Comet", "Aider", "Trae", "SlidesAI", "Mureka", "Beatoven.ai",
    "HappyHorse", "Coda AI", "Semrush AI", "Resemble AI", "Monica AI",
    "Buffer AI", "Pencil AI", "DeepL Write", "Smartcat",
    "Relevance AI", "Glean", "LingoAI", "Zety AI",
    "灵办AI", "夸克AI", "腾讯文档AI",
    # === 2026-05-12 新增 ===
    "Devin AI", "Amp", "OpenHands", "Cluely",
    "Groq", "Cerebras", "OpenRouter", "Mistral AI",
    "LangChain", "LlamaIndex", "Pinecone", "Chroma", "Weaviate",
    "CodeRabbit", "Bloop", "Mem", "Recall", "Octarine",
    "Fathom", "Fireflies AI", "Notion AI Meeting",
    "IconScout AI", "StockImg AI", "Galileo AI",
    "KapKap", "Vizard", "OpusClip",
    "ElevenLabs Dubbing", "Respeecher",
    "MiniMax M2.5", "StepFun Step-2", "Baichuan 2",
    "Meticulous", "Autify", "Shulex", "Jasper Chat",
    "Hippocratic AI", "Glass Health", "Harvey AI", "Ironclad AI",
    # === 2026-05-12 第二轮 ===
    "Mindra", "Shadow AI", "PandaProbe", "Kanwas", "FlowMarket",
    "Postiz", "Huddle01 VMs", "Symphony Agent",
    "Sierra Ghostwriter", "Cloud Computer Manus", "Gemini Deep Research Agent",
    "Kilo Code", "Warp Terminal", "Superset", "Zed Editor",
    "deepclaude", "Tabstack", "Codex CLI",
    "Wonder AI", "open-design", "Mintlify Editor",
    "Hera Launch", "Velo AI", "VideoOS", "Pixelle-Video",
    "Gen-4 Runway", "Luma Dream Machine",
    "Agent Browser", "Browser Use",
    "deepsec", "Xint Code",
    "TradingAgents", "mike AI", "RankSpot", "Schole AI",
    "Jamie AI", "Alexa Plus", "Descript AI",
    "文心快码", "通义灵码", "CodeBuddy腾讯",
    "Seedance 2.0", "Anijam", "Yoroll", "清影AI",
    "海螺AI", "Vidu AI", "PixVerse AI",
    "堆友AI", "美图设计室AI", "触站AI",
    "扣子Coze", "Dify智能体", "百度千帆Agent",
    "Unitree GD01", "AGIBOT智元", "AnySceneGen", "Dexbotic",
    "WPS AI办公", "通义效率", "飞书智能伙伴",
    "秘塔AI搜索", "纳米AI", "夸克AI搜索",
    "文思AI", "火山写作", "笔灵AI",
    "魔音工坊", "讯飞智作", "ACE Studio",
    # === 2026-06-12 扩容 ===
    "OpenClaw", "CrewAI", "AG2", "LangGraph", "MetaGPT",
    "Strands Agents", "OpenAI Agents SDK", "Flowise", "Langflow",
    "Qwen-Agent", "Modelscope-Agent",
    "PearAI", "Melty", "Augment Code", "Qoder", "Cline",
    "Qwen3-Coder-Next", "OpenCode",
    "Kling 3.0", "Moonvalley", "Vidu 2.0", "Hedra", "Pollinations",
    "MusicFX", "Riffusion", "CosyVoice", "ChatTTS",
    "Spark-TTS", "GPT-SoVITS", "F5-TTS",
    "RAGFlow", "Milvus", "Qdrant", "AnythingLLM",
    "LightRAG", "GraphRAG", "Haystack", "Unstructured", "Verba",
    "Base44", "Uizard", "Visily", "Khroma", "Flair AI",
    "Wix AI", "Designs.ai", "Pixso AI",
    "触手AI", "6pen Art", "无界AI", "创客贴AI",
    "图怪兽", "易企秀", "绘蛙", "WHEE", "文心一格", "混元图像",
    "Cartesia", "Deepgram",
    "Algo", "Taskade",
    "Read AI", "Avoma", "Sembly",
    "Intercom Fin", "Ada AI", "Zendesk AI",
    "Duolingo Max", "Khanmigo", "Quizlet AI",
    "Tempus AI", "Ada Health",
    "Bloomberg GPT", "Kensho AI", "Alpaca AI",
    "CoCounsel", "Spellbook", "Robin AI",
    "Eightfold", "HireVue AI",
    "MiniCPM-o", "GLM-5.1", "百川3",
    "Lakera Guard", "PromptArmor",
    "Figure AI", "Tesla Optimus", "宇树H1",
    "FeedHive", "Shopify Magic",
    # === 2026-06-24 扩容 ===
    "Temporal", "Trigger.dev", "Pipedream", "UiPath",
    "Retool AI", "OutSystems AI", "BuildShip", "Superblocks",
    "Kestra", "Dagster",
    "AutoGen", "Smolagents", "Agno", "SuperAGI",
    "Botpress", "Voiceflow", "TaskWeaver", "AgentGPT",
    "Phidata", "Beam AI", "Lindy AI",
    "Databricks AI", "Snowflake AI", "Hex.tech", "Deepnote",
    "MindsDB", "ThoughtSpot", "Dataiku", "MotherDuck",
    "Rill Data", "Evidence.dev", "Sigma Computing",
    "Tavily AI", "Exa AI", "Perplexity Sonar",
    "Glide AI", "Bubble AI", "Softr AI", "Airtable AI",
    "Together AI", "Fireworks AI", "Anyscale",
    "Lakera", "TrojAI", "HiddenLayer",
    "Harness AI", "Kubiya AI", "Pulumi AI",
]


def call_api(prompt, max_tokens=8000, timeout=300):
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


def build_context_from_meta(meta):
    """从cron JSON的工具元数据中构建上下文块（传递给LLM作为真实信息来源）"""
    if not meta:
        return None
    parts = []
    # 基本信息
    if meta.get("name_cn"):
        parts.append(f"- 中文名: {meta['name_cn']}")
    if meta.get("description"):
        parts.append(f"- 官方/来源描述: {meta['description']}")
    if meta.get("category"):
        parts.append(f"- 分类: {meta['category']}")
    if meta.get("subcategory"):
        parts.append(f"- 子分类: {meta['subcategory']}")
    if meta.get("url"):
        parts.append(f"- 官网: {meta['url']}")
    # 来源与热度（含真实数据，LLM可以引用）
    if meta.get("source"):
        parts.append(f"- 信息来源: {meta['source']}")
    if meta.get("heat_signal"):
        parts.append(f"- 热度信号（真实数据可引用）: {meta['heat_signal']}")
    if meta.get("published_date"):
        parts.append(f"- 首发日期: {meta['published_date']}")
    # 可选：有就传，没有不传
    if meta.get("pricing"):
        parts.append(f"- 价格信息（真实数据）: {meta['pricing']}")
    if meta.get("features"):
        if isinstance(meta["features"], list):
            parts.append(f"- 核心功能: {'; '.join(meta['features'])}")
        else:
            parts.append(f"- 核心功能: {meta['features']}")
    parts.append("\n⚠️ 以上信息来自实际采集渠道，可以引用。没有提到的数据（如具体价格数字）不要编造。")
    return "\n".join(parts)


def build_info_prompt(tool_name, existing_names, categories, context=None):
    """第一次调用：生成工具基本信息。context为cron搜索阶段收集的真实数据"""
    context_block = ""
    if context:
        context_block = f"""
=== ⚠️ 以下是从权威来源收集的真实信息，必须基于此整理，不得编造 ===
{context}
=== 真实信息结束 ===
"""
    return f"""你是一个AI工具评测网站的内容编辑。请为AI工具"{tool_name}"生成基本数据。
{context_block}
返回严格JSON，不要其他文字。已有工具（不要重复）: {existing_names}
可选分类: {categories}

JSON结构：
{{
    "name": "{tool_name}",
    "slug": "英文slug小写短横线",
    "emoji": "1个代表emoji",
    "color": "品牌色十六进制",
    "description": "2-3句描述（如果上下文提供了真实描述，整理改写，不要编造）",
    "category": "从可选分类选一个最合适的",
    "tags": [
        {{"text": "标签1"}},
        {{"text": "标签2"}},
        {{"text": "标签3", "type": "free"}}
    ],
    "rating": "⭐ X.X（4.0-5.0，如果不确定填⭐ 4.5）",
    "visits": "月访问量估算（如无数据填'暂无数据'）",
    "badge": {{"type": "hot/new/recommend", "text": "HOT/NEW/推荐"}},
    "url": "官方网址（如果上下文提供了url直接用）",
    "price": "价格信息（如无可靠来源填'价格暂未公开'，不要编造具体价格）",
    "platform": "支持平台（如无数据填'Web'）",
    "pros": ["优点1（基于上下文中的真实信息）", "优点2", "优点3", "优点4", "优点5"],
    "cons": ["缺点1（真实客观）", "缺点2", "缺点3"],
    "features": ["功能1（基于真实信息）", "功能2", "功能3", "功能4", "功能5", "功能6"],
    "related": ["相关工具slug1", "相关工具slug2", "相关工具slug3"],
    "faq": [
        {{"question": "用户最关心的问题1", "answer": "基于真实信息回答"}},
        {{"question": "用户最关心的问题2", "answer": "基于真实信息回答"}},
        {{"question": "用户最关心的问题3", "answer": "基于真实信息回答"}},
        {{"question": "用户最关心的问题4", "answer": "基于真实信息回答"}}
    ],
    "seo_keywords": [
        "{tool_name}",
        "{tool_name}怎么样",
        "{tool_name}免费版",
        "{tool_name}使用教程",
        "{tool_name}和哪个好"
    ]
}}"""


def build_content_prompt(tool_name, description, pros, cons, features, context=None):
    """第二次调用：专门生成content长文"""
    context_block = ""
    if context:
        context_block = f"""
=== ⚠️ 以下是从权威来源收集的真实信息，文章中涉及事实的部分必须基于此，不得编造 ===
{context}
=== 真实信息结束 ===
"""
    return f"""你是一个AI工具站的内容编辑，写一篇关于"{tool_name}"的介绍文章。
{context_block}
工具描述：{description}
主要优点：{', '.join(pros)}
主要缺点：{', '.join(cons)}
核心功能：{', '.join(features)}

写作风格要求：
- 像一个了解AI工具的人向朋友推荐，语气自然、真实、有主见
- 可以有观点和评价，但不要过度夸赞或贬低
- 适当口语化，但不要刻意搞笑或用力过猛

⚠️ 内容红线（违反将导致文章不可用）：
- 🔴 禁止编造具体数据（如"提升32%""准确率92%"）。如果上下文提供了真实数据可以引用并注明来源，否则只描述定性感受
- 🔴 禁止编造个人经历（如"我团队""我测试了30款""我用了18个月"）。可以用"很多用户反馈""实际使用中""据了解"等泛指表述
- 🔴 禁止编造价格/套餐细节。如果上下文没有提供价格信息，写"价格暂未公开"或描述"提供免费试用/免费版"
- 🔴 禁止写"基于XX年XX月的体验"等虚构时间线

文章结构（用##标题）：
1. ## {tool_name}是什么？（通俗介绍，让没听过的人也能快速理解。如果有上下文中的真实描述，以此为基础改写）
2. ## 核心功能（5个功能，每个说清楚用途和实际感受）
3. ## 版本/套餐对比（用Markdown表格，客观列出。如果上下文没有提供价格/版本信息，宁可少写不要编造）
4. ## 值不值得用？（优点+缺点，最后给一个明确的总体结论）
5. ## 使用建议（具体可操作的建议）
6. ## 适合谁用？（分"推荐""可考虑""不推荐"三档）

写作要求：简洁有力，不凑字数。该短则短，该详细则详细。
直接输出Markdown文本，不要JSON包裹。"""


def generate_tool(tool_name, existing_names, categories, verified_keywords=None, context=None):
    """生成单个工具（两次API调用）"""
    print(f"  正在生成: {tool_name}...")

    # 第一步：生成基本信息
    print(f"    [1/2] 生成基本信息...")
    info_prompt = build_info_prompt(tool_name, existing_names, categories, context=context)
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
        tool_data.get("features", []),
        context=context,
    )
    content = None
    for attempt in range(3):
        try:
            raw = call_api(content_prompt, max_tokens=8000)
            content = raw.strip()
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
    # === 转全 Agent 流水线（2026-07-29）：本脚本只产出草稿，禁止未经核验即发布 ===
    tool_data["content_verified"] = False   # 必须经 Agent 联网核验后改为 True
    tool_data["conflict"] = False
    tool_data["verify_status"] = "pending_agent"  # 待 agent-tool-author 协议核验

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
    """标准化工具名：剥离版本号和无意义后缀，保留功能性后缀"""
    n = name.lower().strip()
    prev = None
    while n != prev:
        prev = n
        # 去掉尾部噪音词（含常见AI模型代号: sol/turbo/flash/opus等）
        n = re.sub(r'\s+(ai|ml|pro|plus|lite|beta|3d|\.com|tools|tool|app|web|online|free|premium|studio|sol|turbo|flash|opus|sonnet|haiku|mini|nano|max)\s*$', '', n)
        # 去掉尾部版本号模式: " V3", " 2.0", "-5.6", " 4o"
        n = re.sub(r'[\s\-]+(v?\d+(\.\d+)?[a-z]?)\s*$', '', n)
    n = re.sub(r'（.*?）', '', n)  # 去掉中文括号
    return n.strip()


# 版本号模式：匹配 "v3", "2.5", "5.6", "4o" 等
_VERSION_RE = re.compile(r'^v?\d+(\.\d+)?[a-z]?$')

# 无意义后缀词：附加到基础名上不构成新产品的词
NOISE_SUFFIX_WORDS = {
    "ai", "pro", "plus", "lite", "beta", "free", "premium",
    "online", "web", "app", "tool", "tools", "studio",
    "ml", "3d", ".com",
}


def _is_noise_only_diff(shorter, longer):
    """shorter是longer的子串时，检查多余部分是否全是无意义词或版本号"""
    diff = longer[len(shorter):].strip()
    if not diff:
        return True  # 完全相同
    diff_words = set(re.split(r'[\s\-]+', diff))
    for w in diff_words:
        if w in NOISE_SUFFIX_WORDS:
            continue
        if _VERSION_RE.match(w):
            continue
        return False  # 包含有意义词 → 不同产品
    return True


def is_duplicate_tool(new_name, existing_tools):
    """检查是否与已有工具重复。
    返回: (is_dup: bool, reason: str, matched_index: int or None)
    matched_index 指向 existing_tools 中匹配到的条目索引（仅在 is_dup=True 时有值）"""
    new_lower = new_name.lower().strip()
    new_norm = normalize_name(new_name)

    for idx, t in enumerate(existing_tools):
        existing_name = t["name"].lower().strip()
        existing_norm = normalize_name(t["name"])
        existing_slug = t["slug"].lower()

        # 精确匹配
        if new_lower == existing_name:
            return True, f"完全同名: {t['name']}", idx
        # 标准化后匹配（需区分无意义后缀 vs 有意义后缀）
        if new_norm and existing_norm:
            if new_norm == existing_norm:
                return True, f"标准化后匹配(版本升级): {new_name} ~ {t['name']}", idx
            # 一个包含另一个时，检查多余部分是否只是噪音词
            if existing_norm in new_norm:
                if _is_noise_only_diff(existing_norm, new_norm):
                    return True, f"标准化后匹配(版本升级): {new_name} ~ {t['name']}", idx
            elif new_norm in existing_norm:
                if _is_noise_only_diff(new_norm, existing_norm):
                    return True, f"标准化后匹配(版本升级): {new_name} ~ {t['name']}", idx
        # slug关键词包含（核心词>=3字符才匹配，避免过短误判）
        core = re.sub(r'[^a-z0-9]', '', new_norm)
        slug_core = re.sub(r'[^a-z0-9]', '', existing_slug)
        if len(core) >= 3 and core == slug_core:
            return True, f"slug匹配(版本升级): {t['slug']}", idx

    return False, None, None


def main():
    parser = argparse.ArgumentParser(description="批量生成AI工具内容")
    parser.add_argument("--count", type=str, default="5", help="生成数量，默认5个。使用 'all' 生成全部去重后候选")
    parser.add_argument("--tools-file", type=str, default="", help="从JSON文件读取工具名列表（支持[\"名1\",\"名2\"]或含name字段的对象数组）")
    parser.add_argument("--tools", type=str, default="", help="指定工具名，逗号分隔")
    parser.add_argument("--keywords", type=str, default="", help="Agent验证过的关键词，格式：工具名:核心词|长尾1,长尾2;工具名2:核心词|长尾1（分号分隔多工具）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写入文件")
    args = parser.parse_args()

    print(f"=== 工具内容批量生成器（两次调用版）===")
    print(f"模型: {MODEL}")
    print(f"生成数量: {'全部' if args.count.lower() == 'all' else args.count}")

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

    # 加载提交记录（防止跨批次重复提交同一工具）
    submission_log = []
    if os.path.exists(SUBMISSION_LOG_PATH):
        with open(SUBMISSION_LOG_PATH, 'r', encoding='utf-8') as f:
            submission_log = json.load(f)
    existing_names.extend(submission_log)
    print(f"提交记录: {len(submission_log)} 个历史提交")
    all_categories = sorted(set(
        list(t.get("category", "") for t in existing_tools if t.get("category")) +
        ALL_CATEGORIES
    ))

    print(f"已有工具: {len(existing_tools)} 个")
    print(f"已有分类: {', '.join(all_categories)}")

    skipped = []
    update_queue = []  # (new_name, existing_index, new_meta) — 版本升级待更新

    # 从文件中读取工具名和元数据
    tools_meta = {}  # tool_name -> metadata dict（用于传给LLM作为上下文）
    if args.tools_file:
        with open(args.tools_file, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        raw_names = []
        if isinstance(file_data, list):
            for item in file_data:
                if isinstance(item, str):
                    raw_names.append(item.strip())
                elif isinstance(item, dict) and item.get("name"):
                    name = item["name"].strip()
                    raw_names.append(name)
                    tools_meta[name] = item  # 保存完整元数据
        print(f"从文件加载: {len(raw_names)} 个工具 (含{len(tools_meta)}条元数据)")
        # 统一去重（区分配版本升级和真重复）
        tool_names = []
        for t in raw_names:
            if t in existing_names:
                skipped.append(f"{t} (完全同名)")
            else:
                is_dup, reason, matched_idx = is_duplicate_tool(t, existing_tools)
                if is_dup:
                    if "版本升级" in reason:
                        update_queue.append((t, matched_idx, tools_meta.get(t)))
                        print(f"  🔄 检测到版本升级: {reason}")
                    else:
                        skipped.append(f"{t} ({reason})")
                else:
                    tool_names.append(t)
    elif args.tools:
        raw_names = [t.strip() for t in args.tools.split(",") if t.strip()]
        tool_names = []
        for t in raw_names:
            if t in existing_names:
                skipped.append(f"{t} (完全同名)")
            else:
                is_dup, reason, matched_idx = is_duplicate_tool(t, existing_tools)
                if is_dup:
                    if "版本升级" in reason:
                        update_queue.append((t, matched_idx, tools_meta.get(t)))
                    else:
                        skipped.append(f"{t} ({reason})")
                else:
                    tool_names.append(t)
    else:
        # 使用增强去重过滤 DEFAULT_TOOL_NAMES
        tool_names = []
        for t in DEFAULT_TOOL_NAMES:
            if t not in existing_names:
                is_dup, reason, matched_idx = is_duplicate_tool(t, existing_tools)
                if is_dup:
                    if "版本升级" in reason:
                        update_queue.append((t, matched_idx, None))
                    else:
                        skipped.append(f"{t} ({reason})")
                else:
                    tool_names.append(t)

    if skipped:
        print(f"去重跳过 {len(skipped)} 个: {', '.join(skipped)}")

    if len(tool_names) == 0 and len(update_queue) == 0:
        print("没有可生成的新工具，也没有待更新的条目。")
        return

    generated = []
    if len(tool_names) > 0:
        if args.count.lower() != "all":
            tool_names = tool_names[:int(args.count)]
        print(f"待生成: {', '.join(tool_names)}")
        print()

        if args.dry_run:
            print("[DRY RUN] 以下工具将被生成（不实际调用API）:")
            for name in tool_names:
                print(f"  - {name}")
        else:
            # 逐个生成
            for i, name in enumerate(tool_names, 1):
                print(f"[{i}/{len(tool_names)}]", end="")
                # 从元数据构建上下文
                meta = tools_meta.get(name)
                context = build_context_from_meta(meta)
                if context:
                    print(f" [含真实元数据]", end="")
                tool_data = generate_tool(name, existing_names, all_categories,
                                          verified_keywords=keywords_map.get(name),
                                          context=context)
                if tool_data:
                    # 二次去重校验：生成后再次检查（API可能返回不同名字但同一工具）
                    is_dup, reason, _ = is_duplicate_tool(tool_data["name"], existing_tools + generated)
                    if is_dup:
                        print(f"  ⚠️ 生成后检测重复 ({reason})，跳过: {tool_data['name']}")
                        time.sleep(1)
                        continue

                    # 校验slug必须是小写英文+数字+短横线，禁止中文
                    slug = tool_data.get("slug", "")
                    if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', slug) or len(slug) < 2:
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
                    # 采集端已分类的子类，直接注入（不依赖LLM）
                    if meta and meta.get('subcategory'):
                        tool_data['subcategory'] = meta['subcategory']
                    existing_names.append(tool_data["name"])
                    existing_slugs.append(tool_data["slug"])
                    # 逐个保存，防止中途超时丢失数据
                    existing_tools.append(tool_data)
                    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
                        json.dump(existing_tools, f, ensure_ascii=False, indent=4)
                    print(f"    💾 已保存到 tools.json (累计 {len(existing_tools)} 个)")
                time.sleep(1)

    # === 处理版本升级：更新已有条目 ===
    updated_count = 0
    if update_queue:
        from datetime import datetime
        print(f"\n=== 版本升级更新 ({len(update_queue)} 条) ===")
        for new_name, matched_idx, new_meta in update_queue:
            old_tool = existing_tools[matched_idx]
            old_name = old_tool["name"]
            print(f"  🔄 {old_name} → {new_name}")

            if args.dry_run:
                print(f"    [DRY RUN] 以上将被更新")
                updated_count += 1  # 计数以便展示
                continue

            # === 版本方向校验（治本：防止"降级覆盖"把新版写成旧版）===
            def _extract_ver(name):
                m = re.search(r'(\d+)(?:[.\-](\d+))?', name or '')
                if not m:
                    return None
                return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)

            new_ver = _extract_ver(new_name)
            old_ver = _extract_ver(old_name)
            # 候选版本必须高于已有版本，否则是降级/误判，跳过以防覆盖成旧版内容
            if new_ver and old_ver and new_ver <= old_ver:
                print(f"    ⏭️ 跳过降级覆盖: 候选 {new_name}({new_ver}) 不高于已有 {old_name}({old_ver})，不写旧版内容")
                continue

            # 收集同品牌所有已知版本（用于"版本演进对比"小节）
            brand_norm = normalize_name(new_name)
            brand_versions = []
            for t in existing_tools:
                if normalize_name(t.get("name", "")) == brand_norm and t.get("name"):
                    brand_versions.append(t["name"])
            if new_name not in brand_versions:
                brand_versions.append(new_name)
            brand_versions = sorted(set(brand_versions), key=lambda n: _extract_ver(n) or (0, 0))

            # 构建更新上下文（旧版本信息 + 版本升级指令 + 新采集数据）
            update_ctx_lines = [f"旧版本名称: {old_name}"]
            if old_tool.get("description"):
                update_ctx_lines.append(f"旧版本描述: {old_tool['description']}")
            if old_tool.get("price"):
                update_ctx_lines.append(f"旧版本价格: {old_tool['price']}")
            update_ctx_lines.append(
                f"\n=== ⚠️ 版本升级指令 ===\n"
                f"这是一次版本升级：将「{old_name}」升级为「{new_name}」。\n"
                f"严格要求：\n"
                f"1. 全篇必须以【{new_name}】为准撰写，name 字段必须=「{new_name}」，正文所有事实都是 {new_name} 的能力，禁止把整篇写成旧版本 {old_name}。\n"
                f"2. 必须在 content 末尾新增「## 版本演进对比」小节，用表格列出同品牌已知版本（{'、'.join(brand_versions)}），并明确写出 {new_name} 相比 {old_name} 升级/新增了哪些能力。\n"
                f"3. 若缺乏 {new_name} 的真实升级点，可基于 {old_name} 合理推断差异并标注，但绝不可照抄 {old_name} 旧介绍。"
            )
            new_ctx = build_context_from_meta(new_meta)
            if new_ctx:
                update_ctx_lines.append(f"\n=== 新版本采集信息（本次从来源获取的真实数据）===")
                update_ctx_lines.append(new_ctx)
            full_ctx = "\n".join(update_ctx_lines)

            # 用新名字 + 完整上下文重新生成
            tool_data = generate_tool(new_name, existing_names, all_categories,
                                      context=full_ctx)
            if tool_data:
                # 强制以新版本名为准，杜绝 name 被写成旧版
                tool_data["name"] = new_name
                # 版本一致性校验（止血）：content 主版本须与 new_name 一致，否则不覆盖（避免名新内容旧）
                content_ver = _extract_ver(tool_data.get("content", ""))
                if new_ver and content_ver and content_ver != new_ver:
                    print(f"    ⚠️ 版本不一致，跳过覆盖: 期望 {new_ver}, 实际 {content_ver} — 保留原条目，待人工/agent 核实")
                    continue
                # 保留原有的关键字段
                tool_data["slug"] = old_tool["slug"]  # 保持URL不变
                tool_data["published"] = False  # 标为待重新发布
                # === 转全 Agent 流水线：版本升级产物同样须经 Agent 核验 ===
                tool_data["content_verified"] = False
                tool_data["conflict"] = False
                tool_data["verify_status"] = "pending_agent"
                tool_data["created_date"] = old_tool.get("created_date", "")
                tool_data["data_quality"] = old_tool.get("data_quality", {})
                tool_data["data_quality"]["last_content_updated"] = datetime.now().strftime("%Y-%m-%d")
                # 替换旧条目
                existing_tools[matched_idx] = tool_data
                with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
                    json.dump(existing_tools, f, ensure_ascii=False, indent=4)
                updated_count += 1
                print(f"    ✅ 已更新 (slug保持: {tool_data['slug']}, 待重新发布)")
            time.sleep(1)

    if not generated and updated_count == 0:
        print("\n没有成功生成或更新任何工具。")
        return

    total = len(existing_tools)
    total_unpublished = sum(1 for t in existing_tools if not t.get("published", False))
    print(f"\n✅ 完成！成功生成 {len(generated)} 个工具, 更新 {updated_count} 个版本")
    print(f"   总计: {total} 个工具, 未发布: {total_unpublished} 个")
    print(f"   预计还可发布: {total_unpublished // 3} 天")

    # === 转全 Agent 流水线：草稿必须过 Agent 核验门 ===
    print("⚠️ 重要：本脚本仅生成【草稿】，所有新工具 content_verified=False。")
    print("   须经 agent-tool-author 协议联网核验、写回 content_verified=True 后，")
    print("   发布闸门(publish_new_tools.py)才会放行。切勿跳过核验直接发布！")

    # 追加提交记录（防止下次重复提交同一批工具）
    new_submissions = [n for n in tool_names if n not in submission_log]
    if new_submissions:
        submission_log.extend(new_submissions)
        with open(SUBMISSION_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(submission_log, f, ensure_ascii=False, indent=2)
        print(f"   📝 提交记录已更新 (+{len(new_submissions)})")


if __name__ == "__main__":
    main()

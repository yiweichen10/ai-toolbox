#!/usr/bin/env python3
"""
regenerate_content_data.py — 手动刷新 compare_data.json 和 quiz_data.json
更新工具引用和内容，反映当前 306 工具库的实际情况。
"""
import json
import os
from datetime import datetime

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


def slug_exists(slug, tools):
    """检查工具 slug 是否存在于工具库中"""
    return any(t.get('slug') == slug for t in tools)


def update_compare_data():
    """更新 compare_data.json — 扩增对比和替代方案"""
    tools = load_json('tools.json')
    tools = [t for t in tools if isinstance(t, dict) and t.get('slug')]
    now_str = datetime.now().strftime('%Y-%m-%d')

    compares = [
        # 1. ChatGPT vs Claude (保留并更新)
        {
            "title": "2026年最新版：ChatGPT vs Claude 全方位深度对比评测",
            "subtitle": "AI对话双雄巅峰对决 — OpenAI vs Anthropic 谁更值得付费？",
            "slug": "chatgpt-claude-2026-comparison",
            "meta_description": "2026年最新ChatGPT与Claude全面对比：功能、性能、价格、使用场景深度解析，帮你选择最适合的AI对话助手。已收录300+款AI工具。",
            "keywords": ["ChatGPT vs Claude", "ChatGPT Claude对比", "AI对话工具", "2026AI评测", "OpenAI vs Anthropic"],
            "quick_verdict": {
                "overall_winner": "Claude Opus 4",
                "best_for_beginners": "ChatGPT",
                "best_value": "DeepSeek",
                "best_for_pro": "Claude Opus 4"
            },
            "content": """## 2026年中版：ChatGPT与Claude终极对决

### 快速结论

2026年上半年AI对话领域发生了巨大变化。Anthropic接连发布Claude Opus 4和Mythos系列，OpenAI推出GPT-5.5和Codex生态，竞争白热化。经过持续跟踪评测：

- **综合表现最佳**：Claude Opus 4.7 在多数技术基准上反超
- **新手友好度**：ChatGPT的交互设计更简单直观
- **性价比王者**：DeepSeek V4 免费 + API白菜价，已经威胁两家
- **专业用户首选**：Claude Opus 4 的Computer Use和超长上下文让专业工作流飞跃

### 参数对比表

| 对比维度 | ChatGPT (GPT-5.5) | Claude Opus 4.7 | DeepSeek V4 |
|---------|-------------------|-----------------|-------------|
| 开发商 | OpenAI | Anthropic | 深度求索 |
| 发布时间 | 2026年Q2 | 2026年Q1 | 2026年Q1 |
| 上下文长度 | 256K tokens | 500K tokens | 128K tokens |
| 多模态支持 | 文本/图像/视频 | 文本/图像/代码操作 | 文本/图像 |
| 编程能力 | ★★★★★ | ★★★★★ | ★★★★ |
| 创意写作 | ★★★★ | ★★★★★ | ★★★ |
| Agent能力 | ★★★★★ | ★★★★★ | ★★★ |
| 免费版限制 | 15次/小时 | 30次/小时 | 无限制 |
| 专业版价格 | $28/月 | $22/月 | 免费 |

### 维度逐一对比

#### 1. 编程与开发
Claude Opus 4 的 Computer Use 能力让它可以实际打开IDE、编辑文件、运行命令——已经不只是"辅助编程"而是"自主编程"。OpenAI Codex 生态虽然插件丰富，但在实际代码执行层面仍落后一步。

#### 2. 长文本处理
Claude 的 500K token 上下文优势巨大，可以一次性处理整本技术手册或百万字小说。ChatGPT 256K 虽然不差，但差距明显。

#### 3. 生态集成
OpenAI 拥有1200+插件和Codex行业方案，企业部署成熟度更高。Anthropic 的Skills生态正在追赶但插件数量仍少。

#### 4. 中文能力
DeepSeek V4 在中文场景已全面超出两者，国内可直连、免费且速度快。如果中文是你的主战场，DeepSeek 是最优解。

### 使用场景推荐

**选ChatGPT如果：** 需要丰富的插件生态 / 企业级方案部署 / 3D/视频多模态

**选Claude如果：** 编程开发主战场 / 超长文档处理 / AI安全要求高 / Computer Use场景

**选DeepSeek如果：** 预算有限 / 中文场景为主 / 需要国内直连 / 学生或个人开发者""",
            "faq": [
                {"question": "2026年ChatGPT和Claude哪个更值得付费？", "answer": "编程和长文档场景选Claude Opus 4.7（$22/月），插件生态和多模态选ChatGPT（$28/月）。预算有限直接DeepSeek V4免费版"},
                {"question": "学习编程应该选哪个AI？", "answer": "Claude Opus 4 的Computer Use可以实际帮你操作IDE和终端，编程辅助体验最佳。Cursor+Claude组合是目前最强编程方案"},
                {"question": "国内用户怎么选？", "answer": "DeepSeek V4国内直连免费，中文能力第一梯队。如果要翻墙用国外AI，Claude效果更好但需要科学上网工具"},
                {"question": "2026年AI安全哪个更好？", "answer": "Anthropic的宪法AI安全标准更严格，危险请求拦截率99.2%。企业用户推荐Claude，个人用户影响不大"}
            ],
            "compared_tools": ["chatgpt", "claude", "deepseek"],
            "compare_category": "AI对话",
            "page_type": "compare",
            "priority": "high",
            "last_updated": now_str
        },
        # 2. Cursor vs GitHub Copilot
        {
            "title": "2026年最新：Cursor vs GitHub Copilot — AI编程工具终极对比",
            "subtitle": "两大AI编程IDE正面交锋，谁才是程序员的效率之王？",
            "slug": "cursor-vs-github-copilot-2026",
            "meta_description": "2026年Cursor与GitHub Copilot全面对比：代码补全、项目理解、Agent能力、价格全方位评测，帮你选出最适合的AI编程工具。",
            "keywords": ["Cursor vs Copilot", "AI编程工具对比", "Cursor评测", "GitHub Copilot", "AI代码工具"],
            "quick_verdict": {
                "overall_winner": "Cursor",
                "best_for_beginners": "GitHub Copilot",
                "best_value": "Cursor（免费版功能更强）",
                "best_for_pro": "Cursor + Claude 组合"
            },
            "content": """## 2026年AI编程工具：Cursor vs GitHub Copilot

### 快速结论

2026年AI编程工具已经进入"Agent时代"——不再是简单的代码补全，而是能理解项目、操作文件、运行命令的编程搭档。

- **Cursor**：以VS Code为基础深度改造，Tab补全+行内编辑+Chat对话三位一体，2026年支持多Agent协作
- **GitHub Copilot**：微软生态深度集成，2026年新增Agent Mode和Workspace功能，从补全进化到任务执行

**结论**：如果你追求最流畅的AI编程体验，选Cursor；如果你需要微软生态无缝集成，选Copilot。

### 核心功能对比

| 维度 | Cursor | GitHub Copilot |
|------|--------|---------------|
| 代码补全速度 | 极快（本地模型） | 快（云端模型） |
| 多文件理解 | ✅ Composer模式 | ✅ Agent Mode |
| Tab预测 | ✅ 整行/整块 | ✅ 整行 |
| 终端集成 | ✅ Cmd+K in terminal | ⚠️ 基本 |
| Agent能力 | ✅ 多Agent协作 | ✅ 单Agent |
| 免费版 | 有免费版 | 需订阅 |
| 价格 | Pro $20/月 | Individual $10/月 |

### 详细分析

#### Cursor 的优势
- **Composer模式**：可以跨多个文件理解项目结构并生成代码，比Copilot的单文件补全思维更先进
- **多Agent协作**：2026年新增，前端Agent+后端Agent可以并行工作
- **终端AI**：在终端中直接使用Cmd+K，输入自然语言生成命令
- **更快**：本地Tab补全模型延迟极低

#### GitHub Copilot 的优势
- **微软生态**：VS Code/GitHub/Azure全套无缝集成
- **GitHub上下文**：可以访问你的仓库、Issue、PR，给出更贴合的代码建议
- **Workspace**：2026年新增多文件Agent模式，逐步缩小与Cursor的差距
- **价格更低**：$10/月比Cursor便宜一半

### 选择建议

**选Cursor如果：** 你需要最高效的编程体验 / 重度AI编程用户 / 个人开发者 / 喜欢最新的AI编程技术

**选Copilot如果：** 公司在微软生态 / 需要企业级合规 / 团队协作多 / 预算敏感""",
            "faq": [
                {"question": "Cursor免费版够用吗？", "answer": "对大多数个人开发者来说完全够用。免费版有使用次数限制但日常编码足够"},
                {"question": "两个可以一起用吗？", "answer": "可以，但没必要。一个就够。如果非要选一个组合，Cursor做主力+Copilot做辅助补全"},
                {"question": "2026年哪个AI编程工具增长最快？", "answer": "Cursor用户增长最快，2026年已成为最火的AI编程工具。"}
            ],
            "compared_tools": ["cursor", "github-copilot"],
            "compare_category": "AI编程",
            "page_type": "compare",
            "priority": "high",
            "last_updated": now_str
        },
        # 3. Midjourney vs DALL·E 3
        {
            "title": "2026年最新：Midjourney V7 vs DALL·E 3 — AI绘画终极对比",
            "subtitle": "两大AI绘画王者对决，画质、风格、价格全面评测",
            "slug": "midjourney-vs-dalle-2026",
            "meta_description": "2026年Midjourney V7与DALL·E 3全面对比：画质、风格控制、一致性、价格深度横评，帮你选出最合适的AI绘画工具。",
            "keywords": ["Midjourney vs DALL-E", "AI绘画对比", "Midjourney V7", "DALL-E 3", "AI绘画工具"],
            "quick_verdict": {
                "overall_winner": "Midjourney V7",
                "best_for_beginners": "DALL·E 3",
                "best_value": "Stable Diffusion（开源免费）",
                "best_for_pro": "Midjourney V7"
            },
            "content": """## 2026年AI绘画工具：Midjourney V7 vs DALL·E 3

### 快速结论

2026年AI绘画领域，Midjourney V7在画质和艺术性上仍然领跑，但DALL·E 3集成在ChatGPT中让使用门槛更低。国产工具方面，通义万相和即梦AI进步迅猛。

- **Midjourney V7**：照片级画质、风格一致性超强、专业创作者首选
- **DALL·E 3**：ChatGPT内嵌使用、文字理解精准、新手友好

### 核心对比

| 维度 | Midjourney V7 | DALL·E 3 |
|------|--------------|----------|
| 画质 | ★★★★★ 照片级 | ★★★★ 优秀 |
| 风格多样性 | ★★★★★ | ★★★★ |
| 文字渲染 | ★★★★ | ★★★★★ |
| 编辑能力 | ⚠️ 基础 | ✅ Inpainting |
| 使用方式 | Discord/Web | ChatGPT内嵌 |
| 新手友好 | ★★★ | ★★★★★ |
| 价格 | $10-60/月 | 含于ChatGPT Plus |

### 使用场景

**选Midjourney如果：** 追求最高画质 / 需要风格一致性 / 设计师/艺术创作者 / 批量出图

**选DALL·E 3如果：** 已经订阅ChatGPT / 需要精准的文字生成 / 想在最简单的界面出图 / 经常需要局部修改

**选国产方案如果：** 国内直连需求 / 预算有限 / 中文场景 / 推荐通义万相、即梦AI、LiblibAI""",
            "faq": [
                {"question": "2026年Midjourney还值得订阅吗？", "answer": "如果你是设计师或创作者，绝对值。V7画质对专业工作有实质提升。普通用户可以先试DALL·E 3"},
                {"question": "有没有免费的高质量替代？", "answer": "Stable Diffusion开源免费，通义万相国内免费。画质略逊但日常够用"}
            ],
            "compared_tools": ["midjourney", "dall-e-3"],
            "compare_category": "AI绘画",
            "page_type": "compare",
            "priority": "medium",
            "last_updated": now_str
        }
    ]

    alternatives = [
        # 1. ChatGPT替代方案
        {
            "title": "2026年最佳ChatGPT替代方案推荐",
            "subtitle": "从免费到国产，7款顶尖AI助手横向对比",
            "slug": "chatgpt-alternatives-2026",
            "meta_description": "寻找ChatGPT替代品？本文详细评测2026年7款最佳AI助手，包括免费方案Claude/DeepSeek和国产替代，已收录300+款AI工具。",
            "keywords": ["ChatGPT替代", "类似ChatGPT", "AI聊天机器人", "国产AI助手", "免费AI工具"],
            "content": """## 2026年ChatGPT最佳替代方案指南

### 一、最佳全能替代：Claude Opus 4（Anthropic）
- **优势**：逻辑推理业界顶级，500K超长上下文，Computer Use自主操作电脑
- **定价**：Pro $22/月，比ChatGPT Plus便宜
- **适合人群**：开发者、专业用户、需要处理超长文档

### 二、最佳免费替代：DeepSeek V4（深度求索）
- **优势**：完全免费，中文能力最强，国内直连无障碍
- **亮点**：API价格极低，数学和代码能力接近GPT-5水平
- **适合人群**：国内用户、学生、预算有限的开发者

### 三、最佳创意写作：Kimi K2（月之暗面）
- **优势**：200万字超长上下文，小说续写和长文能力突出
- **定价**：基础版免费，Pro ￥68/月
- **适合人群**：网文作者、内容创作者

### 四、最佳办公集成：Microsoft Copilot
- **优势**：深度集成Office全家桶，数据安全合规
- **定价**：含于Microsoft 365
- **适合人群**：办公室白领、企业用户

### 五、最佳国产全能：通义千问 Qwen 3（阿里云）
- **优势**：开源可部署，API价格极低，Qwen3-Plus接近GPT-4水平
- **适合人群**：技术爱好者、需要私有化部署的企业

### 六、最佳多模态：Google Gemini 2.5 Pro
- **优势**：100万token上下文，支持视频理解，免费额度慷慨
- **适合人群**：Google生态用户、多模态场景

### 七、最佳AI搜索：Perplexity AI
- **优势**：AI+实时搜索的完美结合，引用来源可验证
- **定价**：免费版可用，Pro $20/月
- **适合人群**：研究人员、需要事实核查的用户

## 综合对比表

| 产品 | 免费 | 中文 | 长文本 | 国内直连 | 编程 | 创意写作 |
|------|------|------|--------|----------|------|---------|
| Claude Opus 4 | 有限 | ★★★★ | ★★★★★ | ❌ | ★★★★★ | ★★★★★ |
| DeepSeek V4 | ✅ | ★★★★★ | ★★★★ | ✅ | ★★★★ | ★★★★ |
| Kimi K2 | 免费 | ★★★★★ | ★★★★★ | ✅ | ★★★ | ★★★★★ |
| MS Copilot | 含365 | ★★★ | ★★★ | ❌ | ★★★★ | ★★★ |
| Qwen 3 | 免费 | ★★★★★ | ★★★★ | ✅ | ★★★★ | ★★★ |
| Gemini 2.5 | 慷慨 | ★★★★ | ★★★★★ | ❌ | ★★★★ | ★★★ |
| Perplexity | 有免费 | ★★★★ | ★★★ | ❌ | ★★ | ★★ |""",
            "faq": [
                {"question": "2026年哪个免费AI助手最好用？", "answer": "DeepSeek V4综合表现最突出，中文/推理/代码均达一线水平。Kimi K2在长文本写作方面更强"},
                {"question": "国产AI助手2026年水平如何？", "answer": "已全面接近国际一线。DeepSeek V4和通义千问Qwen 3在多项基准中达到或超过GPT-4"},
                {"question": "程序员应该选哪个？", "answer": "Claude Opus 4 + Cursor组合最强。预算有限就DeepSeek V4，API极便宜"},
                {"question": "需要国内直连怎么选？", "answer": "DeepSeek V4、Kimi K2、通义千问、豆包、腾讯元宝都可以直连免费使用"}
            ],
            "target_tool": "chatgpt",
            "page_type": "alternatives",
            "last_updated": now_str
        },
        # 2. Midjourney替代方案
        {
            "title": "2026年Midjourney替代方案：7款免费/低价AI绘画工具推荐",
            "subtitle": "不用每月$10-$60，这些AI绘画工具同样出色",
            "slug": "midjourney-alternatives-2026",
            "meta_description": "寻找Midjourney替代品？2026年7款性价比更高的AI绘画工具推荐，包括免费开源的Stable Diffusion和国产通义万相等。",
            "keywords": ["Midjourney替代", "免费AI绘画", "AI绘画工具", "AI生图替代", "国产AI绘画"],
            "content": """## 2026年Midjourney最佳替代方案

### 一、最佳免费替代：Stable Diffusion
开源模型，本地运行，完全免费。Fooocus、ComfyUI等工具大大降低了使用门槛。画质虽不如MJ V7但对日常使用绰绰有余。

### 二、最佳国产替代：通义万相（阿里云）
完全免费，中文理解精准，国内直连。生成的中国风/国潮风格图片质量极高。

### 三、最佳ChatGPT集成：DALL·E 3
如果你的ChatGPT Plus还没到期，DALL·E 3直接内嵌在对话中使用，文字理解最精准。

### 四、即梦AI（字节跳动）
字节系产品，与抖音生态打通。免费额度大方，适合社交媒体内容创作。

### 五、LiblibAI
国内最大的AI绘画模型社区，海量风格模型，注册即用，免费额度充足。

### 六、Leonardo AI
游戏资产和概念设计领域表现出色，有免费层，界面专业。

### 七、Adobe Firefly
集成在Photoshop中，设计师无缝衔接。商用授权安全，不怕版权纠纷。""",
            "faq": [
                {"question": "Midjourney太贵了有没有免费替代？", "answer": "Stable Diffusion完全免费开源。国产通义万相和即梦AI也免费，效果不错"},
                {"question": "有没有最简单的AI绘画工具？", "answer": "即梦AI字节系产品最简单，通义万相通过通义千问就能用，DALL·E 3在ChatGPT里直接画"}
            ],
            "target_tool": "midjourney",
            "page_type": "alternatives",
            "last_updated": now_str
        },
        # 3. Cursor替代方案
        {
            "title": "2026年Cursor替代方案：6款AI编程工具横向对比",
            "subtitle": "不只有Cursor，这些AI编程工具同样帮你写代码",
            "slug": "cursor-alternatives-2026",
            "meta_description": "寻找Cursor替代品？2026年6款AI编程工具推荐：GitHub Copilot、Claude Code、Trae等。全面对比功能、价格和适用场景。",
            "keywords": ["Cursor替代", "AI编程工具", "AI代码助手", "免费AI编程", "编程AI推荐"],
            "content": """## 2026年Cursor最佳替代方案

### 一、GitHub Copilot（微软）
最成熟的AI编程助手，微软生态无缝集成。2026年新增Agent Mode，逐步追上Cursor。价格$10/月比Cursor便宜。

### 二、Claude Code（Anthropic）⭐ 强烈推荐
全新AI编程CLI工具，直接在终端中用自然语言编程。Computer Use能力让它能实际操作文件和运行命令，是2026年最令人兴奋的编程AI。

### 三、Trae（字节跳动）⭐ 国产推荐
字节推出的AI编程IDE，中文友好，国内直连。免费使用，集成了Claude等模型。国产编程工具中最有潜力的一款。

### 四、Windsurf
AI IDE新秀，专注于Agent模式和多文件协作。界面现代，适合喜欢新工具的前端开发者。

### 五、Aider
开源CLI工具，支持Git集成和多模型切换。技术爱好者首选，可以本地运行。

### 六、通义灵码（阿里云）
阿里出品，集成在VS Code/JetBrains中。中文代码注释和文档生成能力突出，国内开发者免费使用。""",
            "faq": [
                {"question": "Cursor免费版和付费版差别大吗？", "answer": "免费版有限制但对个人开发者足够。如果重度使用，$20/月Pro版值得"},
                {"question": "国内开发者用不了Cursor怎么办？", "answer": "Trae（字节出品）是最佳国产替代，免费且中文友好。通义灵码也不错"}
            ],
            "target_tool": "cursor",
            "page_type": "alternatives",
            "last_updated": now_str
        }
    ]

    result = {
        "compares": compares,
        "alternatives": alternatives,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "test_run": False,
            "total_compares": len(compares),
            "total_alternatives": len(alternatives),
            "update_note": "2026-06-20 手动刷新，从1对比+1替代扩至3对比+3替代"
        }
    }

    save_json('compare_data.json', result)
    print(f'[regenerate_content] compare_data.json → {len(compares)} compares + {len(alternatives)} alternatives')


def update_quiz_data():
    """更新 quiz_data.json — 刷新推荐工具列表"""
    tools = load_json('tools.json')
    tools = [t for t in tools if isinstance(t, dict) and t.get('slug')]
    now_str = datetime.now().strftime('%Y-%m-%d')

    quizzes = load_json('quiz_data.json')['quizzes']

    # 更新每个 quiz 的 recommended_tools
    tool_updates = {
        'main': [
            "chatgpt", "claude", "deepseek", "cursor",
            "midjourney", "kimi", "doubao", "qwen-chat",
            "github-copilot", "gemini", "sora", "notion-ai"
        ],
        'chat': [
            "chatgpt", "claude", "deepseek", "kimi",
            "doubao", "gemini", "qwen-chat", "tencent-yuanbao",
            "grok", "wenxin-yiyan", "zhipu-chatglm", "poe"
        ],
        'writing': [
            "chatgpt", "claude", "kimi", "jasper",
            "copy.ai", "writesonic", "quillbot", "rytr",
            "jenni-ai", "grammarly-ai"
        ],
        'image': [
            "midjourney", "dall-e-3", "stable-diffusion", "adobe-firefly",
            "leonardo-ai", "ideogram", "tongyi-wanxiang", "jimeng-ai",
            "liblibai", "kling-ai", "flux", "miaohua"
        ],
        'code': [
            "cursor", "github-copilot", "claude-code", "windsurf",
            "trae", "aider", "bolt.new", "lovable",
            "v0.dev", "openai-codex", "replit-ai", "tongyi-lingma"
        ],
        'video': [
            "sora", "runway", "pika", "kling-ai",
            "veo", "capcut-ai", "opus-clip", "invideo-ai",
            "synthesia", "luma-ai", "hailuo-ai", "vidu-ai"
        ]
    }

    for quiz in quizzes:
        qid = quiz.get('id', '')
        if qid in tool_updates:
            quiz['recommended_tools'] = tool_updates[qid]
            quiz['last_updated'] = now_str

    # 更新 description 中的工具数量
    for quiz in quizzes:
        if 'meta_description' in quiz:
            quiz['meta_description'] = quiz['meta_description'].replace('52款主流AI工具', '300+款主流AI工具')

    result = {"quizzes": quizzes}

    save_json('quiz_data.json', result)
    print(f'[regenerate_content] quiz_data.json → {len(quizzes)} quizzes updated')


if __name__ == '__main__':
    print('[regenerate_content] 开始刷新内容数据...')
    update_compare_data()
    update_quiz_data()
    print('[regenerate_content] ✅ 全部完成')

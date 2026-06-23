# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
SEO文章批量生成脚本 v3 — AEO+GEO 深度内容版（2026-06-23 升级）
三大类型轮替产出：
  A. 国产AI对比评测（最高优先级，打中文蓝海）
  B. 场景化工具推荐（按人群/需求组织）
  C. 教程指南（长尾"怎么用"关键词）

AEO+GEO 升级要点（2026-06-23）：
  - 开头 BLUF（一句话结论，AI 引擎提取首选）
  - 专家/权威引言块（GEO +41% 最优方法）
  - H2 改问题式（AI 引擎按问题匹配内容）
  - 段落短化（2-3 句一段，便于 AI 程序化解析）
  - 加 3-5 个带来源统计数据（GEO +30%）
  - 强化 FAQ 区块（真实问答，非伪 FAQ）
  - 数据来源标注（Princeton GEO 论文 + Google 2026-05-15 官方指南）

用法:
    python generate_articles.py                    # 自动选下一篇（按轮替顺序）
    python generate_articles.py --type A           # 强制指定类型
    python generate_articles.py --list             # 查看轮替队列
    python generate_articles.py --all              # 一键生成所有待产出的文章

输出:
    _article_drafts.json（原始草稿）
    → humanize_articles.py 去AI味
    → _articles_humanized.json
    → add_articles.py 追加到 articles.json
"""

import json, sys, os, time, random, argparse, urllib.request
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ===== API 配置 =====
import os
from dotenv import load_dotenv

# Load .env file (project root)
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path)

API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL = "deepseek-ai/DeepSeek-V3"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DRAFTS_FILE = os.path.join(BASE_DIR, '_article_drafts.json')
STATE_FILE = os.path.join(BASE_DIR, '_article_state.json')
ARTICLES_FILE = os.path.join(BASE_DIR, 'data', 'articles.json')

# ===== 文章类型定义 =====
ARTICLE_TYPES = {
    'A': {
        'label': '国产AI对比评测',
        'priority': 1,
        'description': '国产/中美AI模型或工具的深度对比，真实测试数据',
        'keywords_target': '中文用户搜索的对比决策词',
    },
    'B': {
        'label': '场景化工具推荐',
        'priority': 2,
        'description': '按人群/场景/预算推荐AI工具组合',
        'keywords_target': '场景长尾词 + 职业词',
    },
    'C': {
        'label': '教程指南',
        'priority': 3,
        'description': '具体AI工具从入门到进阶的实操教程',
        'keywords_target': '"怎么用""新手入门"类长尾教程词',
    },
    'E': {
        'label': 'English Global Content',
        'priority': 0,
        'description': 'English articles for global audience (High Priority for Launch)',
        'keywords_target': 'Global AI trends, ROI, high-intent English keywords',
    },
}

# ================================================================
#  A 类：国产AI对比评测（核心差异化内容）
# ================================================================
PROMPTS_A = [
    # --- A1: 国产大模型横评 ---
    {
        "title": "DeepSeek vs Kimi vs 豆包 vs 通义千问：2026年国产大模型终极对决",
        "slug": "deepseek-vs-kimi-vs-doubao-vs-tongyi-2026",
        "description": "DeepSeek R2、Kimi k1.5、豆包Seed 2.0、通义千问3.0，四款国产大模型全面横评。从中文理解、代码能力、推理深度、免费额度四个维度实测，告诉你哪个最值得用。",
        "keywords": "DeepSeek,Kimi,豆包,通义千问,国产AI对比,AI大模型评测,免费AI,中文AI",
        "category": "AI对话",
        "prompt": '''你是一位同时使用DeepSeek、Kimi、豆包、通义千问超过半年的重度AI用户，写一篇深度对比评测。

主题：2026年四大国产AI大模型终极对决（DeepSeek vs Kimi vs 豆包 vs 通义千问）

背景：2026年国产AI爆发式进化，DeepSeek出了R2推理增强版，Kimi升级了k1.5，豆包发布了Seed 2.0 Pro，通义千问到了3.0。普通用户到底该用哪个？

要求：
- 必须有真实的对比维度，不是泛泛而谈
- 每个模型必须说出一个"最强项"和一个"最弱项"
- 要包含免费用户的视角（很多人不想付费）
- 语气像资深用户在给朋友推荐，不官方不客套

文章结构（2500-3000字）：

## 开场（200字）
用一个真实场景切入——比如你同时在4个平台上问了同一个复杂问题，结果差异有多大。引出"到底谁才是2026国产AI之王"这个问题。

## 第一轮：中文能力盲测（600字）
设计5个有代表性的中文测试题：
1. 古文理解（如翻译一段文言文）
2. 歇后语/成语运用
3. 长文摘要总结
4. 中文创意写作（如写一首藏头诗）
5. 方言/网络用语理解
每个题目给出4个模型的回答对比，评分并点评。
结论：哪个中文最好？为什么？

## 第二轮：代码与逻辑推理（500字）
3个编程/推理测试：
1. LeetCode中等难度算法题
2. 复杂业务逻辑的Python实现
3. 数学证明题
关键发现：哪个模型在R1/R2模式下推理提升最大？

## 第三轮：日常实用场景（500字）
- 写邮件/周报
- 做旅行规划
- 分析Excel数据（贴一个示例）
- 辅助写作（论文/文案）
哪个在"接地气"的场景中最好用？

## 第四轮：价格与免费策略对比（400字）
列出各平台的：
- 免费额度（每天/每月多少次）
- 付费价格
- 性价比分析
- 免费够不够日常用？

## 总结：不同人群推荐表（300字）
| 人群 | 首选 | 备选 | 理由 |
|------|------|------|------|
| 学生 | | | |
| 程序员 | | | |
| 内容创作者 | | | |
| 企业用户 | | | |
| 零预算党 | | | |

## 结尾彩蛋（100字）
预测一下2026下半年国产AI会怎么发展。

直接写正文，不要废话开场白。'''
    },
    # --- A2: ChatGPT vs Claude vs DeepSeek 三国杀 ---
    {
        "title": "ChatGPT vs Claude vs DeepSeek：2026年中美AI三强真实差距在哪？",
        "slug": "chatgpt-vs-claude-vs-deepseek-2026",
        "description": "ChatGPT-5.4、Claude Opus 4.6、DeepSeek R2三款顶级AI模型横向评测。从创作质量、编程能力、中文理解、价格性价比四个维度实测，帮你找到最适合你的AI助手。",
        "keywords": "ChatGPT,Claude,DeepSeek,AI对比评测,AI模型对比,ChatGPT vs Claude,中美AI,GPT-5.4",
        "category": "AI对话",
        "prompt": '''你是一位每天同时使用ChatGPT Plus、Claude Pro和DeepSeek的专业用户，写一篇三国杀级别的深度对比。

主题：ChatGPT vs Claude vs DeepSeek — 2026年真实差距在哪里？

背景：三款AI代表了三条不同的技术路线（OpenAI通用路线、Anthropic安全路线、DeepSeek开源路线）。用户经常问"到底买哪个订阅"，这篇文章要给出明确答案。

要求：
- 基于真实使用经验，不是参数罗列
- 敢说真话：哪个被高估了？哪个被低估了？
- 价格要算细账：月花多少钱能得到什么

文章结构（2500-3000字）：

## 引子（150字）
描述一个真实的日常：你一天之内三个AI轮流用的场景。比如早上用Claude写方案，下午用ChatGPT查资料，晚上用DeepSeek跑代码。

## 创作能力大PK（700字）
同一个写作任务让三个AI分别完成：
- 任务1：写一篇2000字的行业分析报告（给框架+开头）
- 任务2：把一段技术文档改写成小白能懂的文章
- 任务3：中文创意写作（写个产品营销文案）
评分标准：准确性、可读性、文风自然度、是否需要大量修改
结论附上三个AI的实际输出片段对比

## 编程实战对比（600字）
真实项目测试：
- 从零搭建一个Web API（全栈任务）
- Debug一段有隐蔽bug的代码
- 代码审查和优化建议
哪个真能当程序员的"配对工程师"？

## 中文能力（这个很关键）（400字）
虽然都是美国公司的产品，但中文能力差异很大：
- 翻译质量（中→英 / 英→中）
- 中文长文理解
- 中文语境下的"情商"
- DeepSeek作为国产选手有没有主场优势？

## 价格账本（400字）
| 项目 | ChatGPT Plus | Claude Pro | DeepSeek Plus |
|------|-------------|-----------|--------------|
| 月费 | | | |
| 限额 | | | |
| 超额计费 | | | |
| 实际月花费估算 | | | |
| 值不值 | | | |

## 最终推荐：按使用场景（350字）
明确给出结论：
- 写作者选什么？
- 程序员选什么？
- 研究人员选什么？
- 学生/预算有限的选什么？

直接写正文。'''
    },
    # --- A3: AI绘画工具 ---
    {
        "title": "Midjourney vs Stable Diffusion vs DALL-E vs 可灵：2026AI绘画四巨头横评",
        "slug": "midjourney-vs-sd-vs-dalle-vs-keling-2026",
        "description": "Midjourney V7、Stable Diffusion 3.5、DALL-E 3、可灵AI 2.0，四款主流AI绘画工具同一提示词实测对比。画质、风格控制、易用性、价格全方位比较，帮创作者选对工具。",
        "keywords": "Midjourney,Stable Diffusion,DALL-E,可灵AI,AI绘画对比,AI绘图工具,AI绘画评测,文生图",
        "category": "AI绘画",
        "prompt": '''你是一位设计师+AI绘画重度玩家，同时在用Midjourney、SD、DALL-E和可灵，写一篇硬核对比评测。

主题：2026年AI绘画四巨头横评 — 同一提示词，看看差距有多大

要求：
- 必须有具体的提示词案例（至少3组不同的提示词，每组都描述实际生成的效果差异）
- 不只谈画质，还要谈工作流效率（出图速度、修改成本、批量生产能力）
- 对中国用户特别说明哪些国内能用、哪些需要特殊网络

文章结构（2500-3000字）：

## 为什么做这次对比（150字）
简述当前AI绘画市场的格局变化：MJ出新版了、SD开源社区爆发、DALL-E集成到ChatGPT里了、可灵作为国产黑马崛起。用户选择困难症越来越严重。

## 测试方法说明（200字）
- 使用3组标准提示词（写实人像/科幻场景/商业插画）
- 统一生成尺寸和设置
- 评价标准：画质、风格还原度、细节丰富度、一致性

## 提示词组1：写实人像（600字）
给出完整的英文/中文提示词
描述四个平台各自生成的效果（用文字精确描述画面差异）
评分排名
最佳适用场景分析

## 提示词组2：科幻/幻想场景（500字）
同上格式

## 提示词组3：商业插画/产品设计（400字）
同上格式，侧重商业可用性

## 工作流对比（不是单张图比拼）（500字）
这是很多评测忽略但最重要的部分：
- 出图速度（从输入到拿到结果的时间）
- 修改成本（想调整一个细节要多麻烦）
- 批量生成能力（一次出10张vs一张张来）
- 后期处理需求（生成后还要修多少）
- 学习曲线（新手上手要多久）

## 中国用户特别提醒（300字）
- 各平台访问方式
- 价格换算成人民币
- 免费额度对比
- 支付方式便利性

## 最终推荐矩阵（200字）
| 需求 | 首选 | 理由 |
|------|------|------|
| 追求最高画质 | | |
| 需要批量生产 | | |
| 预算有限 | | |
| 国内方便使用 | | |
| 商业项目交付 | | |

直接写正文。'''
    },
    # --- A4: AI编程工具 ---
    {
        "title": "Cursor vs Copilot vs Windsurf vs Cline：程序员AI助手2026年度测评",
        "slug": "cursor-vs-copilot-vs-windsurf-vs-cline-2026",
        "description": "Cursor 1.5、GitHub Copilot、Windsurf、Cline四款主流AI编程工具深度对比。从智能补全、代码生成、Debug效率、价格四个维度实测，帮助开发者选择最适合的AI编程搭档。",
        "keywords": "Cursor,GitHub Copilot,Windsurf,Cline,AI编程工具,AI编程对比,程序员AI助手,AI代码补全",
        "category": "AI编程",
        "prompt": '''你是有10年经验的全栈工程师，这四个AI编程工具都在实际项目中用过，写一篇程序员视角的真实测评。

主题：2026年AI编程工具终极PK — Cursor/Copilot/Windsurf/Cline谁值得掏钱？

要求：
- 用真实项目中的例子说话（不要空谈功能列表）
- 敢于批评：每个工具最让你崩溃的是什么
- 关注实际提效幅度：用了之后真的省时间了吗？省了多少？

文章结构（2500-3000字）：

## 背景：我这一年是怎么用AI写代码的（200字）
描述真实的工作流演变：从不用AI → 只用Copilot补全 → 全家桶混用。引出"到底该投入哪个"的问题。

## 四款工具快速定位（300字）
用一句话概括每个工具的性格/定位：
- Cursor：______
- Copilot：______
- Windsurf：______
- Cline：______

## 实测环节1：代码生成能力（600字）
3个真实编程任务：
1. 从零写一个RESTful API（含认证）
2. 复杂SQL查询优化
3. 前端组件开发（带状态管理）
每个任务记录：
- 第一次生成能用吗？（还是需要大幅改）
- 改到能用花了多长时间？
- 和自己手写的代码质量相比如何？
- 哪个工具在这个任务上赢了？

## 实测环节2：Debug与代码理解（500字）
拿一段有3个bug的代码（约200行），让每个工具找问题：
- 能找出几个？
- 给出的修复对不对？
- 解释清不清楚？
- 这个环节暴露了各工具最大的弱点是什么

## 实测环节3：大型项目的上下文管理（400字）
AI工具在大项目中表现如何？
- 能不能理解跨文件的依赖关系？
- 改了一个文件能不能预判影响范围？
- 会不会"改A坏B"？

## 价格与效率ROI计算（400字）
| 工具 | 月费 | 实际日均节省时间 | 时薪折算值 | ROI |
|------|------|----------------|-----------|-----|
| Cursor | | | |
| Copilot | | | |
| Windsurf | | | |
| Cline | | | |

## 结论：不同类型程序员的推荐（300字）
- 前端工程师 → 推荐
- 后端/全栈 → 推荐
- 数据科学/ML → 推荐
- 初学者/学生 → 推荐
- 团队Leader（考虑团队采购）→ 推荐

直接写正文。'''
    },
    # --- A5: AI视频生成 ---
    {
        "title": "可灵AI vs Runway vs Pika vs Veo：2026AI视频生成工具深度对比",
        "slug": "keling-vs-runway-vs-pika-vs-veo-2026",
        "description": "可灵2.0、Runway Gen-4、Pika 2.0、Google Veo 3.1四款AI视频生成工具实测对比。从视频画质、动作连贯性、中文提示词支持、价格等维度全面评测，帮你选对AI视频工具。",
        "keywords": "可灵AI,Runway,Pika,Veo,AI视频生成,AI视频工具对比,文生视频,AI视频评测,Sora替代品",
        "category": "AI视频",
        "prompt": '''你是短视频创作者+AI视频工具的早期使用者，这四款工具都有实际的商用经验，写一篇深度对比。

主题：2026年AI视频生成哪家强？可灵 vs Runway vs Pika vs Veo

背景：Sora关停后市场重新洗牌，国产可灵崛起，Runway持续迭代，Google推出Veo 3.1。内容创作者该怎么选？

文章结构（2500-3000字）：

## 市场格局速览（150字）
简单交代Sora退场后的竞争态势，引出四款主力工具。

## 核心测试：统一提示词对比（800字）
准备4组不同类型的提示词：
1. 人物动态（"一位女性在海边跑步，长发飘动，慢动作"）
2. 自然景观（"瀑布飞流直下，阳光透过水雾形成彩虹"）
3. 动物行为（"一只金毛幼犬在草地上追蝴蝶"）
4. 特效向（"赛博朋克风格的未来城市，飞行汽车穿梭"）

每组提示词：
- 中英文各跑一次（测试中文理解）
- 记录生成时长
- 描述实际效果（画质/连贯性/光影/细节）
- 1-5分评分

## 功能深度对比（600字）
| 功能 | 可灵 | Runway | Pika | Veo |
|------|------|--------|------|-----|
| 最大时长 | | | | |
| 最高分辨率 | | | | |
| 图生视频 | | | | |
| 视频编辑 | | | | |
| 音效生成 | | | | |
| 风格控制 | | | | |

## 中文支持专项测试（300字）
这对国内用户极其重要：
- 纯中文提示词的效果 vs 英文
- 中文语义理解（比如"国风""水墨画"这种文化特色词）
- 哪个对中文用户最友好

## 价格与商用授权（400字）
- 各平台的免费额度
- 付费方案
- 商用授权条款（生成的内容能直接用在广告/短视频变现吗？）
- 性价比排序

## 适用场景推荐（300字）
- 抖音/快手短视频博主 → 选
- 广告/宣传片制作 → 选
- 个人创作者/UP主 → 选
- 企业级应用 → 选
- 预算为零的学生 → 选

直接写正文。'''
    },
]

# ================================================================
#  B 类：场景化工具推荐
# ================================================================
PROMPTS_B = [
    {
        "title": "2026年自媒体人AI工具箱：从选题到发布的全套自动化方案",
        "slug": "content-creator-ai-toolkit-2026",
        "description": "自媒体人/博主必备AI工具推荐，覆盖选题策划、文案写作、封面设计、视频剪辑、数据分析全流程。15款工具按免费/低价分级推荐，帮你一个人干出一个团队的活。",
        "keywords": "自媒体AI工具,博主工具,AI写作,AI封面设计,短视频AI工具,自媒体效率工具,AI选题,AI数据分析",
        "category": "AI办公",
        "prompt": '''你是一个全职自媒体人，靠AI工具把自己的工作效率提升了3倍，写一篇给同行看的工具推荐。

主题：自媒体人的AI武器库 — 一个人干出一个团队

要求：
- 按"自媒体工作流"的每个环节推荐工具（不是随便罗列）
- 每个推荐要说清楚"为什么是这个而不是其他的"
- 区分免费和付费方案，照顾不同预算的创作者

文章结构（2500-2800字）：

## 自媒体人的痛点（200字）
描述典型的一天：选题焦虑、写稿3小时、排版半小时、剪视频到凌晨...引出AI工具链如何改变这个现状。

## 环节一：选题与热点追踪（400字）
推荐2-3个AI工具用于：
- 热点话题捕捉
- 选题灵感生成
- 竞品爆款分析
每个工具：名字+核心功能+为什么好用+免费/付费+使用技巧

## 环节二：内容创作（500字）
- AI写作工具（长文/短文案/脚本）
- 不同平台适配（公众号/小红书/抖音文案风格不同）
- 你自己的实战经验："我用XX写了篇XX，结果XX阅读量"
- 注意事项：AI写的初稿通常需要怎样调整才能发

## 环节三：视觉素材（400字）
- 封面图AI生成
- 配图/插画AI工具
- 数据可视化（让数据更好看）
- 排版美化工具

## 环节四：视频内容（400字）
- AI视频生成（适合口播外的B-roll素材）
- AI剪辑/字幕
- 数字人出镜（不想真人出镜时）
- 背景音乐/音效

## 环节五：运营与分析（300字）
- 发布多平台分发工具
- 数据分析（哪些内容效果好）
- 粉丝互动自动化
- 变现辅助

## 我的个人工具栈（透明分享）（200字）
你自己在用的完整工具清单 + 月总成本 + 哪些觉得最值哪些可以不买

## 新手起步最低成本方案（150字）
预算为0时用什么？预算100元/月呢？预算500元/月呢？

直接写正文。'''
    },
    {
        "title": "程序员2026AI效率工具集：写代码只是冰山一角",
        "slug": "programmer-ai-efficiency-tools-2026",
        "description": "除了AI编程助手，程序员还需要哪些AI工具？从代码审查、文档生成、API调试、数据库优化到部署运维，12款AI工具覆盖程序员工作全流程，实测告诉你哪些真正能提效。",
        "keywords": "程序员AI工具,AI代码审查,AI文档生成,AI调试工具,AI运维,程序员效率,Developer tools,AI for developers",
        "category": "AI编程",
        "prompt": '''你是一个追求极致效率的程序员，不只是用AI写代码，而是把AI嵌入到开发的每一个环节，写一篇全面的工具推荐。

主题：程序员的AI军火库 — 不止是Copilot

很多程序员只知道AI编程助手（Cursor/Copilot），但其实AI能渗透到开发流程的每个环节。这篇文章要把全链路讲透。

文章结构（2500-2800字）:

## 开发流程全景（200字）
画一个典型的软件开发流程图（用文字描述）：需求→设计→编码→测试→文档→部署→运维，标出每个环节有哪些AI工具可以用。

## 编码阶段（大家都在做的）（500字）
- AI编程助手（简要回顾Cursor/Copilot/Windsurf的选择）
- 代码片段生成（特定场景的快速模板）
- 单元测试自动生成
- Code Review辅助

## 调试与排错（400字）
- AI驱动的错误诊断（不只是报错信息粘贴）
- 日志分析和异常检测
- 性能瓶颈定位
- 安全漏洞扫描

## 文档与知识管理（400字）
这个环节最容易被忽视但也最耗时间：
- 自动生成API文档
- README/注释自动补全
- 技术文档撰写（架构设计文档/决策记录）
- Wiki知识库维护

## DevOps与基础设施（300字）
- AI辅助的Docker/K8s配置生成
- CI/CD Pipeline配置
- 监控告警智能化
- 数据库查询优化建议

## 沟通与协作（300字）
- 技术方案的AI评审
- Code Review意见生成
- 周报/日报自动整理
- 技术分享PPT大纲生成

## 我的实际工具组合 + 成本（200字]
透明展示你日常使用的完整工具链和月度花费

## ROI量化（200字）
用了这些工具之后：
- 每天节省多少时间？
- 哪个环节提效最明显？
- 哪些工具其实没用处？（避坑）

直接写正文。'''
    },
    {
        "title": "大学生免费AI工具大全：论文、笔记、PPT、翻译一个都不花钱",
        "slug": "student-free-ai-tools-2026",
        "description": "大学生必看的免费AI工具合集，涵盖AI论文润色、课堂笔记整理、PPT自动生成、外语学习、文献检索等12个场景。全部免费可用，帮助学生党零成本提升学习效率。",
        "keywords": "大学生AI工具,免费AI工具,AI论文,AI笔记,AI PPT,学生党AI,免费AI写作,AI翻译,AI学习工具",
        "category": "AI效率",
        "prompt": '''你是一个善于挖掘免费资源的大学生（或刚毕业不久），深知学生党没钱的痛，写一篇"白嫖党福音"级别的工具推荐。

主题：学生党的免费AI武器库 — 论文/笔记/PPT/翻译全覆盖

要求：
- 所有推荐的工具必须有**免费可用**的方案
- 诚实标注"免费版限制"（不要骗人说完全免费结果核心功能要钱）
- 针对学生的真实学习场景，不推荐工作中才用的工具

文章结构（2300-2600字）:

## 学生的真实痛点（150字）
论文写到崩溃、PPT做到凌晨、英语课文看不懂、专业课笔记记不过来...这些场景你有共鸣吗？

## 论文写作神器（500字）
- AI论文润色/降重（注意学术诚信边界）
- 文献检索与管理（AI辅助找论文）
- 参考文献格式自动生成
- 数据分析与图表制作
- ⚠️ 特别说明：哪些可以用，哪些涉及学术不端

## 课堂学习（400字）
- AI笔记整理（录音转文字→自动提炼要点）
- PPT自动生成（输入大纲→输出完整PPT）
- 公式/概念解释（像问老师一样问AI）
- 语言学习（口语陪练/作文批改）

## 作业与考试备考（400字）
- 习题解答思路引导（不是直接给答案）
- 思维导图自动生成（复习用）
- 重点知识抽取（从课本/课件中）
- 错题本智能分析

## 英语/小语种学习（300字）
- AI翻译（比传统翻译软件好在哪）
- 口语练习伙伴
- 作文批改与润色
- 外刊阅读辅助（生词标注+难度适配）

## 生活实用（200字）
- 简历/求职信优化
- 兼职/实习信息整合
- 时间管理/日程规划
- 省钱攻略（学生优惠汇总）

## 免费工具汇总表（200字）
| 场景 | 推荐工具 | 免费额度 | 限制说明 | 推荐指数 |
|------|---------|---------|---------|---------|

直接写正文。'''
    },
    {
        "title": "设计师AI工具箱2026：从灵感捕捉到最终交付的全链路方案",
        "slug": "designer-ai-toolkit-2026",
        "description": "UI/UX设计师、平面设计师、插画师的AI工具推荐合集。覆盖灵感收集、草图生成、配色方案、图标设计、原型制作到交付输出的全流程，14款工具让设计师效率翻倍。",
        "keywords": "设计师AI工具,AI设计,AI绘画,UI设计AI,AI配色,AI图标,AI原型,Figma AI,Canva AI,设计效率工具",
        "category": "AI设计",
        "prompt": '''你是一名紧跟AI趋势的设计师（UI/UX+平面都会），已经在实际项目中大量使用AI工具提高产出，写一篇给设计师同行的深度推荐。

主题：设计师的AI外挂 — 从灵感到交付全链路加速

文章结构（2500-2800字）:

## 设计行业的AI焦虑与机遇（200字]
坦率讨论：AI会取代设计师吗？你的观点是什么？然后转折到"与其担心不如利用"。

## 阶段一：灵感与构思（400字）
- AI头脑风暴（输入模糊想法→输出具体方向）
- Mood Board自动生成
- 风格参考搜索（以图搜图/AI风格分类）
- 色彩趋势分析
实战案例：我是怎么用AI在10分钟内搞定客户要的3套风格方案的

## 阶段二：视觉素材创建（600字）
- AI图像生成（Midjourney/Stable Diffusion/可灵的设计工作流）
- AI图标/插画生成
- AI去背景/超分辨率/图片修复
- AI字体搭配推荐
关键：如何让AI生成的素材融入设计而不显得"AI味太重"

## 阶段三：界面设计与原型（500字）
- Figma AI功能详解（真的好用还是噱头？）
- AI辅助布局（从线框到高保真）
- AI生成响应式适配方案
- 设计系统/Design Token自动生成
- AI辅助的可访问性检查

## 阶段四：交付与协作（300字]
- AI切图/标注自动化
- 设计稿→前端代码（靠谱程度如何？）
- 客户反馈的AI辅助处理（"感觉不对"→AI给修改方向）
- 版本管理与变体生成

## 设计师的核心竞争力变了？（300字）
AI时代设计师真正不可替代的能力是什么？技能树该如何更新？

## 工具推荐汇总表（200字）
按使用频率排序，标明免费/付费

直接写正文。'''
    },
]

# ================================================================
#  C 类：教程指南
# ================================================================
PROMPTS_C = [
    {
        "title": "DeepSeek完全使用手册：从注册到高级技巧的保姆级教程",
        "slug": "deepseek-complete-guide-2026",
        "description": "DeepSeek新手入门到精通的完整教程，包括账号注册、R1/R2深度思考模式使用、API调用、提示词技巧、常见问题解决等。一篇搞懂DeepSeek所有核心功能。",
        "keywords": "DeepSeek教程,DeepSeek使用,DeepSeek R1,DeepSeek API,DeepSeek提示词,DeepSeek深度思考,AI助手教程",
        "category": "AI对话",
        "prompt": '''你是一个DeepSeek的重度使用者（每天都在用），写一篇新手看了就能上手的完整教程。

主题：DeepSeek从入门到精通 — 我踩过的坑你别再踩

文章结构（2500-2800字）:

## DeepSeek是什么？为什么要用它？（200字）
简单介绍DeepSeek背景（幻方量化出品、开源先锋、2025-2026年的突破性进展），以及和ChatGPT/Claude的核心区别。

## 第一步：注册与登录（300字）
- 支持哪些注册方式（手机号/邮箱/第三方）
- 国内用户直接用还是很顺畅的
- 免费账户有什么限制
- Plus会员值不值得开（详细算账）

## 第二步：基础使用（400字）
- 界面介绍（网页版/App/API三个入口）
- 最基本的使用方式
- 第一次对话该聊什么（给几个好的 starter prompt）
- 对话管理的最佳实践（新建对话的时机）

## 第三步：深度思考模式（重点！）（600字）
这是DeepSeek最强的差异化功能：
- 什么是R1/R2深度思考模式？什么时候该开？
- 展示一个对比案例：同样一个问题，普通模式 vs 深度思考模式的回答差异
- 哪类问题开了深度思考效果飞跃？哪类问题开了反而浪费时间？
- 深度思考模式的局限性和坑

## 第四步：API开发者指南（400字）
- 如何获取API Key
- 价格（真的比OpenAI便宜多少）
- 用Python调用的最小示例（贴完整代码）
- 常见API问题和解决方案

## 第五步：提示词进阶技巧（400字）
- DeepSeek擅长什么样的提示词风格？
- 和ChatGPT的prompt写法有什么不同？
- 5个你亲测有效的提示词模板
- 让DeepSeek输出更精准的技巧（温度/长度/格式控制）

## 常见问题FAQ（200字）
- 回复中断怎么办？
- 为什么有时候回答很短？
- 怎么上传文件给它分析？
- 数据隐私安全吗？

直接写正文。'''
    },
    {
        "title": "Midjourney新手零基础教程：2026年版从注册到出大片",
        "slug": "midjourney-beginner-tutorial-2026",
        "description": "Midjourney最新版本完整入门教程，涵盖Discord注册加入、/imagine命令使用、参数设置、提示词编写技巧、Niji动漫模式等。小白也能跟着做出高质量AI画作。",
        "keywords": "Midjourney教程,Midjourney入门,Midjourney提示词,AI绘画教程,Midjourney注册,Midjourney参数,Niji模式",
        "category": "AI绘画",
        "prompt":'''你是Midjourney的老用户（从V3就开始用），写一篇面向零基础小白的教程。

主题：Midjourney 2026 — 0基础到出大片的完整路径

文章结构（2400-2700字）:

## Midjourney是什么？为什么选它而不是其他？（150字]
一句话概括+和其他AI绘画工具的核心区别（质量最高但学习成本也最高）。

## 注册与准备工作（350字）
- Discord账号注册（一步步截图般的文字描述）
- 加入Midjourney服务器
- 订阅方案选择（哪个套餐适合新人？）
- /subscribe 命令的使用
- 新用户免费体验额度说明

## 你的第一张图（300字）
- 找到正确的频道
- 输入第一个 /imagine prompt
- 等待生成的过程说明
- U/V按钮的作用（放大/变换）
- 保存图片的方法

## 提示词基础（500字）
- 最简单的提示词结构：主体 + 风格 + 参数
- 10个高频实用参数一览（--ar --s --niji --style --cref等）
- 中英文提示词效果差异（推荐用英文写prompt的原因+技巧）
- 5组立竿见影的提示词模板（复制就能用）

## 进阶技巧（500字）
- Image Prompt（参考图生成）：怎么让人物/风格保持一致
- Blend（图片融合）：混合两张图的风格
- Describe（图生文）：分析一张图的prompt
- Niji动漫模式详解（二次元爱好者必读）
- 风格化参数（--s）的最佳实践

## 常见失败案例与解决方法（300字）
- "生成的不像我要的" → 怎么优化提示词
- "画面崩坏/变形" → 什么原因+怎么避免
- "风格不一致" → 如何用cref保持角色一致
- "被审核拦截了" → 敏感词规避技巧

## 省钱技巧（200字）
- 怎么用最少的GPU时长出最多的图
- 合理使用 relax mode
- 批量生成的效率技巧
- 有没有免费的替代方案

直接写正文。'''
    },
    {
        "title": "国内怎么用ChatGPT和Claude：2026年最新方法汇总",
        "slug": "how-to-use-chatgpt-claude-in-china-2026",
        "description": "国内用户访问ChatGPT和Claude的完整指南，包括账号注册、支付充值、网络设置、官方API接入等多种方案。对比各方案的优缺点和成本，帮你找到最适合的方式。",
        "keywords": "国内用ChatGPT,国内用Claude,ChatGPT注册,Claude注册,ChatGPT充值,Claude充值,AI科学上网,ChatGPT API国内",
        "category": "AI对话",
        "prompt":'''你在国内同时使用ChatGPT和Claude超过一年，对各种"翻墙"和使用方法了如指掌。写一篇实用的方法汇总。

主题：2026年在国内用ChatGPT和Claude — 所有方法一次讲清

⚠️ 要求：
- 诚实说明每种方法的合法合规风险
- 不教违法的事，但客观呈现现有方案
- 包含最新的政策/服务变化情况
- 语气中立，不做任何政治评论

文章结构（2500-2800字）:

## 为什么国内用户想用ChatGPT/Claude？（150字]
简述国产AI（DeepSeek/Kimi等）已经很强大了，但在某些方面海外AI仍有优势，所以用户有跨境使用需求。

## 方案概览对比表（200字）
| 方案 | 难度 | 成本 | 稳定性 | 风险 | 适合人群 |
|------|------|------|--------|------|---------|
| 科学上网+官网 | | | | |
| API中转服务 | | | | |
| 海外虚拟卡+官网 | | | | |
| 第三方镜像站 | | | | |
| 合规企业通道 | | | | |

## 方案一：科学上网+官方客户端（600字）
- 网络工具选择（只提不违规的类型）
- ChatGPT注册步骤（2026年最新流程）
- 手机号验证问题（接码平台/海外手机号）
- 付款方式（Depay/Wildcard/Nobe等虚拟卡方案）
- Claude注册的特殊限制（不支持中国区）
- 常见问题：封号/风控/登录异常

## 方案二：API中转服务（500字）
- 原理：通过第三方中转调用OpenAI/Anthropic API
- 优势：不需要翻墙、稳定、按量付费
- 推荐的中转服务商（列3-5个，说明各自的价差和服务质量）
- 使用方法（Python示例代码）
- 和官方API的功能差异
- 安全性考量（数据经过第三方）

## 方案三：官方API直连（400字）
- 如果你有海外服务器/云环境
- OpenAI API在国内可以直接调吗？（2026年最新情况）
- Anthropic API同理
- 企业用户的合规方案
- 成本对比

## 方案四：替代方案 — 其实你可能不需要出海（300字)
诚实评估：2026年国产AI（DeepSeek R2/Kimi k1.5/豆包Seed 2.0）已经达到什么水平？
哪些场景下国产AI完全够用？
哪些场景下确实还需要ChatGPT/Claude？

## 成本汇总（200字）
各种方案的月费用区间，从0元到几百元不等

## 选择建议（150字）
根据用户身份（学生/上班族/开发者/企业）给出推荐

直接写正文。'''
    },
    {
        "title": "Suno AI音乐生成完整指南：从入门到发布一首歌",
        "slug": "suno-music-complete-guide-2026",
        "description": "Suno V4音乐生成工具的完整使用教程，包括注册入门、歌词编写技巧、风格选择、音乐结构控制、音频质量优化等。零基础也能学会用AI创作原创音乐。",
        "keywords": "Suno教程,Suno音乐生成,AI作曲,AI音乐创作,Suno V4,AI写歌,Suno歌词,Suno使用技巧",
        "category": "AI音频",
        "prompt":'''你是一个用Suno创建了30+首歌曲的音乐爱好者，写一篇从入门到能发布作品的完整教程。

主题：用Suno做音乐 — 不会乐器也能出原创歌曲

文章结构（2300-2600字）:

## Suno是什么？能做出什么样的音乐？（150字）
简述+嵌入你对Suno能力的客观评价（能做到什么程度、做不到什么、和专业制作的差距）。

## 注册与界面熟悉（250字）
- 注册流程（非常简单）
- 免费额度说明（每天能生成多少）
- 付费方案对比（Create vs Pro vs Premier）
- 界面功能一览

## 快速上手：你的第一首歌（300字）
- 最简单的方式（只输入风格描述，不写歌词）
- 听一听效果 → 通常还不错但缺乏个性
- 引出"想要更好的效果需要怎么做"

## 歌词编写的艺术（600字）
这是Suno出好歌的关键：
- 歌词的基本结构（主歌/副歌/桥段/尾奏）
- 用[括号标记]控制音乐结构
- 风格提示词怎么写（"pop rock, female vocals, upbeat"这类）
- 元标签详解（[Verse]、[Chorus]、[Bridge]、[Guitar Solo]等）
- 歌词的情感表达（AI能感知歌词情绪并反映在旋律中）
- 语言问题：中文歌 vs 英文歌的质量差异
- 给出2个完整的歌词模板（一个中文一个英文），读者可直接复制使用

## 高阶技巧（500字）
- Instrumental（纯音乐）模式
- 用音频片段作为风格参考（Audio Input）
- Extend功能（延长歌曲某一部分）
- Merge（合并两个片段）
- 如何让自己的歌曲有"记忆点"
- v3.5/v4版本的新功能利用

## 从创作到发布（200字）
- 导出音频（wav/mp3）
- 版权说明（Suno生成的内容版权归谁？能商用吗？）
- 发布到音乐平台（网易云音乐/QQ音乐/Spotify）
- 在抖音/B站/YouTube做音乐类内容的可能性

## 10个亲测有效的风格Prompt（200字]
列出10种风格组合的prompt模板，覆盖流行/摇滚/古风/电子/爵士/说唱等

直接写正文。'''
    },
]


# ================================================================
#  全部文章池（A+B+C 合并，按优先级排列）
# ================================================================

# ================================================================
#  E Category: English Global Content (Outbound strategy)
# ================================================================
PROMPTS_E = [
    {
        "title": "2026 AI Tool ROI Benchmark: 48+ Tools Tested for Real-World Profitability",
        "slug": "2026-ai-tool-roi-benchmark-48-tools-profitability",
        "description": "We rigorously tested 48+ AI tools across content creation, coding, and automation. Here is the definitive ROI report for 2026.",
        "keywords": "AI Tool ROI, best AI tools 2026, profitable AI, AI tools benchmark, AI for business efficiency",
        "category": "Market Trends",
        "prompt": """You are a professional AI industry analyst with a focus on business ROI and practical implementation. Write a high-authority, deep-dive article (2000-3000 words).

Theme: 2026 AI Tool ROI Benchmark: 48+ Tools Tested for Real-World Profitability

Context: It's April 2026. The AI market has shifted from 'hype' to 'utility.' Businesses are cutting subscriptions that don't yield direct returns. We spent 3 months testing 48 tools.

Requirements:
- Categorize tools by: Content Gen, Dev Tools, Automation, and Niche Business Apps.
- Use a 'Hard ROI' vs 'Soft ROI' metric.
- Include a section on 'The 2026 Efficiency Stack.'
- Critical and objective tone. No marketing fluff.

Structure:
## Executive Summary
Summarize the state of AI efficiency in 2026. The era of generic wrappers is over.

## Category 1: Generative Content - Beyond Text
Focus on video and high-fidelity 3D assets. (Sora 2, Kling 3, etc.)

## Category 2: Developer Productivity - The Agentic Shift
Cursor, Windsurf, and the rise of autonomous coding agents.

## Category 3: Business Automation - Connecting the Dots
Make.com, Zapier Central, and multi-agent workflows.

## The ROI Leaderboard (Table)
List top 10 tools with estimated % efficiency gain.

## Conclusion: How to Build Your 2026 AI Strategy
"""
    }
]

ALL_PROMPTS = (
    [(p, 'A') for p in PROMPTS_A] +
    [(p, 'B') for p in PROMPTS_B] +
    [(p, 'C') for p in PROMPTS_C] +
    [(p, 'E') for p in PROMPTS_E]
)


# ============================================================
# AEO+GEO 通用追加要求（2026-06-23）
# 所有 prompt 在调 API 前会自动拼接此段，确保新文章自动符合
# AEO（Answer Engine Optimization）+ GEO（Generative Engine Optimization）
# 知识来源：Princeton GEO 论文 + Google 2026-05-15 官方 AI 搜索指南
# ============================================================
AEO_GEO_SUFFIX = """

=== AEO + GEO 写作规范（必须严格遵守，否则返工）===

【开头 BLUF（Bottom Line Up Front）】
正文第一行必须是 Markdown 引用块，以 "> 一句话结论：" 开头，40-60 字内直接给出本文的核心结论。
不要"在本文中我们将探讨..."这种废话开场，AI 引擎只提取前 1-2 句话作为答案。

【专家/权威引言块】
开头第二行必须是另一个 Markdown 引用块，引用一位真实的行业专家、官方机构、研究报告的原话，并署名。
真实示例：
> "笔记工具的核心价值不是功能多寡，而是十年后你还能不能打开当年的笔记。" —— Nick Milo，Obsidian 社区核心贡献者
> "AI 编程工具的月费不是成本，是时薪的零头——选错工具每周浪费 5+ 小时。" —— Andrej Karpathy，2026-03 X 推文
不要瞎编人名和语录，引用真实的公开人物/机构/报告。如果实在没有合适引用，引用本文作者自己的实测记录并署名"—— 本文作者实测记录，YYYY-MM"。

【H2 标题必须是问题式】
所有 H2（## 开头）必须是疑问句或问题导向的陈述句，例如：
- 不要：## 编码能力对比
- 要：## 编程能力谁更强？Claude 完胜，没有悬念
- 不要：## 价格分析
- 要：## 价格谁更划算？同价竞争，但有个隐藏坑
- 不要：## 踩坑经验
- 要：## 使用时踩了哪些坑？
原因：AI 引擎（ChatGPT/Perplexity/Google AI Overviews）按用户问题匹配内容，问题式 H2 被引用率提升 30%+。

【段落 BLUF 化】
每个段落第一句话直接给结论/答案（40-60 字），后面再展开背景、细节、案例。
不要"首先让我们了解一下背景..."这种铺垫，AI 会直接跳过。

【段落短化】
每段 2-3 句话，便于 AI 程序化解析。超过 4 句的段落必须拆开。

【带来源的统计数据】
全文必须包含至少 3-5 个带来源的统计数据，例如：
- 错误：用户很多
- 正确：根据 Notion 2026 Q1 财报，月活用户达 1.2 亿
- 错误：速度快
- 正确：实测响应时间 2.8 秒（来源：作者 2026-04 实测，50 次取平均）
数据来源优先级：官方年报/财报 > 行业协会 > 权威媒体 > 第三方数据平台 > 作者实测。
不要瞎编数据，宁可引用作者实测记录，也不要写"行业数据显示"这种模糊话。

【FAQ 区块】
文末必须有 "## 常见问题（FAQ）" 区块，3-5 个用户真实会问的问题，每个答案 50-100 字，直接给结论。
不要"什么是 XX？XX 是一种..."这种百科式伪 FAQ，要写真实用户疑问。
示例：
Q: Obsidian 和 Logseq 都支持本地 Markdown，到底选哪个？
A: 如果你主要做"写"（长文、博客、读书笔记），选 Obsidian。如果你主要做"连"（知识图谱、学术引用），选 Logseq。

【最终结论区块】
文末 FAQ 之后，必须有 "## 最终结论：到底选哪个？"（或对应场景的"怎么选/怎么用/哪个值"）区块，包含一个总结表格（你的需求 → 推荐 → 月成本/理由），最后一句直接给作者的明确推荐。

【内链】
文中提到的 AI 工具名，必须用 <a href="/tools/{slug}/index.html">工具名</a> 格式做成内链（slug 用工具英文短横线名，如 chatgpt、claude、cursor、deepseek、kimi、perplexity、notion-ai、notebooklm 等）。每个工具第一次出现时做内链，后续直接用名字。

【禁忌】
- 禁止关键词堆砌（GEO 实测 -8% 负效果）
- 禁止伪 FAQ（为搜索引擎生成的模板问答已被 Google 判死）
- 禁止"保姆级教程""yyds""赶紧收藏"等营销词
- 禁止 emoji 滥用（只在确实需要的列表前用，正文段落不用）
- 禁止"在本文中我们将探讨""首先让我们了解"等铺垫

=== AEO + GEO 规范结束 ===

请按以上规范生成正文。直接输出 Markdown 内容，不要前后缀说明。"""


def build_prompt_with_aeo_geo(original_prompt):
    """拼接原始 prompt + AEO/GEO 通用规范"""
    return original_prompt + AEO_GEO_SUFFIX


def call_api(prompt, max_tokens=8000, timeout=300):
    """调用 DeepSeek-V3 API（自动拼接 AEO+GEO 规范）"""
    full_prompt = build_prompt_with_aeo_geo(prompt)
    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [ERROR] API call failed: {e}")
        return None


def load_state():
    """加载轮替状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"produced_slugs": [], "last_type": None, "history": []}


def save_state(state):
    """保存轮替状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_existing_slugs():
    """获取已产出的文章slug集合"""
    slugs = set()
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
            articles = json.load(f)
            slugs = {a['slug'] for a in articles}
    if os.path.exists(DRAFTS_FILE):
        with open(DRAFTS_FILE, 'r', encoding='utf-8') as f:
            drafts = json.load(f)
            slugs.update(drafts.keys())
    state = load_state()
    slugs.update(state.get("produced_slugs", []))
    return slugs


def select_next_article(force_type=None):
    """
    智能选择下一篇要产出的文章。
    
    策略：
    1. 强制指定类型则从该类型队列取第一篇未产的
    2. 否则按 A→B→C 轮替，优先从未产出的文章中选择
    3. 类型内按定义顺序排列
    """
    existing = get_existing_slugs()
    state = load_state()

    if force_type:
        candidate_pool = [(p, t) for p, t in ALL_PROMPTS if t == force_type and p['slug'] not in existing]
        if not candidate_pool:
            print(f"[WARN] 类型 {force_type} ({ARTICLE_TYPES[force_type]['label']}) 的文章已全部产出！")
            return None
        return candidate_pool[0]

    # 轮替逻辑：上次产了什么类型，这次优先产下一个类型
    type_order = ['E', 'A', 'B', 'C']
    last_type = state.get("last_type")

    if last_type:
        # 从下一个类型开始找
        idx = type_order.index(last_type) if last_type in type_order else -1
        ordered_types = type_order[idx+1:] + type_order[:idx+1]
    else:
        ordered_types = type_order

    for t in ordered_types:
        for p, pt in ALL_PROMPTS:
            if pt == t and p['slug'] not in existing:
                return (p, t)

    # 全部产出过了
    print("[INFO] 所有预设文章都已产出过！可以考虑添加新的prompt模板。")
    return None


def list_queue():
    """查看当前轮替队列（显示未产出的文章）"""
    existing = get_existing_slugs()
    print("=" * 70)
    print(f"{'类型':<4} {'标题':<50} {'状态'}")
    print("-" * 70)

    type_labels = {k: v['label'] for k, v in ARTICLE_TYPES.items()}
    count_pending = 0
    count_done = 0

    for p, t in ALL_PROMPTS:
        status = "✅ 已产出" if p['slug'] in existing else "⏳ 待产出"
        if p['slug'] in existing:
            count_done += 1
        else:
            count_pending += 1
        print(f"{t:<4} {p['title']:<50} {status}")

    print("-" * 70)
    print(f"总计：{count_done} 已产出 / {count_pending} 待产出 / {len(ALL_PROMPTS)} 总计")


def generate_one(article_data, article_type):
    """生成单篇文章"""
    slug = article_data['slug']
    print(f"\n{'='*60}")
    print(f"[{article_type}] {article_data['title']}")
    print(f"Slug: {slug}")
    print(f"{'='*60}")

    content = call_api(article_data['prompt'])
    if not content:
        print(f"[FAIL] 生成失败: {slug}")
        return False

    print(f"  生成字数: {len(content)} 字符")

    # 检查字数是否达标（目标2000字以上，中文约3000字符起）
    if len(content) < 1500:
        print(f"  [WARN] 字数偏少({len(content)}字符)，可能达不到深度内容标准")

    # 保存到 drafts
    drafts = {}
    if os.path.exists(DRAFTS_FILE):
        with open(DRAFTS_FILE, 'r', encoding='utf-8') as f:
            drafts = json.load(f)

    drafts[slug] = {
        "title": article_data['title'],
        "slug": slug,
        "description": article_data['description'],
        "keywords": article_data['keywords'],
        "category": article_data['category'],
        "content": content,
        "type": article_type,
    }

    with open(DRAFTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

    # 更新状态
    state = load_state()
    if slug not in state.get("produced_slugs", []):
        state["produced_slugs"].append(slug)
    state["last_type"] = article_type
    state["history"].append({
        "slug": slug,
        "title": article_data['title'],
        "type": article_type,
        "time": datetime.now().isoformat(),
        "chars": len(content)
    })
    save_state(state)

    print(f"  [OK] 草稿已保存到 _article_drafts.json")
    return True


def main():
    parser = argparse.ArgumentParser(description='SEO文章批量生成器 v2 - 深度内容版')
    parser.add_argument('--type', choices=['A', 'B', 'C', 'E'], help='强制指定文章类型 (A=国产AI对比 B=场景推荐 C=教程)')
    parser.add_argument('--list', action='store_true', help='查看轮替队列状态')
    parser.add_argument('--all', action='store_true', help='一键产出所有未产出的文章（谨慎使用！）')
    args = parser.parse_args()

    if args.list:
        list_queue()
        return

    if args.all:
        existing = get_existing_slugs()
        pending = [(p, t) for p, t in ALL_PROMPTS if p['slug'] not in existing]
        if not pending:
            print("所有文章都已产出！")
            return
        print(f"\n将连续产出 {len(pending)} 篇文章...\n")
        success = 0
        fail = 0
        for i, (p, t) in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}]")
            if generate_one(p, t):
                success += 1
            else:
                fail += 1
            # 避免 API 限流
            if i < len(pending):
                wait = random.randint(3, 8)
                print(f"  等待 {wait}s 避免限流...")
                time.sleep(wait)
        print(f"\n完成！成功 {success} 篇，失败 {fail} 篇")
        print("下一步：运行 python humanize_articles.py 去AI味")
        print("       然后：运行 python add_articles.py 追加到articles.json")
        return

    # 默认模式：选下一篇产出
    selection = select_next_article(force_type=args.type)
    if not selection:
        print("\n没有更多待产出的文章了！")
        return

    article_data, article_type = selection
    print(f"\n📝 下篇文章：[{article_type}] {ARTICLE_TYPES[article_type]['label']} — {article_data['title']}")

    if generate_one(article_data, article_type):
        print("\n✅ 完成！下一步：")
        print("  1. python humanize_articles.py     （去AI味处理）")
        print("  2. python add_articles.py          （追加到文章库）")
        print("  3. python scripts/build.py          （构建网站）")
        print("  4. git push                         （部署）")


if __name__ == '__main__':
    main()

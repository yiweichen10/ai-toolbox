import json

PATH = "C:/Users/27040/WorkBuddy/20260321092139/seo-site/data/tools.json"

updates = {
    "sigma-computing": {
        "url": "https://www.sigmacomputing.com/",
        "description": "Sigma Computing 是 Sigma Computing 公司推出的云原生 BI 与分析平台，以类电子表格界面直连 Snowflake、BigQuery、Databricks 等数据仓库，支持实时查询、协作与 AI 应用。",
        "features": [
            "云原生架构：直连 Snowflake/Databricks/BigQuery 等数据仓库实时查询，治理在源头",
            "电子表格式分析界面，无需写 SQL 即可探索数十亿行数据",
            "AI Toolkit 与 Sigma Agents：用自然语言构建仪表板、应用并自动化任务",
            "AI Apps 平台：在受治理数据上快速构建、部署 AI 应用",
            "嵌入式分析与像素级精准（Pixel-Perfect）报表"
        ],
        "price": "暂未公开（官网提供免费试用，企业版需联系销售获取报价）",
        "platform": "Web",
        "source_url": "https://www.sigmacomputing.com/",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True
    },
    "tavily-ai": {
        "url": "https://tavily.com/",
        "description": "Tavily 是面向 AI 代理的实时搜索与检索 API（发布方：Tavily 公司），提供 Search、Extract、Crawl、Map、Research 接口，返回结构化网页数据以降低代理幻觉。",
        "features": [
            "Search API：为 LLM 优化的实时网页搜索，返回结构化、带评分的结果",
            "Extract API：从任意 URL 提取干净的结构化内容，免去 HTML 清洗",
            "Crawl / Map API：爬取与映射网站结构，构建检索索引",
            "Research API：自动多步研究并生成带引用的综合报告",
            "Keyless 免费接入：无需 API Key 即可试用 Search 与 Extract"
        ],
        "price": "免费版 1,000 credits/月（无需信用卡）；按量付费 $0.008/credit；Project 档约 4,000 credits/月（具体价格官网滑动选择）；企业版定制报价",
        "platform": "Web API",
        "source_url": "https://tavily.com/pricing",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True
    },
    "exa-ai": {
        "url": "https://exa.ai/",
        "description": "Exa 是面向 AI 应用的语义搜索与数据 API（发布方：Exa Labs），提供 Search、Deep Search、Websets、Research、Extract 等接口，以嵌入向量理解语义并返回结构化结果。",
        "features": [
            "Search API：基于嵌入向量的语义搜索，理解查询意图而非关键词",
            "Deep Search / Deep-Reasoning：深度检索与推理，返回更全结果",
            "Websets：处理复杂查询、批量返回数千条结果并结构化输出",
            "Research：跨网页与 PDF 的深入研究报告",
            "Extract / 内容抓取：从任意网页提取清洗后的全文；含 70M+ 公司与人物索引"
        ],
        "price": "Search $7/1k 请求；Deep Search $12/1k；Deep-Reasoning $15/1k；Contents $1/1k 页；Monitors $5/1k；提供免费试用额度",
        "platform": "Web, API",
        "source_url": "https://exa.ai/pricing",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True
    },
    "perplexity-sonar": {
        "url": "https://sonar.perplexity.ai/",
        "description": "Perplexity Sonar 是 Perplexity 推出的实时联网搜索与问答 API，提供 Sonar / Sonar Pro 等模型，返回带引用的回答，供开发者构建联网 AI 应用（官方域名 perplexity.ai）。",
        "features": [
            "实时联网搜索：从数十亿网页检索最新信息",
            "带引用的对话式回答（citations），降低幻觉",
            "提供 Sonar、Sonar Pro、Sonar Reasoning Pro、Sonar Deep Research 等模型",
            "OpenAI 兼容 Chat Completions 接口，易集成到现有应用",
            "可定制搜索来源、多查询搜索与搜索上下文深度"
        ],
        "price": "按量计费：Search API $5/千次请求；Sonar 模型输入/输出 $1/$1 per 1M tokens + 请求费 $5/$8/$12（低/中/高上下文）每 1k；Sonar Pro 输入/输出 $3/$15 per 1M + 请求费 $6/$10/$14；公开页面未标注长期免费额度",
        "platform": "Web API, SDK",
        "source_url": "https://docs.perplexity.ai/docs/getting-started/pricing",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True
    },
    "glide-ai": {
        "url": "https://www.glideapps.com/ai",
        "description": "Glide AI 是无代码应用平台 Glide 内置的 AI 能力（发布方：Glide 公司），可用自然语言生成应用、生成 UI 组件、提取文件信息并驱动 Glide Agent 工作流。",
        "features": [
            "Glide Agent：用自然语言描述即时生成定制应用（数据结构 + 布局）",
            "AI 生成 UI 组件：通过聊天界面创建交互卡片、进度条等",
            "文件洞察：将音频/图片/文本转为结构化信息（转录、摘要、提取）",
            "Glide AI 列：在 Workflow 中用 AI 处理数据、生成内容",
            "连接 Google Sheets/Excel/SQL 等数据源，无需编码即可搭建"
        ],
        "price": "Free 免费（无限草稿、1 编辑者、25k 行，不含 Glide AI）；Business 版起价 $199/月（年付，含 30 用户 + 5,000 更新）；Enterprise 定制；Glide AI 在 Explorer/Maker/Business/Enterprise 计划可用",
        "platform": "Web",
        "source_url": "https://www.glideapps.com/ai",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True
    }
}

d = json.load(open(PATH, encoding="utf-8"))
count = 0
for t in d:
    if t.get("slug") in updates:
        t.update(updates[t["slug"]])
        count += 1

json.dump(d, open(PATH, "w", encoding="utf-8"), indent=4, ensure_ascii=False)
print("updated", count, "tools")

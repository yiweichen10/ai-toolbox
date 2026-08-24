import json

results = [
    {
        "slug": "ironclad-ai",
        "name": "Ironclad AI",
        "verdict": "REAL",
        "official_url": "https://www.ironclad.ai",
        "url_correct": True,
        "vendor": "Ironclad, Inc.",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Ironclad官网ironclad.ai及公开资料确认其为AI合同管理与法律审查平台"
    },
    {
        "slug": "gaoding-ai",
        "name": "稿定设计AI",
        "verdict": "REAL",
        "official_url": "https://www.gaoding.com",
        "url_correct": True,
        "vendor": "稿定（厦门稿定股份）",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "稿定设计官网gaoding.com，国内知名在线设计平台，AI功能属实"
    },
    {
        "slug": "wps-ai",
        "name": "WPS AI",
        "verdict": "REAL",
        "official_url": "https://ai.wps.cn",
        "url_correct": True,
        "vendor": "金山办公（Kingsoft Office）",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "WPS官方论坛多处确认ai.wps.cn为WPS AI官网"
    },
    {
        "slug": "otter.ai",
        "name": "Otter.ai",
        "verdict": "REAL",
        "official_url": "https://otter.ai",
        "url_correct": True,
        "vendor": "Otter.ai (AISense Inc.)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "知名AI会议转录工具，官网otter.ai，功能与描述一致"
    },
    {
        "slug": "remove.bg",
        "name": "Remove.bg",
        "verdict": "REAL",
        "official_url": "https://www.remove.bg",
        "url_correct": True,
        "vendor": "Canva (收购)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "全球知名AI去背景工具，官网remove.bg"
    },
    {
        "slug": "weaviate",
        "name": "Weaviate",
        "verdict": "REAL",
        "official_url": "https://weaviate.io",
        "url_correct": True,
        "vendor": "Weaviate (SeMI Technologies)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "开源向量数据库，官网weaviate.io，描述准确"
    },
    {
        "slug": "writesonic",
        "name": "Writesonic",
        "verdict": "REAL",
        "official_url": "https://writesonic.com",
        "url_correct": True,
        "vendor": "Writesonic Inc.",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI写作/SEO内容平台，官网writesonic.com"
    },
    {
        "slug": "luma-ai",
        "name": "Luma AI",
        "verdict": "REAL",
        "official_url": "https://lumalabs.ai",
        "url_correct": True,
        "vendor": "Luma AI (Luma Labs)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Luma AI及Dream Machine视频模型，官网lumalabs.ai"
    },
    {
        "slug": "n8n",
        "name": "n8n",
        "verdict": "REAL",
        "official_url": "https://n8n.io",
        "url_correct": True,
        "vendor": "n8n GmbH",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "开源工作流自动化平台，官网n8n.io"
    },
    {
        "slug": "eightfold",
        "name": "Eightfold",
        "verdict": "REAL",
        "official_url": "https://eightfold.ai",
        "url_correct": True,
        "vendor": "Eightfold AI",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "人才智能/招聘平台，官网eightfold.ai"
    },
    {
        "slug": "pixso-ai",
        "name": "Pixso AI",
        "verdict": "REAL",
        "official_url": "https://pixso.cn",
        "url_correct": True,
        "vendor": "Pixso（即时设计团队）",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "国产UI设计工具Pixso，官网pixso.cn，内置AI功能"
    },
    {
        "slug": "augie-ai",
        "name": "Augie AI",
        "verdict": "REAL",
        "official_url": "https://augie.ai",
        "url_correct": True,
        "vendor": "Storyblocks (Augie)",
        "desc_issue": "实为AI视频生成/剪辑工具（Augie by Storyblocks），目录描述为通用'创意助手'略有偏差；且存在多个同名Augie产品（如销售助手myaugieai.com）易混淆",
        "confidence": "medium",
        "evidence": "augie.ai对应Augie（Storyblocks旗下AI视频工具），同名产品较多致歧义"
    },
    {
        "slug": "lumen5",
        "name": "Lumen5",
        "verdict": "REAL",
        "official_url": "https://lumen5.com",
        "url_correct": True,
        "vendor": "Lumen5",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI文本转视频平台，官网lumen5.com"
    },
    {
        "slug": "wujie-ai",
        "name": "无界AI",
        "verdict": "REAL",
        "official_url": "https://www.wujieai.com",
        "url_correct": True,
        "vendor": "无界AI团队（超次元）",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "国产AI绘画平台，官网wujieai.com"
    },
    {
        "slug": "tencent-hunyuan",
        "name": "腾讯混元",
        "verdict": "REAL",
        "official_url": "https://hunyuan.tencent.com",
        "url_correct": True,
        "vendor": "腾讯",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "腾讯混元大模型，官网hunyuan.tencent.com"
    },
    {
        "slug": "verba",
        "name": "Verba",
        "verdict": "REAL",
        "official_url": "https://github.com/weaviate/Verba",
        "url_correct": True,
        "vendor": "Weaviate",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Weaviate开源RAG应用Verba，GitHub仓库确认"
    },
    {
        "slug": "colossyan",
        "name": "Colossyan",
        "verdict": "REAL",
        "official_url": "https://colossyan.com",
        "url_correct": True,
        "vendor": "Colossyan",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI数字人视频平台，官网colossyan.com"
    },
    {
        "slug": "jenni-ai",
        "name": "Jenni AI",
        "verdict": "REAL",
        "official_url": "https://jenni.ai",
        "url_correct": True,
        "vendor": "Jenni AI",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "学术写作AI助手，官网jenni.ai"
    },
    {
        "slug": "decohere",
        "name": "Decohere",
        "verdict": "REAL",
        "official_url": "https://decohere.ai",
        "url_correct": True,
        "vendor": "Decohere",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI视频/图像生成工具，官网decohere.ai"
    },
    {
        "slug": "tempus-ai",
        "name": "Tempus AI",
        "verdict": "REAL",
        "official_url": "https://www.gettempus.app",
        "url_correct": False,
        "vendor": "Anh Nguyen / Van Anh Chu (Tempus AI Daily Planner)",
        "desc_issue": "记录URL tempus-ai.com 应为 gettempus.app；实际为AI日程规划/专注App（Tempus AI Daily Planner），功能描述基本准确但定价（$9.99/$29.99）与App Store实际不符",
        "confidence": "high",
        "evidence": "App Store及gettempus.app确认Tempus AI为AI时间管理App，无tempus-ai.com"
    },
    {
        "slug": "tongyi-wanxiang",
        "name": "通义万相",
        "verdict": "REAL",
        "official_url": "https://tongyi.aliyun.com/wanxiang",
        "url_correct": True,
        "vendor": "阿里巴巴（通义实验室）",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "阿里通义万相，官网tongyi.aliyun.com/wanxiang"
    },
    {
        "slug": "webflow-ai",
        "name": "Webflow AI",
        "verdict": "REAL",
        "official_url": "https://webflow.com",
        "url_correct": True,
        "vendor": "Webflow, Inc.",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Webflow无代码建站平台内置AI，官网webflow.com"
    },
    {
        "slug": "devin-ai",
        "name": "Devin AI",
        "verdict": "REAL",
        "official_url": "https://devin.ai",
        "url_correct": True,
        "vendor": "Cognition Labs",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Cognition推出的AI软件工程师Devin，官网devin.ai"
    },
    {
        "slug": "claude-fable-5",
        "name": "Claude Fable 5",
        "verdict": "REAL",
        "official_url": "https://www.anthropic.com",
        "url_correct": False,
        "vendor": "Anthropic",
        "desc_issue": "记录描述为'专注故事创作的AI写作工具(fable.anthropic.com)'与事实不符：Claude Fable 5是Anthropic的旗舰大模型（非写作工具），捏造了'超长叙事引擎/动态角色记忆/10万字故事'等能力；fable.anthropic.com并非Anthropic官方地址",
        "confidence": "medium",
        "evidence": "Anthropic透明度中心及多篇报道确认Claude Fable 5为Anthropic模型，无任何来源提及fable.anthropic.com"
    },
    {
        "slug": "invideo-ai",
        "name": "InVideo AI",
        "verdict": "REAL",
        "official_url": "https://invideo.io",
        "url_correct": True,
        "vendor": "InVideo",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI文本转视频平台，官网invideo.io"
    },
    {
        "slug": "prowritingaid",
        "name": "ProWritingAid",
        "verdict": "REAL",
        "official_url": "https://prowritingaid.com",
        "url_correct": True,
        "vendor": "ProWritingAid (Orpheus Technology)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "英文写作辅助工具，官网prowritingaid.com"
    },
    {
        "slug": "sourcegraph-cody",
        "name": "Sourcegraph Cody",
        "verdict": "REAL",
        "official_url": "https://sourcegraph.com/cody",
        "url_correct": True,
        "vendor": "Sourcegraph",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "Sourcegraph推出的AI编程助手Cody，官网sourcegraph.com/cody"
    },
    {
        "slug": "githits",
        "name": "GitHits",
        "verdict": "REAL",
        "official_url": "https://githits.com",
        "url_correct": False,
        "vendor": "GitHits (Jaakko Timonen 等，芬兰)",
        "desc_issue": "记录URL githits.ai 应为 githits.com；描述基本准确（AI驱动代码/仓库发现），但其核心定位是面向AI编程代理的开源代码索引/MCP服务，而非'社区热度趋势分析'推荐平台",
        "confidence": "high",
        "evidence": "githits.com确认GitHits为AI代理代码索引服务，2026年6月获175万美元种子轮"
    },
    {
        "slug": "lottiefiles-ai",
        "name": "LottieFiles AI",
        "verdict": "REAL",
        "official_url": "https://lottiefiles.com",
        "url_correct": True,
        "vendor": "LottieFiles (Nattu Adnan & Shafiu Hussain)",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "LottieFiles含AI动画功能(Motion Copilot等)，官网lottiefiles.com"
    },
    {
        "slug": "relume",
        "name": "Relume",
        "verdict": "REAL",
        "official_url": "https://relume.io",
        "url_correct": True,
        "vendor": "Relume",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI网站结构/设计系统生成工具，官网relume.io"
    },
    {
        "slug": "relevance-ai",
        "name": "Relevance AI",
        "verdict": "REAL",
        "official_url": "https://relevanceai.com",
        "url_correct": True,
        "vendor": "Relevance AI",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI应用开发/智能体平台，官网relevanceai.com"
    },
    {
        "slug": "alexa-plus",
        "name": "Alexa Plus",
        "verdict": "REAL",
        "official_url": "https://www.amazon.com/alexa-plus",
        "url_correct": True,
        "vendor": "Amazon",
        "desc_issue": "订阅价记录为$5.99/月起，实际标准版为$19.99/月（Prime会员免费）；其余功能描述准确",
        "confidence": "high",
        "evidence": "亚马逊Alexa+官方页面确认其为生成式AI语音助手"
    },
    {
        "slug": "d-id",
        "name": "D-ID",
        "verdict": "REAL",
        "official_url": "https://www.d-id.com",
        "url_correct": True,
        "vendor": "D-ID",
        "desc_issue": None,
        "confidence": "high",
        "evidence": "AI数字人/照片说话视频平台，官网d-id.com"
    }
]

with open(r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\verify_batches\result_09.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Written", len(results), "entries")

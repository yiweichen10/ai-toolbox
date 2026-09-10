# -*- coding: utf-8 -*-
"""入库华为盘古大模型（2026-09-10，联网核实版）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from data_store import save_tool

TODAY = "2026-09-10"

tool = {
    "name": "盘古大模型",
    "slug": "pangu",
    "emoji": "🏔",
    "color": "#C7000B",
    "description": "想用国产全栈自主可控的大模型？华为盘古大模型提供 505B 开源 MoE 旗舰（openPangu-2.0-Pro）、512K 超长上下文与昇腾原生优化，开发者可免费下载权重，或经华为云 MaaS 按 Token 计费调用，企业还能私有化部署行业模型。",
    "category": "AI开发",
    "tags": ["大语言模型", "开源模型", "华为", "昇腾", "企业AI"],
    "rating": "⭐ 4.2",
    "visits": "新上架",
    "badge": {"type": "new", "text": "NEW"},
    "url": "https://pangu.huaweicloud.com",
    "price": "开源权重免费（openPangu-2.0-Pro 可商用下载）；华为云 MaaS 按 Token 计费（openPangu-2.0-Pro 约 3.2 元/百万输入、14.5 元/百万输出，32K 以上请求另档）；企业版盘古大脑目录价约 70 万元/年起，以官网为准",
    "platform": "Web/API/开源/私有化部署",
    "pros": [
        "全栈自主：昇腾芯片 + MindSpore + 鸿蒙端到端自研，数据安全可控",
        "openPangu-2.0-Pro（505B/激活18B）权重与推理代码已开源，可商用下载",
        "512K 超长上下文，长文档与复杂 Agent 任务友好",
        "昇腾原生优化，单卡推理吞吐率可达业界主流开源模型约 2 倍",
        "华为云 MaaS 提供在线体验与 API，企业可私有化部署"
    ],
    "cons": [
        "无面向个人的免费聊天入口，个人用户上手门槛较高",
        "生态与教程资源不及 DeepSeek / 通义千问等主流开源模型",
        "MaaS 在线体验目前仅支持部分区域（如西南-贵阳一）",
        "开源早期曾因与通义千问参数结构相似引发讨论，官方已声明遵循开源许可"
    ],
    "features": [
        "openPangu-2.0-Pro：总参数 505B / 激活 18B，512K 上下文，MoE 架构（2026.06 发布，07.31 开源）",
        "openPangu-2.0-Flash：总参数 92B / 激活 6B，轻量化部署（2026.06 发布）",
        "昇腾原生训练与推理，DSA+SWA 独立分层混合架构",
        "鸿蒙 Agent 专项优化，系统级智能体'小艺Claw'已接入",
        "华为云 MaaS 在线推理与 API 调用（按 Token 计费）",
        "行业模型矩阵：矿山、气象、药物研发、政务、盘古大脑对话系统等"
    ],
    "related": ["deepseek", "qwen-chat", "wenxin-yiyan", "zhipu-chatglm", "kimi"],
    "faq": [
        {
            "q": "盘古大模型是免费的吗？",
            "a": "分两块：开源侧，openPangu-2.0-Pro 的模型权重、基础推理代码及技术报告已于 2026 年 7 月 31 日开源上线，可免费下载；云端侧，通过华为云 MaaS 调用按 Token 计费（约 3.2 元/百万输入、14.5 元/百万输出，以官网控制台最新价格为准）。企业版'盘古大脑'为订阅制，目录价约 70 万元/年起。"
        },
        {
            "q": "openPangu-2.0-Pro 有多大？能做什么？",
            "a": "总参数量约 505B、每 token 激活约 18B 的 MoE 模型，支持 512K 上下文，训练数据约 34T Tokens。面向长上下文与高复杂度 Agent 任务设计，对昇腾算力与鸿蒙生态做了深度优化，适合企业级智能体、长文档分析与复杂规划场景。"
        },
        {
            "q": "个人开发者怎么体验盘古？",
            "a": "注册华为云账号并实名认证后，在 MaaS（ModelArts Studio）平台开通预置的 openPangu-2.0-Pro 服务即可在线体验或创建 API Key 调用。注意在线体验目前仅支持部分区域（如西南-贵阳一）。有技术能力的团队也可以直接下载开源权重本地部署。"
        },
        {
            "q": "盘古和 DeepSeek、通义千问比怎么样？",
            "a": "盘古的差异点在于全栈自主（昇腾芯片+MindSpore+鸿蒙）与昇腾原生优化，推理吞吐有硬件层面的优势；模型能力上 2.0 系列刚开源，社区生态、微调教程与第三方工具链暂时不如 DeepSeek、通义千问成熟。追求自主可控选盘古，追求生态成熟可先对比再定。"
        }
    ],
    "seo_keywords": [
        "盘古大模型",
        "华为盘古大模型",
        "openPangu 2.0",
        "盘古大模型官网",
        "盘古大模型开源",
        "openPangu-2.0-Pro 下载",
        "盘古大模型 API 价格"
    ],
    "content": (
        "## 盘古大模型是什么？\n\n"
        "盘古大模型是华为 2021 年 4 月发布的大模型品牌，是国内最早的大模型之一。它长期主打'行业大模型'路线——矿山、气象、药物研发、政务这些 To B 场景，而不是做面向个人的聊天产品，所以普通用户对它的感知一直不强。\n\n"
        "2026 年是个转折点。6 月 12 日华为开发者大会（HDC 2026）上，余承东发布了开源盘古 openPangu 2.0 系列；7 月 31 日，旗舰模型 openPangu-2.0-Pro 的权重、推理代码和技术报告正式开源上线。加上昇腾芯片、MindSpore 框架、鸿蒙系统的全栈协同，盘古成了目前'自主可控'标签最重的国产大模型。\n\n"
        "---\n\n"
        "## 核心版本\n\n"
        "### openPangu-2.0-Pro（旗舰）\n"
        "总参数量 505B、每 token 激活 18B 的 MoE 模型，512K 超长上下文，训练数据约 34T Tokens。采用 DSA+SWA 独立分层混合架构，针对昇腾算力原生训练，官方称单卡推理吞吐率可达业界主流开源模型的约 2 倍。2026 年 6 月 30 日起预训练代码、后训练代码、训练算子等 7 大组件陆续开源；7 月 31 日权重与推理代码正式上线。\n\n"
        "### openPangu-2.0-Flash（轻量）\n"
        "总参数 92B、激活仅 6B，大幅降低稀疏配比，面向轻量化部署场景，算力有限的团队更容易跑起来。\n\n"
        "### 行业模型矩阵\n"
        "开源系列之外，华为云仍有成熟的行业模型：盘古大脑对话系统（基础版目录价约 70 万元/年）、气象、矿山、药物研发等垂直模型，走私有化/项目制路线。\n\n"
        "---\n\n"
        "## 价格\n\n"
        "| 用法 | 费用 | 备注 |\n|------|------|------|\n| 开源权重下载 | 免费 | openPangu-2.0-Pro，可商用 |\n| 华为云 MaaS 调用 | 输入约 3.2 元/百万 Token（缓存命中 0.8）、输出约 14.5 元/百万 | ≥32K 请求另档（4.8/1.2/17.6），以控制台为准 |\n| 盘古大脑企业版 | 约 70 万元/年起（基础版目录价） | 专业版/模型订阅更高，需商务咨询 |\n\n"
        "注意 32K 是计费分界：单次请求低于 32K Token 走第一档，达到或超过走第二档。做 RAG 和长文档分析的企业测算成本时要按请求分布算，不能只看均价。\n\n"
        "---\n\n"
        "## 值不值得用？\n\n"
        "**优点：**\n"
        "- 全栈自主可控，数据安全要求高的政企场景几乎绕不开\n"
        "- 505B 开源旗舰权重免费可商用，在当前开源阵营里规格靠前\n"
        "- 512K 长上下文 + Agent 专项优化，跨应用复杂任务表现是官方主打方向\n"
        "- 昇腾硬件亲和度高，已采购昇腾算力的团队推理效率有优势\n\n"
        "**缺点：**\n"
        "- 没有个人免费聊天入口，尝鲜成本比 DeepSeek、文心一言高\n"
        "- 开源时间短，社区微调脚本、量化方案、教程积累还很少\n"
        "- MaaS 在线体验区域受限（目前仅西南-贵阳一等）\n\n"
        "**总体结论：** 政企、信创、需要昇腾算力配套的团队，盘古 2.0 开源后是值得认真评估的选项；个人开发者想先白嫖体验，DeepSeek / 通义千问仍是更低门槛的起点。\n\n"
        "---\n\n"
        "## 使用建议\n\n"
        "1. **先在 MaaS 上开通预置服务试效果**：注册华为云 + 实名认证后在 ModelArts Studio 开通 openPangu-2.0-Pro，跑通 API 再决定是否自部署。\n"
        "2. **本地部署先评估算力**：Pro 版 505B 总参对显存要求高，算力有限先看 92B 的 Flash 版。\n"
        "3. **关注鸿蒙 Agent 生态**：'小艺Claw'已接入 openPangu 2.0 Pro，做鸿蒙端侧智能体的话这是官方推荐底座。\n"
        "4. **价格以官网为准**：MaaS 计费档位和区域支持可能调整，下单前以华为云控制台最新信息为准。\n\n"
        "---\n\n"
        "## 适合谁用？\n\n"
        "**推荐使用：**\n"
        "- 对自主可控/信创有硬性要求的政企与关基行业\n"
        "- 已有昇腾算力、需要配套模型底座的团队\n"
        "- 做鸿蒙生态智能体的开发者\n\n"
        "**不推荐：**\n"
        "- 个人尝鲜用户（没有对话入口，门槛高）\n"
        "- 极度依赖成熟社区生态和第三方工具链的小团队\n\n"
        "*数据来源：华为官方新闻（huawei.com/cn/news/2026/7/openpangu）、华为云 MaaS 帮助中心与社区帖、HDC 2026 公开报道（2026-09-10 核实），以官网为准。*"
    ),
    "published": True,
    "published_date": TODAY,
    "created_date": TODAY,
    "verified_url": "https://pangu.huaweicloud.com",
    "verified_publisher": "华为（Huawei），模型品牌隶属华为云/开源盘古 openPangu",
    "verified_what": "华为大模型品牌，2021.04 首发，长期主打行业大模型；2026.06.12 HDC 发布开源 openPangu 2.0（Pro 505B/激活18B、Flash 92B/激活6B、512K 上下文），2026.07.31 openPangu-2.0-Pro 权重与推理代码及时间报告正式开源上线，小艺Claw 已接入。",
    "verified_price": "开源权重免费可商用；华为云 MaaS 按 Token 计费（社区帖 2026-09 前后：openPangu-2.0-Pro 输入 3.2 元/百万、缓存命中 0.8、输出 14.5 元/百万；≥32K 另档 4.8/1.2/17.6）；盘古大脑企业版基础版目录价约 70 万元/年。",
    "verified_platform": ["Web", "API", "开源模型", "私有化部署"],
    "last_verified": TODAY,
    "confidence": "high",
    "conflict": False,
    "verified_features": [
        "openPangu-2.0-Pro：总参数 505B / 激活 18B，512K 上下文，MoE 架构（2026.06 发布，07.31 开源）",
        "openPangu-2.0-Flash：总参数 92B / 激活 6B，轻量化部署（2026.06 发布）",
        "昇腾原生训练与推理，DSA+SWA 独立分层混合架构",
        "鸿蒙 Agent 专项优化，'小艺Claw'已接入",
        "华为云 MaaS 在线推理与 API 调用",
        "行业模型矩阵（矿山/气象/药物/政务/盘古大脑）"
    ],
    "verified_description": None,  # 稍后填充
    "content_verified": True,
    "price_verified": True,
    "verified_pros": None,
    "verified_cons": None,
    "verified_faq": None,
    "verified_tags": ["大语言模型", "开源模型", "华为", "昇腾", "企业AI"],
    "verified_category": "AI开发",
    "source_urls": [
        "https://www.huawei.com/cn/news/2026/7/openpangu",
        "https://pangu.huaweicloud.com",
        "https://support.huaweicloud.com/bestpractice-maas/bestpractice_maas_0021_02.html",
        "https://bbs.huaweicloud.com/blogs/99aa3a8cb069468eb2d7ec7ffc466e4b",
        "https://baike.baidu.com/item/openPangu%202.0/68593064",
        "https://www.nfnews.com/content/VoQVOmQLy5.html"
    ],
    "verify_notes": "2026-09-10 联网核实：openPangu 2.0 于 2026.06.12 HDC 发布（Pro 505B/18B、Flash 92B/6B、512K），07.31 Pro 权重开源；MaaS 计费数字来自华为云社区代理商帖（非官网价目页），已在 price 标注'以官网为准'；MaaS 在线体验区域限制来自官方帮助中心（西南-贵阳一）。2025.07 曾有与通义千问结构相似性争议，官方（诺亚方舟实验室）已声明遵循开源许可。"
}

tool["verified_description"] = tool["description"]
tool["verified_pros"] = tool["pros"]
tool["verified_cons"] = tool["cons"]
tool["verified_faq"] = tool["faq"]

save_tool(tool)
print("OK 已写入 data/tools/pangu.json")

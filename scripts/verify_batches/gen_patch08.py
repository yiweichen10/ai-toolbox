# -*- coding: utf-8 -*-
import json

patches = [
    {
        "slug": "jamie-ai",
        "description": "Jamie 是德国公司出品的隐私优先 AI 会议纪要工具，能不邀请机器人地为线上/线下会议自动生成结构化笔记、转录文本与待办事项，支持 100+ 语言。",
        "content": "Jamie 是一款注重隐私的 AI 会议记录助手。会议结束后它会自动生成结构化的会议纪要、完整转录和行动项，支持 100 多种语言，线上、线下会议均可使用，且无需在会议中邀请机器人。作为德国公司，Jamie 遵循 GDPR：会议音频在转写后会被删除，数据采用 TLS 1.2 传输加密与 AES-256 存储加密，且绝不会用于训练模型。它还能与 Notion、Google Docs、OneNote、HubSpot 等工具同步笔记。免费版每月 10 次会议额度，付费版 Plus/Pro/Team 按月订阅。"
    },
    {
        "slug": "glass-health",
        "description": "Glass Health 是面向临床医生的 AI 临床决策支持与病历撰写平台，可基于循证医学生成鉴别诊断列表与诊疗建议。",
        "content": "Glass Health 由医学博士 Dereck Paul 创立，是一款面向医生、护士从业者等临床人员的 AI 临床决策支持与病历撰写工具。输入患者症状、体征和病史，它会生成按可能性排序的鉴别诊断列表，并给出下一步检查与诊疗参考，所有回答均基于同行评议的医学文献与临床指南。平台通过 HIPAA 合规基础设施保障患者隐私，已服务全球 170+ 国家、12 万+ 临床人员。需强调：它是辅助工具，不能替代医生的最终临床判断。"
    },
    {
        "slug": "cocounsel",
        "description": "CoCounsel 是 Thomson Reuters（汤森路透）推出的 AI 法律助手，基于 Westlaw 等权威法律数据库，为律师提供法律研究、文档审查与合同分析。",
        "content": "CoCounsel 是 Thomson Reuters（汤森路透）推出的 AI 法律助手，并非 Clio 的产品。它基于 Westlaw 等权威法律数据库构建，能够帮助律师进行法律研究与检索、复杂法律文件审查、合同条款提取与判例分析。CoCounsel 面向律师、法务等法律专业人士，目标是减少检索与研究耗时，但仍需使用者对输出结果进行专业判断。注意：原批次将厂商误标为 Clio（一家律所管理软件公司），实际归属应为 Thomson Reuters；正确官网为 cocounsel.com。"
    },
    {
        "slug": "pmb",
        "description": "PMB 是面向 AI 编程代理的本地优先记忆工具，通过 MCP 协议为 Claude Code、Cursor、Codex、Zed 等提供跨会话的持久化项目记忆。",
        "content": "PMB（Personal Memory Brain）是一款开源的本地优先记忆工具，专为 AI 编程代理设计。它通过 MCP 协议接入 Claude Code、Cursor、Codex、Zed 等代理，将项目决策、经验教训、目标与进展存储在本地磁盘的 SQLite 与 LanceDB 中，完全离线、无需云端、无需 API 密钥，读取路径不调用大模型。它提供约 29 个 MCP 工具，自动在代理思考前注入相关记忆，并追踪哪些记忆真正被采用。注意：原批次误将其描述为“项目管理助手”，实际是编程代理的记忆层，而非任务/进度管理工具。"
    },
    {
        "slug": "blop",
        "description": "Blop 是面向工程团队的 UX/UI 优化与 QA 测试代理，能把自然语言描述的用户流程转成 Playwright 浏览器测试并在 CI 中运行。",
        "content": "Blop 是一款 QA 测试代理（被称为“UX/UI 优化的 Cursor”），专为使用编程代理交付软件的工程团队打造。你用自然语言描述一段用户流程（如下单、注册），Blop 会将其转成基于 Playwright 的浏览器测试，以代码形式保存在 GitHub 仓库中，并在 GitHub Actions 里运行，把结果与失败聚类直接回传到对应的 Pull Request。它还支持将测试排程为生产环境的周期性探测（synthetic monitoring），并可借 Agent 自动修复失败的测试。注意：原批次误将其描述为“社媒平面设计助手”，实际是工程侧的 UI 测试/优化代理，而非设计出图工具。"
    },
    {
        "slug": "video-os",
        "description": "VideoOS 是 Jupitrr AI 推出的一站式视频工作流平台，覆盖选题研究、脚本撰写、剪辑与多平台发布。",
        "content": "VideoOS 是 Jupitrr AI 旗下的一站式视频工作流产品，帮助创作者与企业从选题研究、脚本撰写到剪辑、发布在一个平台内完成。它提供 AI 视频编辑器（自动加字幕、B-roll、转场）、提词器、音频转视频、内容日历、多平台发布与视频数据分析等功能，已服务 20 万+ 企业与创作者。注意：原批次使用的 videoos.net 并非该产品官网，真实官网为 jupitrr.com；同时原描述偏向“视频内容智能分析”，实际更接近于面向社媒的端到端视频制作与发布工作流。"
    },
    {
        "slug": "octarine",
        "description": "Octarine 是一款本地优先的 Markdown / 个人知识管理（PKM）笔记应用，用于结构化地记录与管理个人知识。",
        "content": "Octarine 是一款本地优先的 Markdown 笔记 / 个人知识管理（PKM）应用，强调数据本地存储与隐私，帮助用户以结构化方式记录、链接与检索笔记。它以纯文本 Markdown 为核心，适合长期积累与整理个人知识库。注意：原批次误将其描述为“面向营销人员的 AI 创意内容生成平台（社媒文案、广告、品牌故事）”，实际 Octarine 是知识笔记工具，并非营销内容工厂，请勿按营销场景对外表述。"
    },
    {
        "slug": "unitree-gd01",
        "description": "Unitree GD01 是宇树科技推出的载人变形机甲（可乘坐的变形机器人），并非四足教育机器人。",
        "content": "Unitree GD01 是宇树科技（Unitree Robotics）推出的载人变形机甲——一种可由人员乘坐、具备变形能力的机器人平台，定位偏向可乘坐的消费/展示级机器人，而非科研用四足机器狗。原批次将其描述为“支持 Python/ROS 编程的四足机器人教育平台”存在事实错误：GD01 并非四足形态，也不以高校机器人竞赛教育为主要定位。具体价格与规格请以宇树官方（unitree.com）公布为准。"
    }
]

with open("patch_08.json", "w", encoding="utf-8") as f:
    json.dump(patches, f, ensure_ascii=False, indent=2)

print("Wrote", len(patches), "patches to patch_08.json")
for p in patches:
    print("-", p["slug"], "| content chars:", len(p["content"]))

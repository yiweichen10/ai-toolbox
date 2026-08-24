# -*- coding: utf-8 -*-
"""应用 12 个被闸门拦截工具的核查结果（7 复核修正 + 5 占位补全）→ tools.json"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = __file__.rsplit('\\', 2)[0]
P = BASE + '/data/tools.json'

data = json.load(open(P, encoding='utf-8'))

# ── 7 个复核工具的字段修正 ──
fix7 = {
    'deepl-write': {
        'price': '免费版可用（未登录单次约 1,500 字符）；付费随 DeepL Pro 订阅：Individual 约 8.74 美元/月（年付）、Team 约 28.74 美元/月（年付）、Business 约 57.49 美元/月（年付）；另有独立 Write 附加组件约 7.49 美元/用户/月',
        'description': 'DeepL Write 是 DeepL 旗下的 AI 写作润色工具，随 DeepL Pro 订阅附带使用，另有可单独购买的 Write 附加组件；免费版有字符额度限制。',
        'confidence': 'high',
        'source_urls': ['https://www.deepl.com/pricing', 'https://support.deepl.com/hc/zh-cn/articles/9851524013468'],
    },
    'baichuan-3': {
        'price': '暂未公开（以官网为准）',
        'description': '百川3（Baichuan 3）是百川智能于 2024 年 1 月 29 日发布的超千亿参数大语言模型，主打中文理解、长文本与多轮对话；当前官网主推 Baichuan4 与开源 Baichuan-M 系列，Baichuan3-Turbo 仍提供 API。',
        'confidence': 'high',
        'source_urls': ['https://www.baichuan-ai.com/', 'https://tech.chinadaily.com.cn/a/202401/29/WS65b767a6a310af3247ffdc61.html'],
    },
    'unitree-h1': {
        'price': '官方未公开标价；据第三方渠道，H1 约 65 万元人民币，H1-2 约 9.99-12.89 万美元，以官方销售报价为准',
        'confidence': 'high',
        'source_urls': ['https://m.unitree.com/cn/h1/', 'https://support.unitree.com/home/', 'https://www.robotsasia.com/Unitree-H1-and-H1-2.htm'],
    },
    'uipath': {
        'price': '社区版免费（最多 3 个 attended 机器人）；Automation Cloud Basic 约 25 美元/月起（欧洲区）；Standard/Enterprise 需联系销售；Attended 机器人约 420 美元/用户/年、Unattended 约 1,680 美元/机器人/年（合作伙伴指导价，非公开牌价）',
        'confidence': 'high',
        'source_urls': ['https://www.uipath.com/pricing', 'https://automationatlas.io/answers/uipath-pricing-explained-2026'],
    },
    'dagster': {
        'price': '开源核心免费（Apache 2.0）；Dagster+ Solo 120 美元/月（含 7.5k credits）、Starter 1,200 美元/月（含 30k credits）、Enterprise 需联系销售',
        'confidence': 'high',
        'source_urls': ['https://dagster.io/pricing', 'https://dagster.io/prefect'],
    },
    'softr-ai': {
        'price': 'Free 0 美元；Basic 19 美元/月（年付，月付 25）；Pro 99 美元/月（年付，月付 119）；Business 329 美元/月（年付，月付 395）；Enterprise 定制',
        'confidence': 'high',
        'source_urls': ['https://docs.softr.io/workspace-and-billing/pricing-and-plans', 'https://www.softr.io/ai-app-generator'],
    },
    'kubiya-ai': {
        'price': '暂未公开（联系销售获取报价）',
        'confidence': 'medium',
        'source_urls': ['https://kubiya.ai', 'https://www.businesswire.com/news/home/20241113350704/en/Kubiya-Introduces-Captain-Kubernetes-Industry%E2%80%99s-First-AI-Teammate-for-Autonomous-Kubernetes-Operations'],
    },
}

# ── 5 个占位工具的补全（content + faq）──
fill5 = {
    'bittensor': {
        'content': '## 是什么\nBittensor 是一个去中心化的机器学习网络，把全球的模型、算力和数据贡献者用区块链经济激励连接起来，形成一个开放的「AI 智能市场」。不同于由单一公司垄断的 AI，Bittensor 让任何人都能参与提供 AI 服务，并按贡献质量获得 TAO 代币奖励。\n\n## 核心特点\n- 子网体系：网络由多个子网组成，每个子网专注一类 AI 任务，如文本生成、图像生成、翻译、云存储等，各自有独立的激励机制。\n- 矿工与验证者分工：矿工负责运行 AI 模型、产出结果；验证者负责给矿工打分，决定谁值得奖励，形成「优胜劣汰」的质量循环。\n- 代币 TAO：原生代币，最大供应量 2100 万枚，类似比特币；最小单位 RAO，1 TAO 等于 10 亿 RAO，兼具奖励、质押与治理功能。\n\n## 技术原理\nBittensor 采用「智能证明」思路：节点不靠算力挖矿或抵押币量取胜，而是靠输出真正有用的 AI 结果、被验证者认可来获得 TAO。Yuma 共识把验证者的排名聚合起来，抵押越多的验证者话语权越大，但必须与其他验证者达成一致才能拿到奖励，从而抑制作弊。\n\n## 价格与收费\nTAO 为自由流通的代币，价格随市场波动，具体行情以交易所实时报价为准；网络对参与者按质押与贡献发放排放奖励，无固定服务费，以官网为准。\n\n## 适用人群\n适合想贡献模型或算力获利的 AI 开发者与矿工，希望通过质押 TAO 获取被动收益的投资者，以及需要按效果付费获取 AI 服务的企业。\n数据以官网为准。',
        'faq': [
            {'q': 'Bittensor 的 TAO 代币有什么用？', 'a': 'TAO 是网络的原生代币，最大供应 2100 万枚，用于奖励矿工和验证者，同时可用于质押、注册和治理投票。'},
            {'q': 'Bittensor 里的矿工和验证者是什么？', 'a': '矿工运行 AI 模型并提供服务，验证者给矿工的输出打分排名，决定谁值得获得 TAO 奖励，共同构成质量循环。'},
            {'q': '什么是子网（Subnet）？', 'a': '子网是 Bittensor 内专注特定 AI 任务的迷你网络，如文本生成、图像生成、翻译等，各自有独立的激励与验证机制。'},
            {'q': 'Bittensor 和 OpenAI 这类中心化 AI 有什么区别？', 'a': '中心化公司靠固定薪资雇佣团队做 AI，Bittensor 靠代币激励让全球任何人按效果竞争，贡献越有用回报越高。'},
            {'q': 'TAO 的减半机制是怎样的？', 'a': '与比特币类似，TAO 每 1050 万个区块减半一次，区块约 12 秒一个，供应量逐渐递减。'},
            {'q': '不懂 AI 也能参与吗？', 'a': '可以，你可以购买并质押 TAO 给验证者，作为委托者分享其奖励，无需技术背景。'},
            {'q': 'Bittensor 是谁创立的？', 'a': '由前 Google AI 工程师 Jacob Steeves 与 Ala Shaabana 于 2021 年通过 Opentensor Foundation 推出。'},
        ],
        'source_urls': ['https://bittensor.com', 'https://discoverbittensor.com/glossary'],
    },
    'render-network': {
        'content': '## 是什么\nRender Network 是世界上首个去中心化 GPU 渲染与计算平台，由渲染软件公司 OTOY 推出。它把全球闲置的 GPU 算力汇集起来，让创作者按需租用，完成 3D 渲染、视觉特效和生成式 AI 计算，价格远低于传统云渲染。\n\n## 核心特点\n- 支持主流渲染器：兼容 OctaneRender、Redshift、Blender Cycles，以及 Runway、Black Forest Labs、Luma、Stability AI 等生成式 AI 工具。\n- 按优先级分档计价：Tier 2（优先档）100 OBh/RENDER，Tier 3（经济档）200 OBh/RENDER，可灵活平衡速度与成本。\n- 销毁型通缩机制（BME）：用户支付的 RENDER 会被销毁，把网络使用量与代币供应直接挂钩。\n- 代币 RENDER：最大供应量约 644.2 万枚，2023 年从以太坊的 RNDR 迁移至 Solana 的 RENDER。\n\n## 技术原理\n创作者把场景文件（如 ORBX 格式）上传到 Render 平台，设置分辨率、采样数、帧范围等参数；节点运营商（闲置 GPU 提供者）接单并完成渲染，结果上传云端存储。任务按 OctaneBench 性能分档分配给节点，每笔任务收取 5% 协议费用于维持网络，付款以 RENDER 计价并销毁，形成「使用越多、供应越紧」的平衡。\n\n## 价格与收费\n不设最低消费与预付费，按需计价；Tier 3 经济档为 200 OBh/RENDER，Tier 2 优先档为 100 OBh/RENDER，另收 5% 协议费。相比传统云渲染通常可显著节省成本，具体以官网报价为准。\n\n## 适用人群\n适合电影 VFX、3D 动画、游戏资产渲染的创作者与工作室，以及需要低成本 GPU 做 AI 推理或训练的开发者。\n数据以官网为准。',
        'faq': [
            {'q': 'Render 和传统云渲染比便宜多少？', 'a': 'Render 利用闲置 GPU，通常能显著降低成本，部分案例渲染费用可比 AWS 低一个数量级，具体取决于档位与供需。'},
            {'q': 'RENDER 和 RNDR 是什么关系？', 'a': 'RNDR 是原以太坊代币，2023 年迁移到 Solana 并更名为 RENDER，最大供应量约 644.2 万枚。'},
            {'q': 'Render 支持哪些渲染器？', 'a': '支持 OctaneRender、Redshift、Blender Cycles，以及 Runway、Black Forest Labs、Luma、Stability AI 等生成式 AI 工具。'},
            {'q': 'Tier 2 和 Tier 3 有什么区别？', 'a': 'Tier 2 是优先档，速度更快、分配更强节点，定价 100 OBh/RENDER；Tier 3 是经济档，价格更低但无队列优先，定价 200 OBh/RENDER。'},
            {'q': '用户支付的 RENDER 去哪了？', 'a': '采用销毁型机制（BME），支付的 RENDER 会被销毁，把网络使用量与代币供应直接挂钩，另收 5% 协议费。'},
            {'q': '如何成为节点运营商？', 'a': '拥有闲置 GPU 即可注册为节点运营商接单渲染，按完成的 OctaneBench 小时数获得 RENDER 奖励。'},
        ],
        'source_urls': ['https://rendernetwork.com', 'https://messari.co/4qYLfOw'],
    },
    'akash-network': {
        'content': '## 是什么\nAkash Network 是一个去中心化算力市场，被称为「算力界的 Airbnb」。它把全球闲置的 CPU、GPU 和存储资源汇集起来，通过区块链撮合供需，让用户以远低于 AWS、Google Cloud 的价格租用计算资源。\n\n## 核心特点\n- 反向拍卖定价：租户发布所需资源（GPU 型号、地区、最高价），供应商实时竞价，市场价趋向硬件成本加薄利，而非大厂高溢价。\n- 显著成本优势：官方称可比传统云节省最高约 80%，例如 H200 在 Akash 约 1.40 美元/小时，而 AWS 约 4.33 美元/小时。\n- 标准容器部署：工作负载跑在标准 Docker 容器内，绝大多数现有软件无需修改即可部署。\n- 代币 AKT：用于支付、治理投票与质押安全，网络费用部分销毁或进入社区基金。\n\n## 技术原理\nAkash 基于 Cosmos SDK 构建，区块链负责撮合、结算与执行租赁协议，实际计算跑在真实硬件上。租户广播部署清单并设最高心理价位，供应商竞标，租户在几秒内接受最优出价形成「租约」，资源按实际用量计费结算，链上记录消除了计费纠纷。\n\n## 价格与收费\n无隐藏费用，按资源实际用量计价，价格随供需浮动。官网示例 H200 约 1.40 美元/小时，整体可比主流云便宜约 80%，具体以官网实时报价为准。\n\n## 适用人群\n适合需要低成本 GPU 做 AI 推理、大模型训练、生成式应用部署的团队，也适合有闲置服务器想出租变现的个人或数据中心。\n数据以官网为准。',
        'faq': [
            {'q': 'Akash 为什么被称为「算力界 Airbnb」？', 'a': '它像 Airbnb 汇集闲置房源一样，把全球闲置的 CPU、GPU 和存储汇集起来，撮合算力的供给方与需求方。'},
            {'q': 'Akash 能比 AWS 便宜多少？', 'a': '官方称可比传统云节省最高约 80%，例如 H200 在 Akash 约 1.40 美元/小时，而 AWS 约 4.33 美元/小时。'},
            {'q': 'Akash 的定价机制是什么？', 'a': '采用反向拍卖，租户发布所需资源与最高心理价位，供应商竞价，租户接受最优出价，价格随供需实时浮动。'},
            {'q': 'AKT 代币有什么用？', 'a': 'AKT 用于支付算力费用、参与治理投票和质押保障网络安全，部分网络费用会被销毁或进入社区基金。'},
            {'q': '现有软件部署到 Akash 需要改造吗？', 'a': '通常不需要，工作负载跑在标准 Docker 容器内，绝大多数现有容器化软件可直接部署。'},
            {'q': 'Akash 基于什么技术构建？', 'a': '基于 Cosmos SDK 构建，区块链负责撮合、结算与执行租赁协议，实际计算跑在真实硬件上。'},
        ],
        'source_urls': ['https://akash.network', 'https://akt.fyi/docs'],
    },
    'elizaos': {
        'content': '## 是什么\nElizaOS 是一个开源的 TypeScript AI Agent 框架，前身是 ai16z 生态，被誉为「Agent 的 Linux」。它让开发者用几行配置就能创建能聊天、能上链、能运营社交账号的自主 AI 智能体。\n\n## 核心特点\n- 角色文件定义人格：通过 character file（TypeScript/JSON）配置智能体的名字、背景、知识领域与说话风格。\n- 90+ 官方插件：覆盖 Discord、Telegram、Twitter/X 等社交平台，以及 Solana、Ethereum、Base 等区块链，还有 OpenAI、Anthropic 等模型接入。\n- 持久记忆系统：智能体能记住对话历史、关系与知识，进行长期连贯互动。\n- 多智能体协作：可编排多个分工智能体（研究、交易、运营）共享记忆与消息传递。\n\n## 技术原理\n每个智能体由 Agent Runtime 统一调度，Runtime 管理状态、事件与记忆持久层；插件为智能体扩展动作能力，Provider 为 LLM 组装上下文，Evaluator 在对话后提取要点更新知识库。智能体可接多个客户端适配器，实现跨平台收发消息。\n\n## 价格与收费\nElizaOS 本身为开源免费框架，核心代码在 GitHub 开放；托管平台 Eliza Cloud 及代币 $elizaOS（2025 年由 $ai16z 迁移而来）的付费细节以官网为准。\n\n## 适用人群\n适合想快速构建 Web3 智能体、DeFi 客服机器人、链上监控员、游戏 NPC 或 DAO 助手的开发者，尤其面向既有区块链又有 AI 需求的团队。\n数据以官网为准。',
        'faq': [
            {'q': 'ElizaOS 和 LangChain 有什么区别？', 'a': 'LangChain 是通用 LLM 应用框架，ElizaOS 则从第一天起面向 Web3，内置链上读写、社交平台接入和自主智能体能力，开箱即用。'},
            {'q': 'ElizaOS 的智能体如何定义人格？', 'a': '通过 character file（TypeScript/JSON）配置智能体的名字、背景、知识领域、说话风格与行为约束。'},
            {'q': 'ElizaOS 支持哪些平台？', 'a': '通过 90+ 官方插件支持 Discord、Telegram、Twitter/X 等社交平台，以及 Solana、Ethereum、Base 等区块链和 OpenAI、Anthropic 等模型。'},
            {'q': 'ai16z 和 ElizaOS 是什么关系？', 'a': '项目最初以 ai16z 名义于 2024 年 10 月推出，后为避免与风投 a16z 的品牌冲突更名为 ElizaOS，2025 年完成从 $ai16z 到 $elizaOS 的代币迁移。'},
            {'q': 'ElizaOS 是免费的吗？', 'a': '框架本身开源免费，核心代码托管在 GitHub；托管平台与代币相关的付费细节以官网为准。'},
            {'q': '一个智能体只有一套记忆吗？', 'a': '不是，记忆分多层，包括会话内对话历史、RAG 索引的知识库和跨会话的结构化关系记忆。'},
            {'q': '需要多强的技术背景？', 'a': '官方强调「三条命令创建第一个智能体」，适合有基础 Node.js/Bun 使用经验的开发者快速上手。'},
        ],
        'source_urls': ['https://elizaos.ai', 'http://iq.wiki/wiki/eliza-ai'],
    },
    'aixbt': {
        'content': '## 是什么\nAIXBT 是一个 AI 市场情报 Agent，全天候监控加密社交媒体、链上数据和市场趋势，把海量噪音过滤成可读的市场叙事与热度信号，通过 X 账号 @aixbt_agent 和 AIXBT Terminal 输出。\n\n## 核心特点\n- 实时情报流：持续扫描 400+ 个加密 KOL 账号，以及 Telegram、CoinGecko 与链上日志，识别新兴趋势与叙事。\n- 代币门控终端：完整 AIXBT Terminal 需持有 60 万 AIXBT（约 36 万美元）或按月付费约 200 美元订阅。\n- 动量评分与聚类分析：把 X 账号按社交图谱聚类，测量不同独立社区是否「不约而同」开始讨论同一项目，生成 momentum score。\n- Indigo 升级：集成 CoinGecko、DeFiLlama 等结构化数据源，强化巨鲸钱包追踪与代币估值分析。\n\n## 技术原理\nAIXBT 建立在 Virtuals Protocol 上，部署于 Base 链（以太坊 L2），由化名创建者 rxbt 打造。输入端接入大量 KOL 动态与市场数据，语言模型对信息排序、识别正在升温的故事，自动生成市场情报帖。需要强调的是：它产出的是「注意力与评论」，而不是替你自动下单的交易机器人。\n\n## 价格与收费\n公开帖子免费；深度终端需持有 60 万 AIXBT 或支付约 200 美元/月订阅费。AIXBT 代币总供应 10 亿枚，具体价格随市场波动，以官网为准。\n\n## 适用人群\n适合想用机器速度捕捉叙事热度、监控巨鲸动向与市场情绪的加密交易者、研究者与社区运营者。\n数据以官网为准。',
        'faq': [
            {'q': 'AIXBT 会自动帮我下单交易吗？', 'a': '不会，AIXBT 是市场情报 Agent，产出的是对叙事热度与市场情绪的解读，不是替你执行的交易机器人。'},
            {'q': 'AIXBT 建立在什么基础设施上？', 'a': '建立在 Virtuals Protocol 上，部署于 Base 链（以太坊 L2），由化名创建者 rxbt 打造。'},
            {'q': 'AIXBT Terminal 怎么收费？', 'a': '完整终端需持有 60 万 AIXBT（约 36 万美元），或用约 200 美元/月的订阅，公开帖子免费。'},
            {'q': 'AIXBT 的数据从哪里来？', 'a': '持续监控 400+ 个加密 KOL 账号，以及 Telegram、CoinGecko 与链上日志，经 Indigo 升级后还整合了 DeFiLlama 等数据。'},
            {'q': 'AIXBT 代币总量多少？', 'a': 'AIXBT 为 ERC-20 代币，总供应量固定为 10 亿枚，主要用于门控终端访问与治理。'},
            {'q': '什么是动量评分（Momentum Score）？', 'a': '它把 X 账号按社交图谱聚类，测量多个独立社区是否同时开始讨论同一项目，用于捕捉情绪升温的早期信号。'},
        ],
        'source_urls': ['https://aixbt.tech', 'https://docs.aixbt.tech/introduction/core-concepts'],
    },
}

# 写回
changed = []
for t in data:
    slug = t.get('slug')
    if slug in fix7:
        for k, v in fix7[slug].items():
            t[k] = v
        t['content_verified'] = True
        t['last_verified'] = '2026-08-16'
        changed.append(slug)
    if slug in fill5:
        t['content'] = fill5[slug]['content']
        t['faq'] = fill5[slug]['faq']
        if 'source_urls' in fill5[slug]:
            t['source_urls'] = fill5[slug]['source_urls']
        t['content_verified'] = True
        t['last_verified'] = '2026-08-16'
        if not t.get('created_date'):
            t['created_date'] = '2026-08-16'
        changed.append(slug)

# content 精修（unitree 自由度 + 价格；baichuan "最新"表述）
for t in data:
    if t.get('slug') == 'unitree-h1':
        c = t.get('content') or ''
        c = c.replace('**34个自由度关节模组**', '**19 个自由度关节模组（H1-2 为 27 个）**')
        c = c.replace('价格暂未公开，据业内渠道反馈，单台售价在十几万到二十万人民币区间，属于B端和科研预算范畴，个人用户门槛较高。',
                      '价格官方未标价，据第三方渠道 H1 约 65 万元人民币、H1-2 约 9.99-12.89 万美元，属于 B 端和科研预算范畴，以官方销售报价为准。')
        t['content'] = c
    if t.get('slug') == 'baichuan-3':
        c = t.get('content') or ''
        c = c.replace('百川3是百川智能最新推出的大语言模型', '百川3是百川智能于 2024 年 1 月 29 日推出的大语言模型（当前官网主推 Baichuan4 与开源 Baichuan-M 系列，百川3已非主力，Baichuan3-Turbo 仍提供 API）')
        t['content'] = c

json.dump(data, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# 校验
data2 = json.load(open(P, encoding='utf-8'))
by = {x['slug']: x for x in data2}
print('写入完成，共处理', len(changed), '个工具:', changed)
for s in ['unitree-h1', 'baichuan-3']:
    print(' 校验', s, 'content含"19 个自由度":', '19 个自由度' in by[s]['content'], '| 含"2024 年 1 月 29 日":', '2024 年 1 月 29 日' in by[s]['content'])
# 最终闸门统计
unpub = [x for x in data2 if not x.get('published', True)]
auto = [x for x in unpub if x.get('content_verified') is True and not x.get('conflict')]
blocked = [x for x in unpub if x.get('content_verified') is not True]
print('处理后: 可自动排队发布=', len(auto), '| 仍被拦截=', len(blocked), [x['slug'] for x in blocked])
print('5个占位content长度:', {s: len(by[s]['content']) for s in fill5})

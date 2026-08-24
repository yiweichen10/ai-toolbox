# 全量核实问题 Master 进度表

> 生成时间：2026-07-30 | 数据源：49 个 result_bXX.json 聚合（419 工具 100% 核验）
> 本表仅整理收集；P0 已于 2026-07-30 执行修复并上线（见下）。

## 总览

- 已核验工具：**419 / 419**（100%）
- 已修 URL 并上线：**36 个**（commit 已推送，线上生效）
- **P0 已修复并上线**：**24 个**（2026-07-30，Agent 联网写正确 content/price/platform + 校验落地；windsurf 额外修正了上一轮错改的 URL devin.ai→windsurf.com）。huoshan-writing 的 URL 多处 404 无定论，仅改 platform、URL 留人工复核。
- 仍有问题的工具（去重后）：**308 个**（332 减去已修 24）
  - 其中 URL 已修但 content/price 仍错的：剩余未修批次见 P2/P3

## 阶段进度表

| 阶段 | 说明 | 问题数 | 建议动作 | 状态 |
|------|------|--------|----------|------|
| P0_url_fixed_content_pending | P0 已修URL但内容/价格仍错（上次遗留，最高优先） | 24 | 派 Agent 联网写出正确 content/description/price，校验后落地（上次收尾遗留） | ✅ 已修复上线（2026-07-30，commit a96348a67） |
| P1_url_review | P1 URL 收尾（无正确官网，待下架/概念页决策） | 5 | 人工决定：下架 或 改写为「概念/孵化中」页 | ⏸ 待指令 |
| P2_content_highrisk | P2 内容高危重写（整页/大段张冠李戴） | 110 | 派 Agent 联网写出正确 content+description，校验后落地 | ⏸ 待指令 |
| P3_price_fix | P3 价格编造修复（price 字段） | 101 | 派 Agent 联网核实正确定价（人民币/美元），批量修正 price | ⏸ 待指令 |
| P4_other_field | P4 其余字段幻觉（platform/description 等） | 9 | 派 Agent 核实 platform/description 等字段后修正 | ⏸ 待指令 |
| P5_conflict | P5 冲突项人工裁定 | 21 | 人工逐条裁定：保留 / 改写 / 下架 | ⏸ 待指令 |
| P6_lowconf | P6 低/中置信复核 | 62 | 人工或 Agent 二次复核，确认无误或降级处理 | ⏸ 待指令 |

## P0 已修URL但内容/价格仍错（上次遗留，最高优先）（24 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | agent-skills | content,price | medium | ✅ | URL 冲突：agentskills.ai 实为 Justin Brooke 的商业“预置 AI Agent”服务（卖营销自动化代理），并非 Anthropic |
| 2 | anyscenegen | content,price | high | ✅ | 严重问题：①官网 URL 错误，anyscenegen.ai 无法访问，真实官网为 anyscenegen.intime3d.com（及 GitHub）。②正文 |
| 3 | asi-one | platform,price | medium | ✅ | 官网正确域名为 asi1.ai（数字 1，而非 asi-one.ai，后者失效/无法访问）。真实 ASI:One 由 Fetch.ai 打造的 Web3 原生  |
| 4 | augie-ai | content,price | high | ✅ | augie.ai 域名已停放（GoDaddy parked page），链接失效；真实官网为 augie.studio（Augie by Aug X Labs  |
| 5 | blink-ai-cfo | content,platform,price | medium | ✅ | blinkaicfo.io 无法打开（fetch failed），非真实站点。真实产品为 YC 系 Blink.new 推出的 AI CFO 智能体'Geral |
| 6 | cocounsel | content,price | high | ✅ | URL红线：cocounsel.com 已于2025-03-31停用，官方现为 cocounsel.thomsonreuters.com（非仿冒，系旧官方域退役 |
| 7 | glitter-ai | content | low | ✅ | URL红线：glitter.ai 为 GoDaddy 待售/停放域名，非官网（真实官网 glitter.io）。内容幻觉：长正文将产品写成“通用AI聊天助手（写 |
| 8 | goldfish | content,description,price | high | ✅ | URL goldfish.ai 已被出售（Spaceship parked 页面），非官网。真实产品为 goldfish.sh（Product Hunt 上榜） |
| 9 | happy-horse | content | high | ✅ | happyhorse.ai 访问失败/疑似失效，真实官网为 happyhorseai.com（阿里巴巴 HappyHorse 是文生/图生视频大模型，带原生同步 |
| 10 | hera-launch | content,description,platform | high | ✅ | 功能完全张冠李戴：真实 Hera Launch 是 AI 生成产品发布视频的工具（YC孵化，2026-04-30上线，从提示词生成可编辑的发布视频，浏览器端）， |
| 11 | huoshan-writing | platform | medium | ✅ | ①URL失效：volcengine 产品页返回404，正确官网应为 writingo.net（火山写作确为字节跳动/火山引擎出品）。②平台编造：站内写『iOS、 |
| 12 | kapkap | description,price | medium | ✅ | ①域名错误：kapkap.com 返回 403，真实官网为 kapkap.ai（KapKap - AI Talking Videos，开发商 Starii Gl |
| 13 | kilo-code | platform | low | ✅ | 官方站点为 kilo.ai / kilocode.ai（kilocode.dev 抓取失败且非确认主站）；平台写成'浏览器插件'不实——Kilo Code 是  |
| 14 | melty-ai | content | high | ✅ | URL melty.ai 已被出售（GoDaddy parked 页面），非官网。真实官网为 melty.sh，项目仓库 github.com/meltylab |
| 15 | musicfx | content | high | ✅ | MusicFX是Google Labs完全免费的AI音乐实验，无任何Pro付费版；数据正文却虚构了'Pro版 付费订阅 约60秒 更精细 有（商业授权）'的付费 |
| 16 | octarine | content,price | high | ✅ | ①URL错误：octarine.ai 当前返回503/不可达，真实官网为 octarine.app（本地优先 Markdown/PKM 笔记应用，支持 macO |
| 17 | openhands | price | medium | ✅ | 官网主站应为 openhands.dev（云端 app.all-hands.dev），all-hands.ai 两次抓取失败且搜索无官方引用，非确认主站；官方  |
| 18 | rosply | content,description,platform,price | high | ✅ | 官网正确域名为 rosply.com（而非 rosply.ai，后者无法访问/失效）。真实 Rosply 是‘通过看屏幕、控制鼠标键盘来自动操作电脑’的桌面 A |
| 19 | skywork-3-1 | content,description | medium | ✅ | URL红线：当前 skywork.com 并非已核实官方域名（官方海外站为 skywork.ai，国内站为 tiangong.cn），疑似仿冒/错配，标 con |
| 20 | stanley-ai | content,price | high | ✅ | 当前域名 stanleyai.com 为 GoDaddy 待售占位域名，非官方（疑似仿冒/猜测域名）；官方为 getstanley.ai（Stan 的 Inst |
| 21 | termi-protocol | content,description,price | high | ✅ | termi.com 实际是墨西哥 POS 支付终端公司（Terminal punto de venta），与 AI 无关，URL 错误。真实 Termi Pro |
| 22 | trading-agents | content,platform,price | high | ✅ | 官网 URL 错误：tradingagents-ai.com 并非官方站点，真实官网为 tradingagents.co（对应开源仓库 github.com/T |
| 23 | vida | content,description | medium | ✅ | 官网 https://vida.ai 两次抓取均失败；搜索结果显示 vida.io / vida.app / vida.live 均为企业级 AI 智能体/客服 |
| 24 | windsurf | content,price | high | ✅ | 官网已变：codeium.com/windsurf 与 windsurf.com 均重定向至 Devin（Cognition 收购 Windsurf 并改名 ' |

## P1 URL 收尾（无正确官网，待下架/概念页决策）（5 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | abot-world | content,description,price | high | — | abot.world 为停放/跳转域名（“Click here to enter”），非产品官网。存储描述的“多模态 AI 代理协作平台、实时协作白板、自适应学 |
| 2 | lalamu | - | medium | — | 官网 lalamu.studio 直接抓取返回 403，且多家第三方目录（dang.ai、aitemple）标注 Lalamu 已于2024年前后关停/被收购。 |
| 3 | midjourney-scanner | price | medium | — | midjourneyscanner.com 域名已被 Porkbun 停放（'A Brand New Domain'待售），并非真实产品官网。联网检索未找到名为 |
| 4 | shadow-ai | platform,price | high | — | URL 失效：shadowai.com 为待售域名（GoDaddy 挂牌），并非产品官网。站内描述本身正确（'影子 AI'是企业治理术语，指员工私自使用未授权  |
| 5 | symphony-agent | - | low | — | 域名 symphonyagent.ai 无法交叉验证，疑为构造域名。市面存在多个同名实体：symphony.com（金融通讯/AI）、symphonyai.co |

## P2 内容高危重写（整页/大段张冠李戴）（110 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | ada-ai | content | high | — | 官网为面向企业的 AI 客服平台（ACX，Agent 自动解决客户咨询/聊天/邮件/语音多渠道）；站内 content 却写成'通用聊天助手/写东西/提醒/翻译 |
| 2 | ag2 | content,description,price | high | — | 官网正确（ag2.ai 为 AG2 官方站）。功能严重张冠李戴：真实 AG2 是开源多智能体框架（AutoGen 原班人马出品，'Build Systems,  |
| 3 | agent-browser | content,platform,price | medium | — | 未能直接抓取 agentbrowser.ai（WebFetch 失败），WebSearch 显示 'Agent Browser' 实为 Bright Data  |
| 4 | amp | content | high | — | url 仍可访问（Amp 现独立为 Amp Inc.，规范站 ampcode.com）。但内容严重错误：称'Amp 是 Anthropic 推出的 AI 编程助 |
| 5 | anthropic-console | content,price | high | — | 价格“Pro版$20/月”实为 Claude Pro 消费订阅价（claude.ai），Console 是 API 开发平台、按 token 计费，属张冠李戴； |
| 6 | anysearch | content,description,price | high | — | 官网(anysearch.ai)显示它是面向电信/企业的 AI 商业智能平台(多租户、统一客服/工单/运维数据，由 AWS Bedrock 驱动)，并非『聚合  |
| 7 | baichuan-2 | content,description,price | medium | — | Baichuan 2 是真实开源模型(2023, 4K 上下文)；站内称'2026年2.5系列/128K上下文/专业版¥99每月'，与官网当前主推的 Baich |
| 8 | base44 | content | medium | — | 官网真实（base44.com，已被Wix收购的无代码应用搭建平台）。但正文将其写成'代码补全与重构/Bug自动检测与修复/单元测试自动生成/项目文档自动生成' |
| 9 | bloop | content,description | medium | — | bloop.ai 为 Bloop 官网（但产品已于 2026-04 宣布停运）；描述称'2024年被Sourcegraph收购、持续更新中'均不实——Bloop |
| 10 | blop | content,price | high | — | 严重幻觉。官网blopai.com显示Blop是面向工程团队的QA测试代理(Playwright浏览器测试，测试以.blop.ts代码形式存于repo，跑在CI |
| 11 | bolt.new | content,price | high | — | 官网正确（bolt.new/pricing，StackBlitz 出品，归属无误）。Bolt.new Pro 现定价 $25/月（非 $10 也非 $20）。存 |
| 12 | canva-ai | content | medium | — | 官网正确。content中'AI生图50次/月'为编造：Canva官方为共享AI额度（免费最高200次标准/20次高级AI，Pro为10倍），非固定50次/月。 |
| 13 | claude-code-routines | content,price | medium | — | claude.ai/routines 访问返回『Page not found』，页面不存在，URL错误。未能核实 Anthropic 有『Claude Code |
| 14 | claude-fable-5 | content,description | high | — | Anthropic 官网（anthropic.com）可访问，但其真实产品为 Claude Opus 5 / Sonnet 5 / Haiku / Claude |
| 15 | clipdrop | content | high | — | 归属错误：Clipdrop 于 2024 年 2 月被 Jasper 从 Stability AI 收购，现为 Jasper 旗下产品（clipdrop.co  |
| 16 | cloud-computer-manus | content,description,price | high | — | Manus 确有 Cloud Computer 产品，但官网明确其为持久化 Ubuntu Server 云虚拟机（CLI命令行，无图形桌面、不支持Windows |
| 17 | cluely | content,description | high | — | 官网（cluely.com）真实，价格「付费版19.9美元/月起」属实（Pro=$19.99/月）。但description称其为「功能强大的AI对话助手」、c |
| 18 | colossyan | content,price | medium | — | 官网正常（colossyan.com），确为企业培训向AI数字人视频平台。定价过期：站内称'付费版起价$19/月'，官方最低付费 Starter 为 $27/月 |
| 19 | comet | content | high | — | 官网 comet.com 是 Comet ML（LLM 可观测性 Opik + MLOps 实验追踪平台），并非内容创作工具；站内正文将其描述为『AI内容创作平 |
| 20 | cube-sandbox | content | high | — | 官网真实（cubesandbox.ai 实际跳转/指向 cubesandbox.com，腾讯云出品）。但正文把产品写成'拖拽式工作流编辑器/AI版乐高'的无代码 |
| 21 | decohere | content | medium | — | 官网正常，产品为实时 AI 图像+视频生成器，功能描述（文生图、风格、编辑、批量、社区画廊）与官网一致，无张冠李戴。但正文版本对比表写「专业版 ¥98/月、团队 |
| 22 | deepgram | content | medium | — | URL为官网deepgram.com，正确。price中'免费45,000分钟/月、$0.004/分钟起'基本属实（来自$200额度按约$0.0043/分钟）。 |
| 23 | dexbotic | content | high | — | dexbotic.com 实际是原力灵机（ForceOrigins）开源的 VLA 具身智能机器人开发框架（训练/部署机器人操作与导航策略），descripti |
| 24 | eightfold | content | medium | — | 官网确认其为 AI Native Talent Intelligence Platform（招聘/人才管理），与描述基本一致。但官网仅提供'Book a dem |
| 25 | elai | content,price | medium | — | 官网域名 elai.io 正确（首页被 Cloudflare 拦截无法直接抓取，但搜索确认 elai.io/pricing 为官方页）。定价过期/命名错：站内称 |
| 26 | f5-tts | content | high | — | URL为SWivid官方仓库，正确。但content称'它是Suno团队开源的文本转语音模型'，实则由SWivid社区维护（description已正确标注'并 |
| 27 | fathom | content,description,price | high | — | ①描述与正文称『不录制音频只记录文字』错误：官网明确录制会议（pricing页列 Unlimited recordings & call storage，支持  |
| 28 | fellou | content,platform,price | high | — | 多处幻觉：①正文张冠李戴——将 Fellou 写成可视化拖拽式工作流自动化工具（类 Zapier：节点编辑器、GPT-4/Claude/Gemini 一键对比） |
| 29 | flint | content,platform,price | high | — | 官网可访问。开发者归属‘Tim Disney（disnet）’与‘本地优先、开源’均属实（已交叉核实其博客 disnetdev.com 与 GitHub dis |
| 30 | flowmarket | content | high | — | flowmarket.social 实际是面向 B2B 交易的 AI 代理撮合网络（企业创建代理自动发现/匹配/洽谈客户与供应商，替代冷外联），descript |
| 31 | galileo-ai | content,price | high | — | 描述正确（galileo.ai 是面向 LLM/AI 应用的 AI 可观测与评测平台，现属 Cisco）。但正文将产品写成'通用 AI 聊天助手/学习搭子'，属 |
| 32 | gemini-omni | content | high | — | 官网 gemini.google.com 核实无误，且简介（Google I/O 2026 发布的视频生成与编辑模型，可通过自然对话创作/编辑视频）准确。但正文 |
| 33 | githits | content,price | medium | — | 官网(githits.com)确为面向 AI 编程代理的开源代码/包版本化索引与 MCP 上下文层(GitHits, Inc.)，存储 description  |
| 34 | github-copilot | content,price | medium | — | 官网正确（github.com/features/copilot）。但定价已过时：当前官方方案为 Free $0 / Pro $10 / Pro+ $39 /  |
| 35 | gpt-5-6-sol | content | medium | — | GPT-5.6 Sol 真实存在（OpenAI 2026 旗舰，1M 上下文、max/ultra 推理）；但 content 称其支持音频多模态，官方 API  |
| 36 | grain | content,price | medium | — | ①正文写『支持 30 多种语言』与官网『transcripts available in 100+ languages』不符（至少为 100+）。②定价『Pro |
| 37 | grok-4-5 | content,price | high | — | 官网 grok.com 核实无误，简介（xAI 2026旗舰对话模型、实时联网、幽默风格、多模态、集成X数据）准确。但定价「Grok+ 订阅 $25/月」虚构： |
| 38 | heygen | content,price | high | — | 官网正确(heygen.com)。短期price"基础$10/月起"系虚构：HeyGen 最低付费档为 Creator $29/月（help.heygen.co |
| 39 | hirevue-ai | content | medium | — | 官网确认其为 AI 视频面试/技能评估平台，核心定位一致。但正文称 AI 分析候选人'表情神态'（面部表情），而 HireVue 已于 2021 年停用面部情绪 |
| 40 | huddle01-vms | content,description | medium | — | 官网 huddle01.com 现为 Huddle01 Cloud（云算力：VMs/GPU/Kubernetes），并非描述中的“去中心化视频会议虚拟机”。站内 |
| 41 | intercom-fin | content,description | medium | — | 官网（intercom.com/fin 现跳转 fin.ai）真实，定价基本合理（Intercom Essential 基础套餐起价约 $74/月，Fin 按  |
| 42 | invoko | content,description,platform | high | — | 官网可访问，确为 Invoko，但真实产品是 macOS AI 语音桌面助手（用语音在任意应用内起草、总结、回复、执行操作，Apple Silicon Mac  |
| 43 | jamie-ai | content | high | — | 正文幻觉：站内正文将 Jamie 写成通用 AI 对话/文档/写作/翻译助手（类 ChatGPT），实际官网为隐私优先的 AI 会议纪要工具（无机器人入会、10 |
| 44 | khroma | content,price | high | — | 官网 Khroma 为完全免费的浏览器端 AI 配色工具，无任何付费订阅或企业版。站内'付费版$9/月'及 description/content 中'2026 |
| 45 | kollab | content,description,price | high | — | 官网 kollab.ai 实为“可执行工作流(Playbooks)平台”（AI作为参与者执行流程，含客户端门户、白标），并非描述中的“实时白板+文档+项目管理融 |
| 46 | krisp | content,price | medium | — | ① 内容编造『虚拟背景：替代背景虚化』功能——Krisp 是音频降噪工具，无视频虚拟背景功能（实为噪声消除/回声消除/口音转换/转录）。② 价格字段写『$10/ |
| 47 | lightrag | content | high | — | 官网（官方仓库 github.com/HKUDS/LightRAG）正确。但正文 content 误将开发团队归属为"香港中文大学（深圳）数据科学学院"，实际为 |
| 48 | lingoai | content,price | medium | — | 官网 lingoai.io 真实,但其定位是 Web3/DePIN 去中心化 AI 数据平台(LingoTrans、DAO 众包翻译、Speak to Earn |
| 49 | livedemo | content,description | medium | — | 官网 livedemo.ai 确为交互式产品演示创建工具（无需编码，对标Storylane/Navattic/Arcade），方向正确。但站内称其为“开源替代方 |
| 50 | longcat20 | content,description,platform | high | — | 官网可访问，确为 LongCat-2.0，但真实产品是美团（Meituan，HuggingFace 组织 meituan-longcat）推出的'AI Codi |
| 51 | lovable | content,price | high | — | 官网正确（lovable.dev/pricing，原名 GPT Engineer，归属无误）。Lovable Pro 现定价 $25/月（非存储所称 $20/月 |
| 52 | luma-ai | content,price | high | — | 官网正确(lumalabs.ai)。短期price"免费版+Pro $10/月"虚构：Luma Dream Machine 付费档为 Standard 约$30 |
| 53 | magnific-ai | content,price | high | — | ① 定价字段「免费版每月3次增强，付费版$12/月起」错误：Magnific 为纯付费工具，无永久免费版（仅 24 小时试用、50 token≈10 次放大）； |
| 54 | makersclaw | content,description,price | high | — | 官网(makersclaw.com)自身定位为『Hire AI Agents That Work 24/7』的自主AI员工雇佣平台，并非『专为独立开发者与创客设 |
| 55 | miaohua | content | high | — | 官网真实（商汤）。但content将秒画错误归为'字节跳动/豆包AI'，实为商汤科技(SenseTime)'日日新'体系产品。来源：sensetime.com官 |
| 56 | mike-ai | content | high | — | 官网为 AI 健身教练（Meal/Workout Plans + FitnessGPT）；站内 content 却写成'语音对话助手/支持100+语言/企业定制 |
| 57 | mindra | content,description,price | high | — | 产品归属/功能张冠李戴。Mindra 实为 AI 代理编排平台（组建专业 Agent 团队跨工具执行营销/广告/销售/运营任务，3000+ 集成），并非站内描述 |
| 58 | minicpm-o | content | high | — | MiniCPM-o 实际由 OpenBMB（面壁智能）联合清华开源的端侧全模态模型；content 误写为'MiniMax 公司推出'，开发方张冠李戴。desc |
| 59 | minimax | content,price | medium | — | URL正确（另有 hailuoai.com）。正文称“MiniMax完全免费使用”不实：存在付费会员（海螺AI 至臻版约 ¥899/月、年费过万）与 MiniM |
| 60 | monid | content | high | — | Monid 实为 Agent 工具调用路由器/统一付费层（200+ 数据端点、按调用付费、MCP 接入），非聊天助手；content 误写成'轻量 AI 助手/ |
| 61 | murf-ai | content,description | medium | — | ① 声音/语言数过时：官网现 200+ 声音、35+ 语言，站内写 120+ 声音、20+ 语言（为旧版数据）。② 价格字段写『免费使用』不准确——实为含付费  |
| 62 | nex-n2 | content,platform,price | high | — | 官网(nex-agi.cn)显示 Nex-N2 是 Nex-AGI 开源的 MoE 大模型系列(Pro/mini，基于 Qwen3.5)，定位 Agentic  |
| 63 | open-design | content,price | high | — | 官网 FAQ 明确：Open Design 免费、Apache-2.0、无订阅制（'there is no Open Design subscription'） |
| 64 | openai-codex | content,price | medium | — | 官网正确（openai.com/index/introducing-codex，官方页，归属无误）。但存储价 'Pro $10/月' 错误：Codex 通过 C |
| 65 | openclaw | content | high | — | 官网(openclaw.ai)明确为 Peter Steinberger 团队的开源个人 AI 智能体（“真正干活的 AI”，管理收件箱/发邮件/管日历，跑在本 |
| 66 | panda-probe | content,platform,price | high | — | 官网(pandaprobe.com)明确为 Chirpz AI 的开源智能体工程平台(追踪/评测/监控)，与存储 description 一致；但 conten |
| 67 | pencil-ai | content | high | — | 功能张冠李戴：Pencil（Pencil AI Limited，trypencil.com）实际是面向电商/投放团队的 AI 广告创意与表现预测平台（基于历史广 |
| 68 | perplexity-ai | content | medium | — | 官网 perplexity.ai 正确，Pro $20/月准确；但 content 中“答案准确率提升到92.3%、比2025年提升11%”及“三级可信度标注系 |
| 69 | phinite | content,price | high | — | URL为官网phinite.ai，正确。但content将Phinite描述为'AI语音合成与音频修复工具'，实为多智能体AI编排平台（Agentic OS，与 |
| 70 | pixelle-video | content,platform,price | high | — | GitHub 仓库真实存在（AIDC-AI 团队开源，Apache-2.0，可本地免费运行）。但站内数据严重编造：①定价'付费版$19/月起'错误——开源项目完 |
| 71 | pmb | content,price | high | — | 官网 pmbai.dev 确为“面向AI编程代理的本地优先记忆工具”(MCP协议，Apache 2.0开源，完全免费无付费版)——这与站内 descriptio |
| 72 | poe | content,price | high | — | URL正确（Quora 旗下）。价格字段“基础$10/月起”与正文“Poe订阅 $22/月”均错误：真实付费入门档 $4.99/月（1万积分/日），主力 $19 |
| 73 | propane | content,price | high | — | 官网可访问，确为'面向产品团队的客户情报平台（Customer Intelligence for Product Teams）'，整合 300+ 工具的多源客户 |
| 74 | prowritingaid | content,price | high | — | 官网URL正常。①定价编造：站内写『付费版$20/月起，年付$99/年』，官网当前 Premium 为 $30/月（年付 $120）、Premium Pro $ |
| 75 | qingying-ai | content | high | — | 官网域名 chatglm.cn 为智谱官方站（清影入口为 chatglm.cn/video），URL 无误。但正文归属严重错误：内容称'清影AI是360公司推出 |
| 76 | qoder | content | high | — | 官网(www.qoder.com)及阿里云文档确认 Qoder 为阿里云产品，2026-05-20 由通义灵码(Lingma)更名而来（来源：help.aliy |
| 77 | qwenpaw | content,price | high | — | qwenpaw.dev 域名在售（GoDaddy 标价 $5,500），无真实官网，高度疑似虚构产品。content 描述的『基于通义千问的开发助手』及定价『P |
| 78 | rankspot | content,price | high | — | 官网显示 RankSpot 是『自动研究/撰写/发布 SEO 文章』的 AI Agent(每天自动发博客)，与存储 description 一致；但 conte |
| 79 | recraft | content,platform | high | — | ① 平台字段写「本地部署 / Web」错误：Recraft 是纯云端 SaaS（含 API/移动端），不支持本地部署。② 正文版本对比表写「Premium ($ |
| 80 | reloop-animation-studio | content,description | high | — | 官网 https://reloop.studio 可访问，实为 “AI UGC Video Generator”（用 AI 虚拟主播/形象生成 9:16 社媒短 |
| 81 | replit-ai | content,price | high | — | 官网正确（replit.com/pricing）。但 Replit Core 现定价 $20/月（年付等价 $18/月），并非存储所称 $25/月；且现另有 R |
| 82 | runway-agent | content | high | — | runwayml.com 是 Runway 真实官网；Runway Agent 确为 2026-05-13 发布的对话式 AI 视频创作 Agent，定价（$1 |
| 83 | rytr | content,price | high | — | 免费版实际每月 10K 字符（站内及正文均写 5000，偏低，属价格错误）；付费 Unlimited 约 $7.5/月（年付）起、Premium $24.16/ |
| 84 | schole-ai | content,price | high | — | 官网 schole.ai 真实，且描述准确：Scholé 是基于 EPFL/伯克利/哈佛研究的‘企业级 AI 素养与培训平台’，面向组织与团队。但正文张冠李戴— |
| 85 | sierra-ghostwriter | content,platform,price | high | — | ①URL可达且为真实公司（Sierra.ai = 企业级对话式 AI 智能体平台）。官网确有『Ghostwriter』产品，但它是『智能体构建工具』（用 SOP |
| 86 | spark-tts | content | medium | — | URL为SparkAudio官方开源仓库，正确。但content称'2026年最新版本增加了情感控制功能'——官方README（2025年）仅列出可控生成（性别 |
| 87 | speechify | content,description,price | high | — | ① 价格错误：官网 Premium 网页版 $29/月（年付 $139），站内正文写 $11.99/月、价格字段写『基础$10/月起』，均不对。② 语言数错误： |
| 88 | stepfun | content | high | — | 官网（stepfun.com）真实，Step-2万亿参数自研底座属实。但content误称公司由「前百度高管李开复」创立——李开复实为01.AI（零一万物）创始 |
| 89 | strands-agents | content | high | — | 官网与 description 正确：Strands Agents 是 AWS（亚马逊云科技）开源的 AI 智能体 SDK（Apache 2.0，AWS Ope |
| 90 | swytchcode | content | high | — | 官网(swytchcode.com)确认 Swytchcode 是面向 AI Agent 的生产级 API 执行/工具调用层（含鉴权、重试、Schema 校验， |
| 91 | tabbit | content,platform | high | — | 多处幻觉：①平台错误——站内称 Chrome/Edge/Safari/Firefox 扩展 + Web 端，官网实际为 macOS 原生 AI 浏览器应用（Ap |
| 92 | tabstack | content,price | medium | — | URL 指向正确的产品：tabstack.co 是免费的新标签页/书签管理扩展（一键保存全部标签页、分组/文件夹组织），与描述一致。但正文编造功能：声称'AI  |
| 93 | tempus-ai | content,platform,price | high | — | 多处幻觉：①平台编造——站内称支持网页/iOS/Android/Chrome插件/桌面端，官网实际仅 Apple 生态（iPhone/iPad/Mac/Appl |
| 94 | tldv | content | medium | — | 官网 tldv.io 明确支持 30+ 语言（含中文），但站内正文写『支持 90 多种语言』错误（应为 30+）。定价『付费版$12/月起』官网定价页 /pri |
| 95 | tongyi-wanxiang | content | medium | — | 官网正常（tongyi.aliyun.com/wanxiang，阿里「万相」图像/视频生成模型）。内容幻觉：正文称「2026年已升级至3.0版本」，但官网页面当 |
| 96 | uizard | content,platform,price | high | — | 官网定价页：Uizard Pro 为 $12/月（年付），Business $39/月，无 $19 档；Autodesigner 当前为 2.0（NEW），无  |
| 97 | unitree-gd01 | content,price | high | — | 官网 unitree.com 真实，且描述准确：GD01 是宇树 2026-05 发布的全球首款量产载人变形机甲（可切换双足/四足，约 500kg），起售价 3 |
| 98 | upscayl | content | medium | — | 桌面版确为免费开源且支持批量处理，价格“免费（开源）”对桌面版正确（另有付费的 Upscayl Cloud）。但正文所述“v5.0 版本，新增……企业级 API |
| 99 | v0.dev | content,price | high | — | 官网正确（v0.dev 现重定向至 v0.app，Vercel 出品，归属无误）。v0 现方案 Free $0 / Plus $30/用户/月 / Busine |
| 100 | verba | description | medium | — | GitHub仓库为真实官方主页，但项目已于2026年6月归档停止维护（最新版本2.1.3）。描述称'2026年已更新至v2.0版本，增强多模态检索和自定义工作流 |
| 101 | video-os | content,description | high | — | 官网 jupitrr.com 正确（产品确为 Jupitrr AI 的 VideoOS，公司归属无误）。但正文/描述把 VideoOS 写成'视频内容智能分析平 |
| 102 | vizard | description | medium | — | 官网正常，长视频自动切片+字幕能力属实，定价'免费版+Pro $20/月'与第三方评测一致。但描述称'内置AI虚拟主播功能'存疑——Vizard 官网及多个评测 |
| 103 | wenxin-yige | content,description | medium | — | 官网 yige.baidu.com 真实存在，但百度已于2025年4月1日将文心一格服务迁移合并至文心一言官网（来源：百度百科/官网迁移公告），文中'2026年 |
| 104 | wonder-ai | content | high | — | 官网确认 Wonder AI 是 Codeway 出品的 AI 绘画/文生图应用（iOS/Android、40+ 艺术风格、AI Logo、AI Tattoo） |
| 105 | xint-code | content,description | high | — | 官网正确（Theori 官方站，产品 Xint Code 确为 AI-Powered SAST，产品页 code.xint.io）。但 description/ |
| 106 | xunfei-zhizuo | content,platform | high | — | 官网可访问且确为科大讯飞旗下产品（运营方合肥科讯创想）。但官网（peiyin.xunfei.cn，域名即'配音'）核心定位是 AI 配音 / 数字人视频生成平台 |
| 107 | yoroll | content | high | — | 正文幻觉：站内正文将 Yoroll 写成智能任务管理/内容创作/翻译工具，实际官网为 AI 原生互动视频游戏创作平台（文本/图片/短片生成可玩分支剧情游戏）。描 |
| 108 | zapier-ai | content,platform | high | — | Zapier 为纯云 SaaS 自动化平台，不支持本地部署，platform 字段'本地部署 / Web'错误。content 版本对比表中 Professio |
| 109 | zi-dong-tai-chu | content,description | medium | — | 官网（taichu.ia.ac.cn，中科院自动化所）真实。但description与content均称「2026年已升级至3.0版本」，而官网新闻显示2026 |
| 110 | zoona | content | high | — | 官网 https://zoona.ai 可访问，实为 “Zoona AI Agents for Customer Service”（AI 客服代理平台），与站内 |

## P3 价格编造修复（price 字段）（101 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | 360-zhinain | price | high | — | URL为官方域名（另有 ai.360.com）。定价“免费版+Pro $10/月”错误：真实为人民币（标准版约 ¥49/月、专业版约 ¥99/月），币种与金额均 |
| 2 | activepieces | price | medium | — | Activepieces 云定价为 Standard 免费 + 按活跃流程 $5/个/月（用量计费）、Ultimate 定制（来源 activepieces.c |
| 3 | adcreative-ai | price | medium | — | 定价范围有误：官网当前 Starter 起价 $29/月（季付）与站内下限一致，但 Ultimate 方案现为 $749–999/月，站内写的“上限 $299/ |
| 4 | alexa-plus | price | high | — | Alexa+ 真实存在（亚马逊生成式 AI 助手）；定价标 $5.99/月 错误，官方为随 Prime 免费或 $19.99/月（非Prime）。域名 amaz |
| 5 | anythingllm | price | high | — | 官网 anythingllm.com 正确（Mintplex Labs 出品）。但描述中"付费云服务版起价$9/月"错误：官方托管云最低档为 Basic $50 |
| 6 | anyword | price | medium | — | 官网定价页未列出免费版（仅 Starter $39/月 年付起、Data-Driven $99/月、Business/Enterprise 定制），站内「免费版 |
| 7 | arc-browser | platform,price | high | — | Arc 由 The Browser Company 开发，实际完全免费（含 Arc Max AI 套件），并不存在 $10/月的 Pro 付费版，站内 pric |
| 8 | autify | price | medium | — | 官网 autify.com 正常，AI 自动化测试平台、跨浏览器/移动端描述准确；实际付费起价为 NoCode Starter $199/月（年付$149），无 |
| 9 | baidu-qianfan-agent | price | low | — | 官网（百度智能云千帆）与描述（企业级 Agent 开发平台、基于文心、可视化构建、RAG、工作流编排）基本准确。但“专业版¥99/月起”无可靠来源：千帆采用免费 |
| 10 | bardeen | price | high | — | Bardeen 实际定价为 Basic $10/月、Premium $50/月（或 $480/年）、Enterprise 定制（来源 bardeen.ai/pr |
| 11 | beautiful.ai | price | medium | — | 官网有效。Pro实际$12/月(年付)或$14.50/月，价格字段"基础$10/月起"偏低不准确；正文表格$12/月反而准确。另正文"快速上手"误写官网为www |
| 12 | brandmark | platform,price | high | — | 官网正确。Brandmark为一次性买断制（Basic $35、Designer $95、Enterprise $195），非'$10/月'订阅；且为纯Web工 |
| 13 | buffer-ai | price | high | — | 定价错误。Buffer 实际档位：Free（已含 AI Assistant）、Essentials $5/频道/月、Team $10/频道/月，无 $15/月档 |
| 14 | cartesia | price | high | — | URL为官网cartesia.ai，正确。但price称'付费版$19/月起'——官网定价为Free $0、Pro $4-5/月、Startup $39-49/ |
| 15 | chatgpt-work | price | medium | — | 官网 chatgpt.com/work 确为OpenAI“ChatGPT Work”页面（面向团队的智能体，跨应用/文件产出文档/表格/演示），产品与归属正确。 |
| 16 | chuangketie-ai | price | medium | — | 官网(chuangkit.com/price/vip)通用版标价¥6/月起，站内写“VIP会员29.9元/月起”。该价与App Store内购¥29/月档接近， |
| 17 | claude-code | price | medium | — | 官网正确（docs.anthropic.com/en/docs/claude-code，Anthropic 出品，归属无误）。但存储价 '基础$10/月起' 无 |
| 18 | codebuddy-tengxun | price | high | — | 确为腾讯云代码助手 CodeBuddy（基于腾讯混元/大模型，支持 VS Code/IntelliJ/Chrome/Edge，功能描述准确）。但定价编造：存储' |
| 19 | coderabbit | price | medium | — | 官网 coderabbit.ai 正常；实际付费档为 Pro $24/用户/月（年付）/$30 月付、Pro+ $48，无 $10 的 Team 档，存储'Te |
| 20 | copy.ai | platform,price | high | — | 价格严重失实：现行最低付费套餐为 Chat $29/月，Growth $1000/月 等，无 $10 或「Pro $49/月」套餐（正文亦写 Pro $49/月 |
| 21 | crew-ai | price | medium | — | 官网与内容（开源多智能体编排框架、角色协作、可视化/AMP 平台、企业安全）基本准确。但“Pro版$29/月”已过期：官方定价页当前仅 Basic Free + |
| 22 | d-id | price | medium | — | 官网正常（d-id.com），确为AI数字人/口型同步平台。定价编造：站内称'付费计划起价$5.99/月（个人版）'，官方当前最低付费档为 Lite $4.7/ |
| 23 | dall-e-3 | price | high | — | 官网真实。但price字段'基础$10/月起'错误：DALL-E 3无独立$10档，需ChatGPT Plus($20/月)或按图计费API（约$0.04-0. |
| 24 | deepl | price | medium | — | 官网为真实官网(deepl.com)。价格表虚构:DeepL 2026年已将套餐改名为 Individual / Team / Business / Enter |
| 25 | deepsec | price | high | — | 仓库 github.com/vercel-labs/deepsec 真实存在（Vercel Labs，2026-05 开源，Apache 2.0，依托 Clau |
| 26 | designs-ai | price | high | — | 官网定价为新加坡元：Plus S$49/月、Pro S$99/月、Enterprise S$239/月，无 $29 档，且币种应为 SGD 而非 USD；定价页 |
| 27 | duolingo-max | price | high | — | 官网域名正确。定价写“约$12.99/月”错误，官网 Max 为 $29.99/月（年付$168）。GPT-4驱动、Roleplay/Explain My An |
| 28 | feishu-assistant | platform,price | high | — | 官网有效。飞书AI实为人民币计价（个人AI会员¥69/月起、企业版基础¥9900/年起），站内写"基础$10/月起"币种与金额均错误，属编造定价。另平台字段写" |
| 29 | figma-ai | price | high | — | 官网正确。当前 Professional 全席位 $16/月、Organization $55/月。数据'Pro $10/月'错误；content中'Profe |
| 30 | flair-ai | price | high | — | 官网定价：Free $0、Pro $8/月、Pro+ $26/月、Scale $38/月，无 $29 档；站内'Pro版$29/月起'系编造/过期。功能描述（品 |
| 31 | fliki | platform,price | high | — | 官网正确(fliki.ai)。短期price"免费版+Pro $10/月"虚构：Fliki 最低付费档为 Standard $28/月（fliki.ai/pri |
| 32 | flux | price | high | — | 官网真实。price字段'Pro $10/月'错误：Flux Pro为按图计费API（约$0.04-0.055/张），无$10/月订阅档；Schnell/Dev |
| 33 | frase | platform,price | high | — | 官网URL正常。①定价编造：站内写『免费版有限功能，专业版$12.99/月起』，官网当前最低 Starter $39/月（年付）/$49 月付，且仅有7天试用、 |
| 34 | gaoding-ai | price | medium | — | 官网正确。当前模板会员8元/月起、大会员16.5元/月起（含AI创作），无'AI创作会员¥30/月（原价¥59）'档位，价格虚构；content'基础$10/月 |
| 35 | gemini | price | high | — | 定价虚构：描述与price字段写'Pro $10/月'，实际Google AI Pro(原Gemini Advanced)为$19.99/月(来源:gemini |
| 36 | glass-health | price | high | — | 官网确实存在且功能描述正确（面向临床医生的 AI 临床决策支持与病历撰写）。但定价编造：免费 Lite 档存在，官方 Pro 档约 $81–90/月（另有 St |
| 37 | grammarly-ai | platform,price | high | — | 平台标注「本地部署 / Web」错误：Grammarly 为云端 SaaS（浏览器插件+桌面/移动端），不支持本地/私有化部署。价格「基础$10/月起」无对应套 |
| 38 | humata-ai | price | high | — | Humata 实际定价为免费版（60页/10次问答）与 Expert $9.99/月（500免费页后按 $0.02/页计费），并非站内所写『Pro $19/月无 |
| 39 | hunyuan-image | price | medium | — | 官网 hunyuan.tencent.com 真实。但定价虚构：腾讯混元图像/生图采用云资源包计费，免费额度为各模型一次性50次（非'每月100张'），混元生图 |
| 40 | iconscout-ai | price | high | — | 定价编造/错误：官网 IconScout AI 包含在付费方案中（Individual $14.99/月、Team $24.99/月、Team+ $54.99/ |
| 41 | ideogram | price | high | — | 官网真实。price字段'基础$10/月起'错误：官网无$10档，Basic $8/月（老用户）或新用户入门Plus $20/月。来源：ideogram.ai定 |
| 42 | jasper | price | high | — | 官网现行定价已无「Creator $49」套餐（该档已取消/更名）。现行付费入门为 Pro：$59/月（年付）或 $69/月（月付），Business 为定制报 |
| 43 | kaiber | price | medium | — | 官网正常（kaiber.ai，现为 Kaiber Canvas/Beat Sync 工作流）。定价虚假：站内称'免费版每月100积分，高级版$9.99/月起'， |
| 44 | kanwas | price | medium | — | 产品属实（团队'上下文大脑'/共享上下文协作空间，含 AI Agent、1000+ 连接）。描述称'集成200+企业应用'与官方'1000+ connectio |
| 45 | kapwing | price | medium | — | 官网 kapwing.com 正确（直抓失败但搜索确认官网在线）。定价混乱/有误：站内价 'Starter $16/月、Pro $33/月'，且正文表格又称 ' |
| 46 | krea-2 | price | high | — | Krea官网(krea.ai)真实，Krea 2确为2026年推出（发布说明5月GA）。但定价编造：官网实际为 Free $0(100算力单位/日)、Basic |
| 47 | langflow | price | medium | — | 官网 langflow.org 正确（现由社区/OSS 维护，曾属 DataStax/IBM）。但描述中"Pro版$49/月"无官方依据：DataStax 已于 |
| 48 | language-tool | price | high | — | 官网URL正常。定价编造：站内写『高级版每月€9.99起』，官网实际个人高级版约 $24.90/月（年付约 $69.90/年，折后更低），€9.99 明显偏低、 |
| 49 | lets-enhance | price | high | — | 官网正常，AI 图像放大/增强工具。定价字段写「免费版每月20张，付费版$9起/月」：付费 $9/月起（Starter 100 credits/月，年付 $9） |
| 50 | liblibai | platform,price | high | — | ① 定价字段写「免费版+Pro $10/月」错误：LiblibAI 为人民币计价国内平台，公开资料显示会员最低约 ¥29-39/月（入门版/基础版VIP），并无 |
| 51 | looka | price | high | — | 官网正确。Looka需付费下载Logo（品牌套件订阅或一次性Logo包），仅可免费预览生成，'免费使用'为错误；实际Logo下载需购买（$20起等）。 |
| 52 | magic-patterns-agent-2-0 | price | high | — | 官网magicpatterns.com为AI产品设计工具(提示词/需求转高保真UI)。定价编造：站内写“Pro $29/月、团队版 $79/月”，官方实际为 F |
| 53 | meta-so | price | high | — | 官网 metaso.cn 正确；但价格“基础$10/月起”错误：秘塔AI搜索付费会员以人民币计价（App Store 月度会员¥39、第三方测评 Pro 约¥4 |
| 54 | mureka | price | medium | — | 官网(mureka.ai，Skywork AI)现行定价：Basic $8/月、Pro $24/月（均年付价）；数据写'专业版$9.99/月起、免费版每月50积 |
| 55 | napkin-ai | price | high | — | 官网有效。站内价格字段写"Pro $10/月"，但同一正文表格却写"Pro $20/月"，自相矛盾；官网实际为Free/Plus($9/月)/Pro(~$20- |
| 56 | notebooklm | price | high | — | 官网有效（需登录）。免费版确存在；但付费NotebookLM Plus实为$19.99/月（随Google AI Pro/One AI Premium捆绑），站 |
| 57 | notion-ai | price | high | — | 官网有效（notion.so为App域名）。定价已失效：Notion AI现随Business($20/人/月)与Enterprise套餐内置，旧"AI附加费$ |
| 58 | octolens | price | medium | — | 官网可正常访问，产品定位（AI 社媒监听/品牌与竞品监测、情感分析）与站内描述一致。但站内定价‘付费版从 $49/月起’已过期：官网当前在售为 Pro $159 |
| 59 | openai-agents-sdk | price | low | — | 官网文档与内容（官方代理框架、多代理编排、护栏、结构化输出、工具调用、企业 SSO）基本准确，SDK 本身免费开源。但“$15/百万token（GPT-4o 代 |
| 60 | opencode | price | high | — | 官网(opencode.ai)确认 OpenCode 为开源免费 AI 编码代理（『Free models included or connect any mo |
| 61 | phind | price | medium | — | 官网 phind.com 正确；价格“Pro $10/月”存疑：第三方报道 Phind Pro 多为 $15–20/月（$15/$17/$19.99/$20 不 |
| 62 | pinecone | price | high | — | 价格字段“付费计划从 $49/月起”错误：Pinecone 当前付费档为 Builder $20/月、Standard 最低 $50/月（另有免费 Starte |
| 63 | play-ht | price | medium | — | 价格编造/过期：官网无 $9.99 套餐。实际为 Free(5K字符/月) + Creator 约 $29-31/月 + 无限/Pro 约 $49-99/月 + |
| 64 | pollinations | platform,price | high | — | 官网 pollinations.ai 是面向开发者的多模态 API 平台(文本/图像/视频/音频)，采用 Pollen 积分制，免费起步、按用量/Bring-Y |
| 65 | postiz | price | high | — | 产品属实（开源 AI 社交媒体排程工具），描述与正文功能一致。定价错误：站内写'付费版$9/月起'，实际付费档为 Standard $29/月、Team $39 |
| 66 | predis-ai | price | high | — | 定价已过期：官网当前最低付费方案 Core 为 $19/月（月付）起，站内写“付费版$29/月起”偏低；且正文版本表“专业版约$29/月、团队版约$99/月”与 |
| 67 | quizlet-ai | price | medium | — | 官网域名正确。专业版“$7.99/月”为过期旧价，官网现 Quizlet Plus 约 $2.99–$3.74/月（年付$35.99–$44.99）；“教育版需 |
| 68 | qwen-chat | price | high | — | 定价虚构：price字段写'Pro $10/月'为虚构美元定价；实际千问个人专业版(Pro)为人民币59元/月，基础对话永久免费(来源:阿里云百炼平台、开发者社 |
| 69 | raycast-ai | platform,price | high | — | Raycast 仅支持 macOS 桌面端（非 Web、非本地部署的通用服务），platform 字段『本地部署 / Web』错误；Pro 实际为 $8/月，站 |
| 70 | relevance-ai | price | high | — | 官网与内容基本准确（AI Workforce/无代码智能体平台）。但定价“$49/月起”错误：当前公开档位为 Free $0、Pro $19/月(年付)/$29 |
| 71 | relume | price | medium | — | 官网正确。付费起步为 Starter $18/月（Pro $40/月、Team $36/人/月），数据'付费版$15/月起'金额不准确；免费版存在。 |
| 72 | remove.bg | price | high | — | 官网正确。当前订阅价：Lite $8.10/月、Pro $35.10/月（年付）、Volume+ $80.10/月，免费版仅出低清水印预览。数据'Pro $10 |
| 73 | robin-ai | platform,price | medium | — | 官网 robinai.com 正确。定价“个人版$29/月、专业版$99/月”不实：旧 Pro 曾为$100/席/月且已于2025年停用，现转为企业定制/演示报 |
| 74 | shulex | price | high | — | 产品属实（跨境电商 AI 客服 + VOC.AI 评论分析），描述与正文功能一致。定价错误：站内写'付费版$39起/月'，实际 VOC.AI Pro 为 $99 |
| 75 | slidesai | price | high | — | 官网 slidesai.io/pricing 确认：免费版为 12 次/年（非站内『每月3次』）；Pro €8.79/月(约$9.5，非$10)、Premium |
| 76 | smartcat | price | high | — | 官网真实(smartcat.com)。价格编造:存储价"付费版$15/月起"错误,官网当前最低付费方案 Adapt 为 $1,200/年(约$100/月),无$ |
| 77 | soundraw | price | high | — | 官网现付费档：Creator $5.99/月（限时优惠）、Artist Starter $10.49、Artist Pro $12.59、Artist Unli |
| 78 | spellbook | price | medium | — | 官网 spellbook.legal 正确（旧域 spellbook.com 为$99首月促销页）。定价“免费版/专业版$29/月/团队版$99/月”无依据：现 |
| 79 | suno | price | medium | — | 官网定价卡显示 Pro $8/月、Premier $24/月（年付等价），但站内正文写 Pro $10/月、Premier $30/月（与官网旧版FAQ一致，与 |
| 80 | supabase-ai | price | high | — | 价格字段写“Pro $10/月”错误：Supabase Pro 实际为 $25/月（额外项目才从 $10/月起），同工具 content 表格已正确列 $25。 |
| 81 | surfer-seo | price | high | — | 官网URL正常（surferseo.com）。定价编造：站内写『免费版可用，付费版$49起/月』，官网当前无免费版（仅7天退款保证），最低付费 Essentia |
| 82 | synthesia | platform,price | high | — | 官网正确(synthesia.io)。短期price"基础$10/月起"虚构：最低付费档为 Starter $29/月（synthesia.io/pricing |
| 83 | taskade | price | high | — | 定价过期/错误：站内称付费版 $8/月起，官网定价页实际付费入门为 Pro $10/月（年付），另有 Business $25、Max $100、Enterpr |
| 84 | tencent-yuanbao | price | high | — | 定价虚构且与正文矛盾：price字段写'基础$10/月起'为虚构美元定价，而正文称'完全免费'；实际元宝基础免费，Pro约19-29元/月(人民币)(来源:腾讯 |
| 85 | tiangong | price | high | — | URL为昆仑万维官方域名（另有 canonical tiangong.cn）。定价“免费版+Pro $10/月”错误：真实为人民币会员（Basic 包月 ¥45 |
| 86 | topaz-photo-ai | price | high | — | 定价已过期：Topaz Labs 于 2025 年 9 月取消永久授权，$199 一次性购买已不存在；产品已改名为“Topaz Photo”（原 URL 跳转至 |
| 87 | trae | price | high | — | 官网 trae.ai 正常（字节跳动出品，描述正确）。但定价'专业版$19/月'错误：官网当前 Pro 为 $10/月（首月 $5），另有 Lite $3/$1 |
| 88 | tuguaishou | price | high | — | 官网(818ps.com)个人商用VIP实际为4.92元/月起、个人商用SVIP 8.3元/月；站内价格字段写“29.9元/月起”、正文写“个人会员约¥60/月 |
| 89 | udio | price | medium | — | Udio 实际分 Free / Standard($10/月) / Pro($30/月) 三档。站内写『Pro $10/月 500首/月』混淆了 Standar |
| 90 | velo-ai | price | high | — | 定价编造：站内称高级版$12.99/月，官网定价页实际 Pro 为 $49/月（另有 Ultra $200/月、Enterprise 定制）。功能描述基本准确（ |
| 91 | visily | price | medium | — | 官网定价：Starter $0、Pro $11/编辑器/月（年付）、Business $29；站内写'付费版$12/月起'，与官网 $11 相差约$1，疑似轻微 |
| 92 | warp-terminal | price | medium | — | 官网 warp.dev 正常（AI 终端、Rust、已开源，描述准确）；当前付费档为 Build/Max/Business（$50/用户/月）等，无 $20/月 |
| 93 | wenxin-yiyan | price | high | — | 定价虚构：price字段写'Pro $10/月'为虚构美元定价；实际文心Plus会员为人民币¥59.9/月(连续包月¥49.9)，产品已升级为'文小言'(来源: |
| 94 | wondercraft-ai | price | medium | — | 价格过期/偏低：官网免费档约 6分钟/月（站内写 10分钟），专业版官网约 $20-45/月（站内写 $19/月起）。语言 30+ 基本吻合（Creator 档 |
| 95 | wordtune | price | high | — | 价格「高级版约 $20/月」失实：官网实际 Advanced $4.89–6.99/月（年付/月付）、Unlimited $6.99–9.99/月，最高个人档仅 |
| 96 | writesonic | price | high | — | 价格严重失实：官网现行套餐为 Starter $79/月起步（AI Search Visibility/SEO+GEO 平台）、Basic $199、Growt |
| 97 | xinghuo-iflytek | price | medium | — | URL正确。定价“基础$10/月起”无依据：消费者端免费使用，API 按 token 计费（约3元/百万tokens），并无 $10/月 订阅档；平台标注“本地 |
| 98 | zed-editor | price | high | — | 官网 zed.dev 正常（Atom 团队打造、Rust、内置 AI 协作，描述准确）；实际 Pro 版 $10/月（非 $20），基础版免费准确（来源：zed |
| 99 | zendesk-ai | price | medium | — | 官网域名正确。价格写“基础版$49/用户/月起”无官方依据：官网 Support Team $19/席/月、Suite Team $55、AI（Copilot） |
| 100 | zety-ai | price | high | — | 官网 zety.com/pricing 确认：免费版（仅 TXT 导出），Pro 包 $1.95 试用14天后自动续费 $25.95/4周(约$28/月)，年付 |
| 101 | zhipu-chatglm | price | high | — | URL正确（chatglm.cn 为智谱清言官方站）。定价编造：站内“免费版+Pro $10/月”无依据，真实为人民币计费（标准版50元/月、大会员99元/月、 |

## P4 其余字段幻觉（platform/description 等）（9 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | cleanvoice | platform | medium | — | 平台写『Web / iOS / Android』，但 Cleanvoice 为纯网页应用（app.cleanvoice.ai），无 iOS/Android Ap |
| 2 | jsdesign-ai | platform | medium | — | 官网正确，即时设计为浏览器云端工具，无本地部署版本，'本地部署 / Web'中'本地部署'错误。基础功能免费，价格描述正确。 |
| 3 | krea-ai | platform | high | — | 官网真实。platform字段'本地部署'错误：Krea AI为云端Web实时工具，无本地部署。价格存在来源冲突（官方页Pro $35，另有来源Pro $10） |
| 4 | leonardo-ai | platform | high | — | 官网真实。但platform字段'本地部署'错误：Leonardo AI为云端Web平台，不支持本地部署（内容自身亦描述为Web）。来源：leonardo.ai |
| 5 | make | platform | high | — | Make（原 Integromat）为纯云可视化自动化平台（现属 Celonis），不支持本地部署，platform 字段'本地部署 / Web'错误。官网显示 |
| 6 | n8n | platform | medium | — | n8n 无官方 iOS/Android 应用（仅有第三方社区应用如 N8Ninja 等），官方定位为 Web 平台（云托管/自托管）。platform 字段'W |
| 7 | photoroom | platform | high | — | 官网正确，为云端SaaS+移动端(iOS/Android)，无本地部署。'本地部署 / Web'中'本地部署'为错误归属。有免费版，价格描述基本成立（Pro约£ |
| 8 | quillbot | platform | high | — | 平台标注「本地部署 / Web」错误：QuillBot 为云端 SaaS，不支持本地部署。价格字段写「免费使用」表述片面——实际有免费版（$0）+ Premiu |
| 9 | weaviate | platform | medium | — | platform 字段写“Web/桌面/移动端支持”不准确：Weaviate 是服务端向量数据库，通过 API/SDK（Python/JS/Go/Java）及云 |

## P5 冲突项人工裁定（21 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | 6pen-art | - | medium | — | 官网 6pen.art 仍可访问但已发布停运公告('是时候说再见了')，引导迁移至 6pen Pro(6pen.pro)；文中'2026年最新版本增强了可控生成 |
| 2 | apache-superset | - | medium | — | 产品属实，开源免费（Apache 基金会），描述与正文核心功能（拖拽仪表盘、SQL Lab、40+ 图表、多数据源）均准确。但'2026 年增强 AI 驱动自然 |
| 3 | chuchu-ai | - | medium | ✅ | 官网 URL 错误：chuchuai.com 无法访问且非官方域名，真实官网为 acgnai.art（现迁移至 chushou.art）。功能(文生图/图生图/ |
| 4 | coda-ai | - | medium | — | 官网 coda.io 确认 Coda AI 为文档协作平台的 AI 助手（AI chat / assistant / AI column，600+ 集成），功能 |
| 5 | elicit | - | medium | — | 官网为同一产品（Elicit 论文研究助手，Ought/Elicit 出品），免费版 + Plus 约 $10/月价格基本准确，功能描述（读论文、提取信息、文献 |
| 6 | eqxiu | - | low | — | 官网eqixiu.com为正常运营的易企秀(北京中网易企秀科技)，功能描述(H5/海报/PPT/AI生成)与官方一致。定价“会员39元/月起”无法与官方清晰对应 |
| 7 | feishu-smart-partner | - | medium | — | 官网 feishu.cn 确为字节跳动飞书办公套件，公司/产品归属正确。但当前官网未出现“智能伙伴”这一命名（现有AI产品为飞书aily、知识问答、智能会议纪要 |
| 8 | figma-for-agents | - | low | — | 官网figma.com/agents确为Figma 2026年推出的AI智能体(面向设计师、集成于画布、可生成布局/批量编辑/评论转设计)，在专业版/组织版/企 |
| 9 | gamma | - | low | — | 官网有效，功能（AI演示/PPT生成）描述准确。但Pro月价各来源差异较大（$16–$25/月不等），官方价格页未直接展示固定数字；站内写"Pro $16/月" |
| 10 | graphify | - | low | — | 官网graphify.ai确为数据可视化/KPI工具，但/pricing页返回404，首页仅提real-time updates/dynamic visuali |
| 11 | headlime | - | low | — | 官网仍可访问且为 Headlime 官方站（未跳错站），但页面为遗留营销页、无清晰现行定价。Headlime 已于早前与 Conversion.ai（现 Jas |
| 12 | huiwa | - | low | — | 官网 huiwa.cn（多次抓取超时，但被多家站点列为官方域名；另有 ihuiwa.com 及淘宝子域 huihua.taobao.com）为阿里巴巴旗下电商  |
| 13 | lingban-ai | - | medium | — | 官网 ilingban.com WebFetch 失败，经 WebSearch 确认 ilingban.com 为官方域名且正常存在；其为浏览器插件形态 AI  |
| 14 | lottiefiles-ai | - | low | — | 官网 /ai 页面未展示任何定价数字（LottieFiles 定价页被 Cloudflare 拦截，无法核实站内“付费版$19/月起”）。功能方面：文字生成 L |
| 15 | mem-ai | - | medium | — | 官网 mem.ai 确认 Mem 为 AI 笔记/知识管理工具（Mem Workspace + Agent，自动关联笔记、构建知识上下文），由 Mem Labs |
| 16 | moyin-gongfang | - | low | — | URL moyin.com可访问且确实指向魔音工坊（短视频/有声书AI配音平台），非错误站点。但定价'付费版每月29元起'与官网SVIP会员48-68元/月存在 |
| 17 | officecli | - | medium | ✅ | 站内URL officecli.com 为域名出售/停放页（标价$58,888），并非产品官网。真实官网为 officecli.ai（GitHub: iOffi |
| 18 | qik-office | - | medium | — | 官网 qikoffice.com 确为“AI Office”（部署AI项目经理与Agentic Rooms），核心与“AI办公平台”相符，“文档生成/数据分析/ |
| 19 | resemble-ai | - | low | — | 官网resemble.ai已转型为'生成式AI安全/深度伪造检测'平台，但语音克隆/TTS仍是其核心产品（'5秒克隆'、98种语言、实时语音转换、情感控制、AP |
| 20 | scalenut | - | low | — | 官网URL正常（scalenut.com）。但官网定位已转型为『AI + 专家托管式 GEO 服务』（强调 Book a call / 人工策略师），自助式 S |
| 21 | wujie-ai | - | low | — | 官网 wujieai.com 现已转型为'桌面级 AIPC 智能体'(绘图Agent/写作Agent/本地算力)，不再是纯网页端 AI 绘画平台；文中'平台:网 |

## P6 低/中置信复核（62 项）

| # | slug | 字段 | 置信 | URL已修 | 备注 |
|---|------|------|------|---------|------|
| 1 | ada-health | - | medium | — | 官网域名正确，开发方 Ada Health GmbH（柏林）属实，症状评估/就医建议功能正常。专业版$9.99/月处于官方区间（$5–$10/月）上限，基本合理 |
| 2 | adobe-firefly | - | medium | — | 官网真实。含免费档，但另有Premium($4.99/月)。'免费使用'表述偏简略，但免费档属实，不判幻觉。 |
| 3 | aiva | - | medium | — | 官网aiva.ai可访问且确为AIVA。定价官网为欧元：Free €0、Standard €11/月（年付）、Pro €33/月（年付，含VAT）；数据写'付费 |
| 4 | anijam | - | low | — | 官网正常（Anijam - AI Animation Agent，输入创意/故事生成动画）。描述'将静态图片转动态视频'及姿态控制/风格迁移/多角色动画等功能在 |
| 5 | augment-code | - | medium | — | 官网正确（augmentcode.com，AI编程助手，强调代码库上下文理解/Cosmos智能体编排，支持 VS Code/JetBrains 等）。描述与其定 |
| 6 | baichuan-ai | - | medium | — | 官网（baichuan-ai.com）真实，创始人王小川（前搜狗CEO）属实。API单价 Baichuan4-Air ¥0.00098/千token（官网称0. |
| 7 | beatoven-ai | - | medium | — | 官网付费档约$10/月（Creator）至$20/月（Visionary），另有$3/分钟按量付费；数据写'付费版$19/月起'处于区间内，基本可接受。免费试用 |
| 8 | browser-act | - | medium | — | BrowserAct 确为 2026 年发布的 AI 网页抓取/自动化工具（从一句话生成可复用爬虫，支持 Make/n8n/Zapier 集成），descrip |
| 9 | browser-use | - | medium | — | Browser Use 确为开源浏览器自动化框架 + 云（stealth browsers 从 $0.02/hr 起），description 准确。price |
| 10 | capcut-ai | - | medium | — | 官网正确(capcut.com)。短期price"基础$10/月起"基本可接受：官方 Standard $9.99/月、Pro $19.99/月（capcut. |
| 11 | chatgpt | - | medium | — | 官网URL(chat.openai.com)为OpenAI官方旧域名，仍可用，现规范域名为chatgpt.com；定价Plus $20/月属实(来源:OpenA |
| 12 | claude | - | medium | — | claude.ai为Anthropic官方站；Pro $20/月(月付)属实(来源:claude.ai定价页)。Claude 4系列/Sonnet 5/Fabl |
| 13 | cognition-ai | - | medium | — | 官网 cognition.ai 是 Cognition 公司站，实际产品为 Devin；所写功能与定价(Pro $20/Max $200/Teams $80)均 |
| 14 | cosy-voice | - | medium | — | URL为阿里FunAudioLLM官方开源仓库，正确。CosyVoice是阿里通义实验室开源TTS，可经阿里云百炼(DashScope)API按量付费调用，'企 |
| 15 | deepseek | - | medium | — | deepseek.com为官方站，'免费额度可用，API按token计费'模式属实(来源:官网)。V4 Pro等版本号无法核实，未判定为幻觉。 |
| 16 | elevenlabs | - | medium | — | 整体准确。Starter 官网月费 $6（年付等价 $5），站内写 $5/月可视为年付价；Pro 积分官网 600k（站内写 50万）、Creator 官网 1 |
| 17 | framer-ai | - | low | — | 官网正确。Framer有免费版；付费起步 Basic 约 $9/月(SGD 12)、Pro 约 $26/月(SGD 35)，美元区Pro常见$15/月。'$15 |
| 18 | freepik-ai | - | medium | — | 官网真实。price'基础$10/月起'近似Premium约€10.83/月（$11-12），属合理近似，不判幻觉。 |
| 19 | hailuo-ai | - | medium | — | 官网正常（跳转至 MiniMax 站，海螺AI 为 MiniMax/稀宇科技 产品）。文生视频/图生视频/智能对话/图像生成等多模态能力与描述一致。'视频生成质 |
| 20 | haystack | - | medium | — | 官网 haystack.deepset.ai 正确（deepset 出品，德国公司）。开源免费 + 付费企业版属实（现品牌为 deepset Studio /  |
| 21 | hedra | - | low | — | 官网 https://www.hedra.ai 可访问，确为基于 Character-3 模型的角色/口型同步视频工具，description（角色视频、口型同 |
| 22 | hippocratic-ai | - | medium | — | hippocraticai.com 为真实官网，专注医疗健康生成式 AI Agent（非诊断/非处方，强调安全合规），企业级 B2B 定价，与描述总体一致。需注 |
| 23 | internlm | - | medium | — | GitHub仓库 github.com/InternLM/InternLM 为上海人工智能实验室官方仓库，属实。InternLM 3为真实版本。价格「基础版免费 |
| 24 | invideo-ai | - | medium | — | 官网正常（invideo.io，现主推 Agent One AI 视频平台）。定价量级合理：站内称'付费版$15/月起'，第三方2026年资料显 Plus 约  |
| 25 | jenni-ai | - | medium | — | 价格完全吻合官网：Free（10 次 AI 补全/天）、Plus $12/月、Pro $29/月。功能（学术写作/改写/查重/语法检查/多语言）与官网一致。平台 |
| 26 | julius-ai | - | medium | — | 官网为数据分析工具，功能描述（自然语言问数据、代码生成、可视化、数据清洗）准确；付费版约 $20/月起（站内写 $19/月，接近，仅微差），无明显幻觉。『202 |
| 27 | kimi | - | medium | — | kimi.moonshot.cn为月之暗面官方站，免费可用属实；200万字上下文为Kimi标志性能力。K3(2.8T参数)等版本号无法核实，未判定为幻觉。 |
| 28 | kling-3-0 | - | low | — | 官网 https://kling.kuaishou.com 可访问（跳转 klingai.com），确为快手可灵 AI 视频生成工具，description（快 |
| 29 | kling-ai | - | medium | — | 官网正确(klingai.kuaishou.com，确为快手旗下)。短期price"免费使用"表述不完整：可灵有免费额度但也存在会员/付费档，非纯免费；未作为虚 |
| 30 | lumen5 | - | medium | — | 官网正常（lumen5.com），确为文本/博客转视频平台。定价基本吻合：站内称'专业版$19/月起，企业版定制'，官方最低付费 Basic $19/月、Sta |
| 31 | meitu-design-ai | - | medium | — | 功能（AI海报、商品图背景替换、AI模特试穿、智能抠图、批量详情页）与官网一致。会员29元/月未在公开页面确认，建议人工复核定价。 |
| 32 | meticulous | - | low | — | 官网 meticulous.ai 正常，AI 驱动 UI 测试自动化、自动生成测试描述准确；定价不透明（官网仅'预约演示'），第三方来源有 $25/$99/$3 |
| 33 | microsoft-copilot | - | medium | — | copilot.microsoft.com为有效官网，网页版Copilot免费、Copilot Pro $20/月属实，无定价幻觉。唯一瑕疵：正文"基于GPT- |
| 34 | mintlify-editor | - | low | — | 官网正确（mintlify.com 为官方站）。产品定位准确：Mintlify 是文档平台，2026年确已推出面向团队与智能体的协作式 Editor（官方博客  |
| 35 | modelscope-agent | - | medium | — | 基本正常。官网(阿里魔搭 modelscope.cn)与描述/内容一致：开源 Agent 框架、多模型编排、工具调用、记忆管理、免费开源。仅 platform  |
| 36 | moonvalley | - | low | — | 官网 https://moonvalley.ai 可访问，确为 AI 视频生成工具（现主打 Marey 模型，支持文生/图生视频），“由前 DeepMind 团 |
| 37 | pear-ai | - | medium | — | 官网正确（trypear.ai，开源AI代码编辑器，对标 Cursor，基于 Roo Code/Cline + Continue，支持代码生成/对话/Agent |
| 38 | persona-js | - | low | — | persona.js.org 是 Persona.js 的 js.org 官方子域名（跳转至官网 persona-chat.dev），产品真实：Runtype  |
| 39 | pika | - | medium | — | 官网正确(pika.art)。短期price"免费版+标准$10/月"准确(Standard $10/月)。但内容表写 Pro $30/月，官方实际 Pro 为 |
| 40 | pixso-ai | - | medium | — | 功能（文生图、AI抠图、智能擦除、生成图标、生成UI组件、设计稿转代码 ArkUI/HTML/SwiftUI/Vue）与官网一致。会员29元/月未在公开页面确认 |
| 41 | qwen3-coder-next | - | low | — | tongyi.aliyun.com/qianwen 为真实阿里通义千问站点，但页面展示的是通用千问助手（截屏问答、语音输入法等），未能核实『Qwen3-Code |
| 42 | ragflow | - | medium | — | 官网 ragflow.io 正确（InfiniFlow 出品）。开源免费 + 云端/企业版付费属实（RAGFlow Cloud 提供订阅），描述无明确幻觉。注： |
| 43 | read-ai | - | medium | — | 功能描述与正文准确（AI 会议助手：摘要/转录/智能阅读/Ask Read 跨会议邮件文档检索）。URL 正确。定价 $19/月起未逐项核实官网，存疑但不判幻觉 |
| 44 | recall-ai | - | medium | — | 官网 getrecall.ai（跳转 recall.it）为 AI 知识库/摘要工具，与描述一致。定价：Free（每月 10 次 AI 摘要）+ Plus 约  |
| 45 | respeecher | - | medium | — | 官网respeecher.com确认，产品为专业级AI语音克隆/TTS（情感保留、被好莱坞/顶级播客采用均属实）。定价'企业定制'正确（官网另有TTS API按 |
| 46 | riffusion | - | medium | ✅ | 数据URL riffusion.com抓取两次均返回'Google Flow Music'（错误站点），非Riffusion内容，属跳转/失效错误；Riffus |
| 47 | sembly | - | medium | — | 官网 sembly.ai 确为AI会议助手（自动转录、摘要、行动项、48种语言、接入Zoom/Teams等），与描述高度一致。定价“免费版可用，专业版$10/月 |
| 48 | sensenova | - | medium | ✅ | 官网域名错误：存储url为platform.senseNova.com，商汤官方隐私政策明确官网为 platform.sensenova.cn（.cn而非.co |
| 49 | spline-ai | - | medium | — | 官网确认文字/图像转3D、AI纹理生成等功能，与站内基本吻合。定价“Pro版$12/月起”对应官网 Starter $12/月（Spline AI 为 +$5  |
| 50 | tabnine | - | medium | — | 官网 tabnine.com 正常；Dev $9/月（年付）与当前官网一致，免费版亦存在（2026 多来源引用）。注：Tabnine 已转向企业定价（Code  |
| 51 | tencent-docs-ai | - | medium | — | 官网 docs.qq.com 确认腾讯文档 AI 助手（基于混元大模型，智能写作/续写/总结/翻译，全品类文档生成），平台（网页/Windows/Mac/iOS |
| 52 | tencent-hunyuan | - | medium | — | 正常。官网 hunyuan.tencent.com；描述中 Hy3（295B 参数 MoE、Apache 2.0 开源）与搜索结果（2026-07 上线、295 |
| 53 | tome | - | medium | — | 官网有效（tomeapp.ai）。当前最低档Starter约$9.5/月，站内"基础$10/月起"基本吻合；功能（AI演示/叙事/图片生成/动效）准确。注意：正 |
| 54 | tongyi-lingma | - | low | — | 官网正确（阿里云通义灵码，基于通义大模型，2.0版本确有其事，与描述一致）。功能描述准确。但'专业版¥59/月'未在本次抓取官网页直接核实（官网仅明示个人免费、 |
| 55 | veed-io | - | medium | — | 官网正常（veed.io），确为在线AI视频编辑平台（字幕/剪辑/降噪等）。定价基本属实：站内称'付费版$12起/月'，官方现档 Creator €11/月（≈ |
| 56 | veo | - | low | — | 官网正确(deepmind.google/technologies/veo)。短期price"基础$10/月起"存疑：Veo 常规通过 Gemini Advan |
| 57 | vidu-2-0 | - | low | — | 官网 https://www.vidu.studio 可访问（导向 vidu.cn），确为生数科技 Vidu AI 视频工具，description 准确。co |
| 58 | vidu-ai | - | medium | ✅ | URL 疑似错误：www.vidu.ai 实际展现的是'面向销售团队的 AI 个性化视频外联'产品（不同公司/不同产品），而生数科技（联合清华）推出的 Vidu |
| 59 | wensi-ai | - | low | — | 官网可访问（显示为『文思助手』，AI写作助手/智能写作/公文写作），与站内描述（国产AI智能写作助手）一致。价格仅写『免费版/专业版』无具体数字，未构成可判定编 |
| 60 | wondershare-virbo | - | medium | — | 官网正常，产品/公司（万兴科技 Wondershare）/功能与描述基本吻合（AI数字人、TTS、多语言配音、智能剪辑）。定价'付费版¥99/月起'在首页仅见' |
| 61 | workbuddy | - | medium | — | 官网URL正确，确为腾讯出品的AI办公智能体（官网标题'WorkBuddy - AI Agent 办公新范式'，页脚地址'深圳市南山区科技中一路腾讯大厦'，与描 |
| 62 | xinghuo-cognitive-model | - | medium | — | 官网（xinghuo.xfyun.cn，科大讯飞）真实，星火4.0版本属实（官网提及4.0 Ultra）。免费版+付费专业版模式符合官方。（来源：讯飞星火官网） |

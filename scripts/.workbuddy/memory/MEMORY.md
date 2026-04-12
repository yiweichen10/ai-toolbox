# aitoolbox 项目记忆

## 项目概况
- **中文站**：www.aitoolbox.hk（AI工具导航站，当前在用）
  - 目录：`C:\Users\27040\WorkBuddy\20260321092139\seo-site`
  - 技术栈：纯静态HTML + Python构建脚本
  - 数据源：data/tools.json（工具数据）、data/articles.json（文章数据）
  - 构建：scripts/build.py 生成静态页面
- **英文站**：独立项目（2026-04-11独立出去，目前还是中文站点待迁移）
  - 目录：`C:\Users\27040\WorkBuddy\20260321092139\seo-site-en`
  - 独立系统控制，与中文站分开管理

## 重要事件
- **2026-03-24**：抓取了80个新AI工具，但被 git revert (cebc7ed) 回滚删除
- **2026-03-25**：从 commit 6635e5a 恢复了80个工具数据，重新发布3个工具（Claude Code, Fireflies.ai, Coze）
- **2026-03-25**：SEO 全面优化（详见 2026-03-25.md）
  - HTML 语义化修复（ul 包裹 li）
  - 批量生成 176 张 SEO 图片（OG + 信息图）
  - 100 个工具 content 扩充至 1200+ 字符
  - URL 规范化（去掉 index.html 后缀）
  - 首页工具数量动态化
  - publish_new_tools.py 打通自动 git commit + push
- 当前状态：100个工具（37个已发布，63个待发布）
- **2026-03-27**：自动发布 OpenAI Codex, Tensor.Art, Otter.ai（commit 912584a）
- **2026-03-29**：自动发布 天工AI, DALL-E 3, 秒画（commit 5bb9efc），当前35个已发布/65个待发布
- **2026-03-30**：手动发布 DeepSeek 和 Poe（commit 4ab160d），自动发布 QuillBot, Leonardo AI, You.com（commit 09d1545），当前40个已发布/60个待发布
- **2026-03-29**：SEO紧急修复（commit f55ae49）
  - 全量修正79个虚假URL（www.工具名.com → 真实官网）
  - 修复65个工具content中引用的虚假URL
  - 重写94个工具的FAQ（替换模板化垃圾内容为有价值针对性内容）
  - **严重教训**：绝不能猜测或想象URL，所有工具的官网URL必须基于搜索确认的真实地址

## 注意事项
- 百度推送API配额已用尽（400 over quota），需要等配额恢复
- publish_new_tools.py 每天13:00自动发布3个工具
- publish_new_tools.py 已支持自动 git commit + push，Vercel 会自动部署
- 所有 URL 使用 clean URL 格式（不含 index.html），sitemap/canonical/og:url 统一规范
- **URL合规红线**：tools.json中所有工具的url字段必须是真实可访问的官网地址，禁止使用 `www.工具名.com` 格式的猜测URL。添加新工具时必须通过搜索引擎确认真实官网
- **slug合规红线**：所有工具的slug字段必须是纯小写英文+数字+短横线（如 `tencent-yuanbao`），禁止包含中文字符。generate_tools.py 已增加正则校验，非英文slug会自动fallback

## 内容生成策略（2026-04-11确定）
- **中文站默认模型**：Pro/MiniMaxAI/MiniMax-M2.5（质量4星、速度19.6秒、成本0.012元/篇）
- **英文站默认模型**：Pro/zai-org/GLM-5（质量5星、速度79.6秒、成本0.077元/篇，Pros/Cons结构最强）
- **英文站备选**：GLM-5.1（质量5星、¥0.10）、Kimi-K2.5（质量5星、¥0.084）、MiniMax-M2.5（质量4星、¥0.012）
- **中文站备选**：GLM-5.1（质量5星但贵8倍）、Kimi-K2.5（质量5星但贵7倍）
- **content prompt要求**：禁止虚构数据/经历/时间线，语气自然松弛，内容简洁不凑字数
- **已淘汰**：DeepSeek-V3.2（字数失控、信息冗余、书面腔）
- **Agent不用于批量生成**：成本是API的7倍（0.59元/篇），用于特殊内容（深度测评、有观点的对比页、竞品对比需时效性的内容）
- **API模型通病**：训练数据有截止日期，可能产出过时的竞品信息（如GLM-5提到"Claude 3.5 Sonnet"实际已到Claude 4.x）
- generate_tools.py 工具名列表已扩充至60+个（2026-04-11更新）

## 英文站独立说明（2026-04-11）
- 英文站已从中文站项目中独立，目录：`C:\Users\27040\WorkBuddy\20260321092139\seo-site-en`
- 中英文站独立系统控制，各自有独立的构建脚本、自动化任务、发布流程
- 英文站内容**禁止翻译中文站**，需用英文模型独立生成

## 域名状态（2026-04-11）
- **www.aitoolbox.hk**（中文站当前域名）：线上在用，代码中统一使用
- **aitoollab.cn**：ICP备案中，预计4/17通过，备案通过后从aitoolbox.hk迁移
- **英文站域名**：待确认（目前内容还在中文站下，Phase 3部署后迁移到 aitoollab.hk）
- ⚠️ **域名红线**：代码中域名统一用 `www.aitoolbox.hk`，不要写成 `aitoollab`（少了x）

## SEO文章生成流程（2026-04-11优化）
- gen_article_api.py 默认模型：MiniMax-M2.5
- 新增 `--keywords` 参数：接收Agent核实过的真实关键词（格式：核心词|长尾词1,长尾词2）
- 关键词优先级：Agent预置 > API自行输出 > fallback提取
- **SEO关键词不凭空编**：每次生成文章前，Agent应通过搜索核实关键词搜索量
- 不强制控制字数/每段字数，改为"简洁有力不凑字数"自然引导

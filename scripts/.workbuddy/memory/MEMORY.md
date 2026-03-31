# aitoolbox.hk 项目记忆

## 项目概况
- 网站：aitoolbox.hk（AI工具导航站）
- 技术栈：纯静态HTML + Python构建脚本
- 数据源：data/tools.json（工具数据）、data/articles.json（文章数据）
- 构建：scripts/build.py 生成静态页面

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

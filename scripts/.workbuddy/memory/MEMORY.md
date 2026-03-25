# aitoolbox.hk 项目记忆

## 项目概况
- 网站：aitoolbox.hk（AI工具导航站）
- 技术栈：纯静态HTML + Python构建脚本
- 数据源：data/tools.json（工具数据）、data/articles.json（文章数据）
- 构建：scripts/build.py 生成静态页面

## 重要事件
- **2026-03-24**：抓取了80个新AI工具，但被 git revert (cebc7ed) 回滚删除
- **2026-03-25**：从 commit 6635e5a 恢复了80个工具数据，重新发布3个工具（Claude Code, Fireflies.ai, Coze）
- 当前状态：100个工具（23个已发布，77个待发布）

## 注意事项
- 百度推送API配额已用尽（400 over quota），需要等配额恢复
- publish_new_tools.py 每天13:00自动发布3个工具
- **重要**：publish_new_tools.py 只生成本地文件，不会自动 git commit/push。Vercel 需要 push 才部署。手动发布后必须 commit + push！

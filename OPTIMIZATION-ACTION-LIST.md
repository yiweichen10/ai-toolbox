# 优化行动清单（综合百度 + Bing 数据，2026-08-13）

> 数据来源：百度统计 2026-07-15 ~ 08-13（103,564 PV / 80,732 UV / 跳出率 94.17%）+
> Bing Webmaster 同期（Bing 占 73% 流量，AI 搜索引用日均 7,591 次）。
> 按执行顺序排列；✅=本地已完成（待部署生效），⏳=待办，❓=待决策。

## 阶段 0：度量与数据底座（先做，否则后续优化无法验证效果）

- [x] 0.1 百度统计配置转化目标（2026-08-14 已完成）：页面转化"收藏工具页"（favorites.html）、
      时长转化 30 秒、页数转化 3 页。注：事件转化自 2022 年起平台不再支持新增（trackevent），
      立即使用/CPS 点击等事件只能走"分析→事件分析"（需付费权限）
- [ ] 0.2 百度统计开启"站内搜索统计"，查询参数填 `q`（⏳ 需付费"分析"权限，暂缓）
- [x] 0.3 百度统计排除本地/办公 IP（2026-08-14 已完成）：排除 220.166.10.94 + 127.0.0.1 +
      localhost 开关；另完成统一页面地址（http://aitoollab.cn → http://www.aitoollab.cn）
- [x] 0.4 百度索引量确认（2026-08-13：7/22~8/12 每日仅 0~4 页被收录，最新 4 页——百度基本未收录）
- [ ] 0.5 部署上线后等 Bing 重爬（IndexNow 会自动通知）
- [x] 0.6 全站统计代码补齐（2026-08-14）：构建新增 `inject_baidu_tongji` 后处理，
      119 个手工静态页/模板页补齐 hm.baidu.com 代码（此前 favorites/about/contact 等全缺，
      导致转化目标页无法统计）

## 阶段 1：技术修复（已完成，待部署）

- [x] 1.1 对比页"更多相关对比"只链接真实存在的对比页（消除 ~110 个 4xx 死链源头）
- [x] 1.2 排行页过滤未发布工具（6 个榜单、10 个工具不再产生死链）
- [x] 1.3 排行页 quiz 链接统一为 `/quiz/`（19 个页面，原链接指向不存在的 `/quiz/ai-tool-finder-2026/`）
- [x] 1.4 `/ranking/` 移除 Meta Refresh（改为真实栏目页）
- [x] 1.5 静态页双 h1 → 单 h1：about / contact / privacy / links / 404 / author
- [x] 1.6 contact / privacy / links 补 Meta Description
- [x] 1.7 cms / favorites / tools 模板页 / 备份页加 noindex
- [x] 1.8 sitemap 补齐 6 个枢纽页：ranking / compare / alternatives / articles / author / live
- [x] 1.9 修复构建 bug：`-t all --no-push` 之前不生成 sitemap、坏链清理只在推送时执行
- [x] 1.10 `/tools/{slug}/index.html` 等非规范内链自动规范化
- [x] 1.11 部署上线（2026-08-13 已完成，线上闭环验收通过）
- [x] 1.12 修复 deploy.sh 强制同步目录名 bug（compares/quizzes→compare/quiz，补 author），
      否则对比页/quiz/author 三类页面从不被同步上线

## 阶段 2：流量承接（最大杠杆：文章占 79% 流量、退出率 93.5%）

- [x] 2.1 文章页正文上方新增"本文提到的工具"横排卡（TL;DR 之后、正文之前，移动端可见；320/390/768/1280 四视口布局验证通过）
- [x] 2.2 高流量文章"立即使用"CPS 卡片（机制已存在：文章页侧边栏+移动端正文第4段后由 ads/loader.js 注入，已随部署上线，等统计数据验证效果）
- [x] 2.3 工具页 + 全站描述优化（所有可索引页面描述 ≥110 字，工具/对比/替代/分类/排行/quiz/词典/快讯/live/栏目页全覆盖）
- [x] 2.4 文章正文自动嵌入相关工具内链（`inject_internal_links` 已在文章/工具页构建中生效）

## 阶段 3：Bing 技术优化

- [x] 3.1 长标题瘦身：85 篇文章新增 `seo_title`（≤60 字符，Bing 清单 30 篇 + 全站超长 55 篇），
      仅替换 <title>/og:title/twitter:title，H1 保持不变
- [x] 3.2 Meta 描述过短全站修复（阈值统一到 115，含数据描述门槛 100→115、文章/词条补足阈值 90→115、枢纽页模板补长）
- [x] 3.3 2 篇孤儿文章处理：评估后均不值得保留，文件已移入 `.cleanup_backup/orphan-articles-20260813/`
- [x] 3.4 4 个旧文章 URL 服务器 301 已上线（`/etc/nginx/conf.d/old-url-redirects.inc`，含 backup 可回滚，curl 验证 4 条均 301 指向新地址）
- [x] 3.5 外链建设 · 半自动选文已落地（2026-08-14）：`scripts/backlink_daily_pick.py`
      每日自动选 3 篇高价值文章（时效+质量+教程评测加权，7 天内不重复），生成公众号/知乎/CSDN
      三种格式的"标题+推荐语+摘要+标签"推送文案到 `backlink_push_queue/YYYY-MM-DD.md`；
      Windows 任务计划 `aitoollab_backlink_pick` 已建（每日 09:30）。推送动作仍需人工
      复制到各平台（平台 API 差异与风控），属半自动；各平台接入 API 后再自动化（待办）

## 阶段 4：内容策略（放大 AI 引用这一增长引擎）

- [ ] 4.1 强主题加固：MCP（浏览器 MCP 引用份额 41%）、DeepSeek 价格/涨价、剪映 AI、本地部署、AI 编程工具榜
- [x] 4.2 机会主题补内容 · 既梦 AI（2026-08-14 已上线）：
      `jimeng-ai-complete-guide-2026`（即梦 AI 完全教程：图片/视频/数字人全流程与会员价格），
      内容含智能画布/Seedance 2.0→2.5/数字人对口型/可灵对比/2026 会员调价时间线，数据附来源，
      线上 200 验证通过
- [ ] 4.2 机会主题补内容 · 待产出：cursor ai（引用 3,107 次、份额仅 0.51%）、zcode（1.88%）、
      阿里禁用 Claude、泛词 ai工具、comet 教程
- [x] 4.3 新文章标题规则 ≤60 字符写入 AGENTS.md
- [ ] 4.1/4.2 内容产出（选题大纲已就绪，见 `CONTENT-PLAN-2026-08.md`，逐篇产出时需人工审核质量与数据可溯源）
- [ ] 4.4 comet 教程类内容缺口（百度搜索词里 10+ 次相关搜索，站内只有工具页没有教程）

## 阶段 5：留存与转化

- [x] 5.1 收藏与 PWA 安装引导已具备（收藏按钮+收藏页+浏览器原生安装提示，用户实测有效）；
      邮件订阅引导不在其中（静态站无后端，可选项）
- [ ] 5.2 老访客仅 6.44%：重量版方案 = 邮件订阅（2026-08-14 用户确认）
      - 已完成：方案设计 + 可启用表单模板 `scripts/templates/email_subscribe_form.html`
        （只留邮箱字段、暗色兼容、订阅钩子"每周精选实测"）
      - 待办（需用户决策/注册）：选择第三方邮件服务商后接入——
        方案A 免费起步：Buttondown（免费前100订阅）/ Mailchimp（免费500联系人）；
        方案B 国内稳定：阿里云邮件推送 DirectMail / 腾讯云 SES（需域名验证+表单网关）。
        服务商定好后按模板注释三步接入，部署后必须实测"订阅→收确认邮件→列表可见"闭环

## 阶段 6：百度战略（照旧，等索引量数据）

- [x] 6.1 百度战略结论已定（索引量 1~4 页）：短期资源押 Bing/AI 引用，
      百度仅保持基础维护（推送/sitemap/robots），待权重积累后再评估
- [ ] 6.2 百度推送状态核查（`.baidu_pushed.json` 有记录但收录≈0，需确认推送是否真的生效）
- [ ] 6.3 百度统计付费"分析"权限（⏳ 用户决定暂不付费，待办，属后期事项；
      涉及：站内搜索报告、事件分析、分析模块全部报告）

---

## 附录 A：4 个旧文章 URL 的来龙去脉

| 旧 URL | 产生时间 | 现状 | 建议 |
|---|---|---|---|
| `/articles/microsoft-build-2026-mai-thinking-seven-ai-models/` | 2026-06-11 | 已改名 `microsoft-build-2026-mai-thinking-1-seven-models-0603`（标题一致） | nginx 301 |
| `/articles/2026-ai-coding-tools-30-tools-cost-guide/` | 2026-06-11 | 已改名 `ai-coding-tools-guide-2026`（标题一致） | nginx 301 |
| `/articles/2026-ai-coding-tools-comparison-guide/` | 从未存在（仅出现在其他文章的相关阅读链接里） | 实际对应 `ai-coding-tool-selection-guide-2026`（标题完全一致："2026年AI编程工具选择指南"） | 301 到 `ai-coding-tool-selection-guide-2026` |
| `/articles/deepseek-v4-pro-permanent-price-drop-202605/` | 2026-05 前后 | 已改名 `ai-model-api-pricing-shakeup-may-2026-deepseek-cursor-qwen`（标题一致） | nginx 301 |

根因：6-7 月内容重构时改动 slug，违反"URL 不可变"规则，旧 URL 直接 404，
Bing 索引里残留 → 报 4xx。内容并没有删除，只是换了地址。

## 附录 B：2 篇孤儿文章

- `ai-beginner-tools-0409`（"AI编程工具从入门到精通：一份保姆级工具地图"，2026-04-09，约 3800 字）：
  当天发布即被 revert；内容与现有 `ai-coding-tool-selection-guide-2026`、`ai-coding-assistant-recommend-2026`
  高度重叠，且时效性已过（4 月文）。
  **结论：不值得保留**，建议清理本地文件。
- `ai-review-ai-office-202607`（"2026年7月AI办公工具评测：4款工具同维度实测"，2026-07-02，约 1500 字）：
  已被 `ai-review-ai-office-202607-refreshed`（同题新版，4730 字，数据更新至 7 月）取代。
  **结论：不值得保留**，是被新版本替换后未清理的旧稿，建议清理本地文件。

# AGENTS.md - AI工具宝箱（aitoollab.cn）项目规则

## 项目是什么

AI 工具导航 + 评测静态站。纯静态站点：所有页面（首页 / 工具详情 / 文章 / 分类 / 排行 / 对比 / 词典 / 快讯等）都由构建脚本从 `data/*.json` 生成，前端辅助 JS（搜索、收藏、暗色、TTS、AI 助手）做交互。

## 一图流：数据流

```
data/*.json（工具/文章/对比/排行/词典/快讯）
    │  scripts/build.py（SSG 构建，唯一出口）
    ▼
静态 HTML（根目录 index.html、tools/、articles/、category/ 等）
js/tools-data.js（首页工具数据，构建时由 build.py 生成）
```

## 常用命令（在仓库根目录执行）

- 全量构建：`python scripts/build.py`（默认 `--target all`，构建完会推送 sitemap/IndexNow，慎用）
- 只构建 HTML 不推送：`python scripts/build.py -t none`
- 全量重建但不推送（本地验证推荐）：`python scripts/build.py -t all --no-push`（注意：`-t none` 只做后处理注入，不重建页面）
- 增量构建单个 slug：`python scripts/build.py -s <slug>`
- 指定目标：`-t articles|tools|index|news|dict|ranking|live|pseo|sitemap`
- 本地预览：`python scripts/dev_site_server.py 8090`，然后访问 http://127.0.0.1:8090/
- 改 CSS 后：`python scripts/optimize_css.py`（生成 style.min.css 与 critical CSS）
- 部署：`bash deploy.sh`（内部会先 regenerate_data + optimize_css + build）
- 只发一篇文章（增量，快）：`bash deploy_fast.sh <slug>`（2026-08-28 新增；`--dry-run` 只构建+门禁+列清单）
- AI 助手后端（可选，本地聊天用）：`python ai_assistant/server.py`（端口 8123）

> ⚠️ **Windows 编码铁律（2026-08-09 起机制化，别再踩）**：Windows 控制台默认 GBK，
> Python 打印 emoji/中文（✅、🎉、中文日志）会抛 UnicodeEncodeError 中断执行。
> - `deploy.sh` 已内置 `PYTHONIOENCODING=utf-8`，部署链路无需再手动设置，**不要删那两行**；
> - `scripts/build.py` / `regenerate_data.py` / `optimize_css.py` 已内置 stdout 兜底，直接运行也不崩；
> - 其他脚本（inject_ads.py / fix_css_refs.py 等）若直接运行报编码错，先设
>   `$env:PYTHONIOENCODING='utf-8'` 再跑，并把兜底补进该脚本，不要只口头提醒。
>
> ⚠️ **Windows xargs 铁律（2026-08-27 立规，已踩坑）**：`deploy.sh` 本地用 `xargs` 批量把文件列表传给
> `tar`/`ssh` 时，Git Bash 继承的**环境变量块实测 521KB（169 条）**远超 Windows `CreateProcess` 的
> **32KB exec 上限**，GNU xargs 在 fork/exec 子进程时报 `environment is too large for exec` 并 rc=1——
> **每次有新增文件时必失败**（无变更走 else 分支不触发，故时隐时现）。
> - 症状：信息图/资产增量同步段 `xargs: environment is too large for exec` + 远端 `tar: This does not look like a tar archive`。
> - **禁用** `printf list | xargs -0 tar cf - ...` 这类把大列表喂给 xargs 再 exec 外部命令的写法。
> - **正确写法**：把列表写进临时文件，用 `tar cf - -C <dir> -T <listfile> | ssh ... "tar xf - --overwrite"`
>   （`-T` 让 tar 内部读列表，**不 exec 外部命令**，彻底绕开 32KB 上限）；`-C` 必须放在 `-T` 之前才生效。
> - ⚠️ **隐藏雷**：`assets/` 段原本同样用 xargs，但被 `2>/dev/null || true` 静默吞错——有变更时其实也悄悄失败，
>   从未暴露。已随 infographics 段一并改为 `tar -T`（2026-08-27）。
> - 120 行 `ls | tail | xargs rm -f` 在**远端 Linux** 执行，不受 Windows 环境变量限制，无需改。

## 目录速查

- `data/`：唯一数据源。`tools.json`（工具，6MB+）、`articles.json`、`compare_data.json`、`ranking_data.json`、`dict_terms.json` 等
- ⚠️ **2026-08-25 数据架构变更（重要，改工具数据前必读）**：`build_lib/data_loaders.py` 的 `load_tools()`/`load_articles()` 改为**目录优先**——存在 `data/tools/*.json`（每工具一个 shard，672 个，与单体 1:1 镜像）时，直接聚合 shard 而**忽略** `data/tools.json`；并新增 `sync_mono_from_shards()` 在 build 入口把 shard **聚合回写**单体（shard 胜出）。即 **`data/tools/<slug>.json` 才是真源，`data/tools.json` 是构建派生物**。
  - 后果：任何只写 `data/tools.json`（含 `verify_tools_batch.py --apply` 原逻辑、直接手改 mono）的更新，都会在下次 `build.py` 被 shard 覆盖而**静默丢失**。
  - 正确做法：改工具数据**必须写 shard** `data/tools/<slug>.json`；`verify_tools_batch.py --apply` 已修复为同时写回 shard（见 2026-08-26 补丁）。文章同理走 `data/articles/*.json`。
  - 诊断口诀：build 后数据"回滚"→ 八成是只动了 mono 没动 shard。
- `scripts/`：构建与批处理脚本（build.py、regenerate_data.py、optimize_css.py、check_*.py 验证等）
- `js/`：前端逻辑。`main.js`（首页渲染/搜索）、`favorites.js`（收藏）、`ai-assistant.js`、`tts-reader.js`；**`tools-data.js` 是构建产物，不要手改**
- `css/`：`style.css` 是源文件，`style.min.css` 由 optimize_css.py 生成，**不要手改 min 文件**
- `articles/ tools/ category/ compare/ ranking/ quiz/ dict/ news/`：构建产物目录，**不要手改**，改了也会被下次构建覆盖
- `.indexnow_pushed.json` / `.baidu_pushed.json`：推送记录，构建会自动增量推送，勿手动清空

## 硬性规则（踩过的坑，别重复踩）

1. **所有 HTML 页面都是构建产物**。改模板/数据后必须重跑 `scripts/build.py`，不要直接编辑生成的 HTML。
2. **URL 不可变**：文章地址 `/articles/{slug}/`、工具地址 `/tools/{slug}/`，slug 唯一且永久。分类归并、改名都不允许改 URL（外链/收藏/统计依赖它）。
3. **日期纪律**：`dateModified` 绝不默认"今天"（会被搜索引擎视为作弊，且让"最近更新"全部聚成同一天）。用 `updated_date` 字段，并保证更新日不早于收录日。
4. **构建必须稳定可复现**：随机选取用固定 seed（如 `random.seed(42)`），避免每次构建产生无关 diff。
5. **`tools-data.js` 和 `style.min.css` 由脚本生成**，直接改会被覆盖。要改字段/逻辑改生成脚本（build.py / optimize_css.py）。
6. **搜索的 `?q=` 参数由 main.js 处理**（P0-1 修复后）。404 页与 SearchAction 结构化数据都指向 `/?q=`，改搜索逻辑时务必保持这条链路可用。
7. **外链一律 `target="_blank" rel="nofollow noopener"`**；"立即使用"按钮走推广链接系统（`data/affiliate_links.json`），不要硬编码官网 URL 绕过。
8. **构建有内联守卫**：`scripts/check_internal_leak.py` 会拦截内部溯源信息泄漏（如"收录来源 ai-bot.cn"），不要绕过。
9. **改 data 前先备份**：大改动（如批量字段修改）先复制带时间戳的 .bak，项目有 `.cleanup_backup/` 与历史备份惯例。
10. **推送是构建副作用**：`-t none` 只出 HTML 不推送；日常本地验证用 `-t none`，避免重复触发 IndexNow/百度推送。
    - 注意：`-t none` 不重建页面（仅后处理注入）。需要"重建全部页面但不推送"时用 `-t all --no-push`（2026-08-09 新增参数）。
11. **Windows 编码问题必须修进脚本/规则**（2026-08-09）：凡是"换个环境又崩、需要手动 export"的问题，
    一律把修复写进脚本或 deploy.sh，并在 AGENTS.md 登记，禁止只靠"下次注意"。
12. **交付必须闭环（2026-08-10 立规）**：功能"完成"= 用户真实路径验收通过，不是文件/字段存在。
    - 每个功能改动必须写明验收标准，标准是"真实用户走通路径"（例：PWA 的标准是"安装成功且桌面出现图标"，
      不是"manifest 返回 200"）；
    - 交付前把自己当用户，走完关键路径（搜索→详情→排行→文章→收藏→安装），发现问题在交付前解决，
      不把用户当 QA；
    - 移动端改动必须验证 320 / 390 / 768 / 1280 四种视口；数据格式改动必须跑全量样例（如 FAQ 剥离跑全量工具）；
    - 全局注入 / 模板 / CSS 改动前先列影响面：受影响的页面、幂等标记、全站 sticky 元素、CSS 特异性覆盖关系。
13. **"未闭环"案例库（2026-08-10）**：以下案例说明"只验证中间产物"的代价，同类改动前对照自查：
    - PWA：只加了 manifest+图标，漏了 Service Worker（Chrome 安装硬条件），导致"安装提示有、图标不出"，
      上线后二次修复——教训：安装类功能必须验证可安装性（含 SW/图标尺寸/manifest 字段完整性）；
    - 排行页移动端：表格→sticky→卡片→两行卡片改了多轮，均因交付前未做多视口+多内容长度验证；
    - 搜索条 sticky：未排查全站其他 sticky 元素导致重叠，上线前应全局扫描 position:sticky；
    - build.py 模板 patch：上下文不唯一误改其他函数，patch 前用 inspect 确认目标函数归属。

## 2026-08-28 增量构建修复 + 单篇文章快速发布通道（发文章必读）

- 背景：写稿自动化每发一篇文章都跑 `bash deploy.sh` 全量构建（1100+ 页面）。`build.py -s <slug>`
  增量通道早就存在，但有硬缺陷，用了会把线上打残，所以一直没人用。本次修到底并新增 `deploy_fast.sh`。
- 修了什么（`scripts/build_lib/main.py` + `scripts/build_lib/html_utils.py`）：
  1. **sitemap 写残**：`-s` 分支不加载 compare/quiz/ranking/live/news 数据就调 `generate_sitemap`，
     实测 1141 条被写成 1000 条（掉 137：news 45 / compare 42 / alternatives 21 / ranking 19 / live 5 / quiz 5）。
  2. **首页不重建**：新文章在首页「最近更新/资讯卡」拿不到入口 → 现在 `-s` 也重建 index.html + 搜索索引。
  3. **日期邻居不重建**：新文章插进日期序后，前一篇文章的「下一篇」还指向旧文章 → 现在重建前后两篇。
  4. **related_tools 工具页不重建**：工具页会挂「相关文章」卡（render_tool.py），漏建新文章就不出现在工具页 → 现在重建。
  5. **后处理注入链统一**：抽出 `_post_process_all()`，全量与增量共用同一份（原增量漏
     inject_fav_fab / inject_rss_link / inject_section_hub / 全站坏链清理，导致增量产物 != 全量产物）。
  6. **`_emit()` 幂等**：内容逐字节相同就不写盘，保住 mtime——否则增量会把上千个"没变"的页面标成变更，
     增量直接退化成全量上传。
- 验收（AGENTS 规则 12「闭环」口径）：增量产物与全量产物**逐文件 sha1 一致**（唯一差异是 index.html 的
  `?v=` 缓存戳，属每次构建必然变化）；sitemap 1141 == 1141；
  `bash deploy_fast.sh nvidia-buys-huggingface-2026` 实跑全绿：51 个文件远端字节校验 51/51 一致、
  首页含文章链接、Article/FAQPage/Breadcrumb/canonical/ad-loader 齐、1m15s（全量 deploy 3m42s）。
- 用法：`bash deploy_fast.sh <slug> [--dry-run]`（构建 -s → 5 道门禁 → 远端备份 → tar -T 精准上传 →
  线上逐文件 sha1 + 关键 URL 验收 → git 提交本次相关文件）。
- **边界（不满足就必须走 `bash deploy.sh` 全量）**：
  - 改模板 / `build_lib` / CSS / js → 全站页面要重出，必须全量；
  - 改 `data/tools/*.json`、`dict_terms/`、`news_*.json`、compare/ranking/live → 必须全量；
  - 删页 / 改 slug → 必须全量 + 在 `nginx-old-url-redirects.conf` 补 301；
  - 跑过 `regenerate_data.py` 之后 → 必须全量。
  - 口诀：**只动一篇文章的分片 → 增量；动了数据面或模板面 → 全量。**
- 实现陷阱（别再改回去）：`deploy_fast.sh` 的上传清单 = git 差集 ∪ 构建 `[OK]` 声明 ∪ 关键枢纽页强制项
  ∪ 本文章配图。`tools/` 等产物目录被 gitignore，只靠 git 差集会漏掉重建过的工具页；
  配图与 OG 图也在 gitignore 里，必须显式补进去。远端 sha1 校验别用 `ssh + stdin 循环`
  （Windows OpenSSH 客户端下 stdin 传不进远程 while，会假失败），把路径拼进远程命令分批跑。

## 内容与模板约定

- **标题纪律（2026-08-13 立规）**：新文章标题（含 H1）控制在 60 字符以内；若正文标题较长，
  必须同时提供 ≤60 字符的 `seo_title` 字段（模板的 `<title>`/`og:title`/`twitter:title`
  会自动使用 `seo_title`，H1 不受影响）。存量文章已批量补齐 `seo_title`（Bing"标题太长"清零）。
- 工具详情页正文来自 `tools.json` 的 `content`（markdown），FAQ 统一由模板从 `tool.faq` 渲染——**content 里不要再带"常见问题（FAQ）"小节**（历史重复问题，已由构建剥离兜底）。
- 工具页"相关对比/替代/排行"链接按标题去重（同名不同 slug 只保留一个），新增对比/替代页时勿造同名。
- 文章正文由 `articles.json` 的 `content` 渲染；长文建议保留标题层级（h2/h3），目录功能依赖它。
- 文章正文插图用标准 markdown `![alt](https://www.aitoollab.cn/images/...)`（2026-08-17 起
  `markdown_to_html` 已支持）；图片放 `images/` 对应目录并在部署时同步。
- 首页的搜索框、热门词、分类区块由 `main.js` 读取 `window.__ALL_TOOLS__` 渲染；新增分类要同步 `CATEGORY_SLUG_MAP`。
- 生成内容保持 UTF-8；f-string 中嵌 HTML 时注意花括号转义（build.py 用独立常量块规避）。

## 验证流程（提交/部署前）

1. `python scripts/build.py -t none` 全量构建；
1.5. `python scripts/check_closed_loop.py`（2026-08-13 新增全站门禁：内部死链 / 单 h1 /
     Meta 描述完整性 / noindex / sitemap 枢纽页与覆盖 / 旧死链回归，任一 FAIL 先修再部署）；
1.6. `python scripts/check_sitemap_artifacts.py`（2026-08-27 新增，deploy.sh 已内置为
     [1.2/4] 门禁：sitemap 每条 URL 必须有对应本地 HTML 产物，拦截 pptbot 类"本地产物
     缺失会被同步打成线上 404"的镜像缺口）；
2. `python scripts/dev_site_server.py 8090` 本地起服，抽查改动页面（200、无 JS 报错）；
3. 跑相关校验脚本：`scripts/check_internal_leak.py`（构建已内置）、`scripts/check_urls.py` / `verify_*.py`（如涉及链接/页面）；
4. 检查 diff 范围符合预期（不要包含无关页面或大范围时间戳变化）；
5. 需要上线再执行 `bash deploy.sh`；
   5.5. deploy.sh [3.5/4] 会在 Nginx 重载后跑 `scripts/post_deploy_health_check.py`
   （线上 sitemap 全量 HEAD + 关键入口抽查，任何非 200 自动回滚中止）——背景：8/22
   部署窗口期 4 页线上 404，被 Google 抓进 404 清单一周后才被发现。今后删页/改 slug
   必须同步在 `nginx-old-url-redirects.conf` 补 301 并推送服务器（流程见
   `GSC-404治理与索引率提升方案.md`）。


## 已知优化清单

见 `UX-OPTIMIZATION-TODO.md`（按 P0/P1/P2 排序）。P0 全部与 P1 全部已于 2026-08-09 完成并标注；新改动请同步更新该文档，避免重复评估。

## 2026-08-09 已落地改动速览（改这些模块时注意）

- `scripts/build.py` 后处理注入器：全局搜索条（`GLOBAL_SEARCH_HTML`）、footer 链接（`FOOTER_LINKS_HTML`）、PWA manifest + Service Worker 注册（`inject_pwa`，2026-08-10 起 SW 与 manifest 分两段独立幂等注入）。它们遍历全站 HTML，**幂等靠特定 id/类名判断**，改动时不要破坏幂等标记。
- 工具页 FAQ 由模板统一渲染：正文 content 中的"常见问题（FAQ）"小节在构建时剥离（`extract_faq_section`），写新工具内容时不要再在 content 里带 FAQ 小节，数据放 `faq` 字段。
- 工具页 action-bar 含"复制链接 / 信息有误？"（`data-copy-link`、`contact.html?tool=`），改按钮布局时保留。
- 文章页自动生成目录与上一篇/下一篇（`_pagination_html`、`toc_html`、`prev_next_html`），依赖正文 h2/h3 标题层级。
- `sw.js`（根目录）是 PWA Service Worker：网络优先 + 离线兜底，**改缓存策略/预缓存列表时更新 `CACHE_NAME` 版本号**（当前 v2），否则旧缓存不失效。Chrome 安装 PWA 必须有 SW，不要删除注册脚本。
- PWA manifest 用根目录 `manifest.json`（2026-08-13 从 `.webmanifest` 改名）：nginx 默认把 `.webmanifest` 以 `application/octet-stream` 返回，Chrome/部分浏览器会判不可安装（小米浏览器装快捷方式不校验所以"能装"）；`.json` 由 nginx 默认以 `application/json` 返回。改 manifest 文件名/内容时同步改 `scripts/build.py` 的 `inject_pwa` 链接与 `sw.js` 的 `PRECACHE_URLS`，并 bump `CACHE_NAME`。

## 2026-08-19 文章页 FAQ 可见渲染（改文章模板时注意）

- 事件：文章 FAQ 从「正文自带小节」迁移到 `faq` 字段后，文章模板（build_article_page）只输出 FAQPage schema、
  不渲染可见 FAQ 区块，导致用 faq 字段的文章前端看不到 FAQ（gpt-live / descript / ai-open-weight 3 篇中招；
  ai-open-weight 用 q/a 键，schema 回退只认 question/answer，连 FAQPage 都没输出）。
- 修复（`scripts/build.py` build_article_page）：
  1. `faq` 字段 → 模板渲染可见 `.faq-section#faq`（复用工具页 faq-section/faq-item/faq-q/faq-a 样式），
     兼容 `question/answer` 与 `q/a` 两种键；
  2. 正文已含「常见问题」小节的旧文章跳过模板渲染，避免双 FAQ；
  3. FAQPage schema 回退逻辑同步兼容 `q/a` 键。
- 规则：新文章 FAQ 一律写 `faq` 字段（3-5 条），模板自动输出「可见 FAQ 区块 + FAQPage schema」，
  正文不要再带「常见问题」小节（避免与模板区块重复）。改文章模板时保持以上三处逻辑。

## 2026-08-10 品牌标识（改 LOGO 时注意）

- 站点标识 =「方框 + 内嵌四角星光」（2026-08-11 改版）：居中对称，方框象征宝箱/收纳、星光代表 AI；旧版「星光上浮于箱体」易被误看成蜡烛，已废弃。绿色系（与 `--bg-gradient` 一致）。全站头部旧 emoji（🛠️/🛠/&#x1F6E0;）与旧扳手 SVG 已统一替换为新图形。
- **矢量母版**：`assets/logo/logo-mark.svg`；**生成脚本**：`scripts/generate_site_logo.py`（输出 favicon.ico 16/32/48/64、`assets/icons/pwa-*.png`、`images/logo.png`、`images/og/aitoolbox-og.png`、`output/logo-preview.png`）。改图形 = 改该脚本的几何常量 + 母版 SVG + `scripts/build.py` 的 `SITE_LOGO_MARK` 常量，三者必须一致，再重跑脚本与全量构建。
- `scripts/build.py` 新增 `inject_site_logo()` 后处理：幂等替换全站 HTML 头部标识（div.site-logo / a→h1 / 旧扳手 SVG 等写法）。CMS 控制台页（`cms.html`）品牌是 aitoollab.cn，**不要替换**。
- `images/logo.png`（512 方标）是结构化数据 Organization.logo 的正式引用；`images/og/aitoolbox-og.png`（1200×630）是社交分享卡。旧脚本 `scripts/generate_favicon.py` 为紫色旧版遗留，勿再使用。

## 2026-08-12 今日推荐机制修复（日期与内容同源）

- 曾出现「首页日期显示今天、推荐工具还是昨天」：根因是候选池生成晚于构建（deploy.sh 先 build.py 后 generate_picks_candidates.py），且词典/发布等自动化只跑 build.py 不生成候选池，而日期标签用 `datetime.now()` 硬写。
- 修复（三处，改推荐逻辑时注意保持）：
  1. `deploy.sh`：候选池生成已挪到构建之前（步骤 0.8），并纳入 git add 提交清单；
  2. `scripts/build.py`：构建首页时若 `homepage_picks.json` 为 auto 模式且日期非当天，先自动调用 `generate_picks_candidates.py` 刷新再渲染（幂等，当天只刷一次）；
  3. 日期标签 `picksDate` 改用 `homepage_picks.json` 的 `date` 字段渲染，不再用 `datetime.now()`，保证标签与内容永远一致。

## 2026-08-13 推荐文案防劣化守卫（问号事件）

- 事件：线上「今日推荐」3 个工具的 tag/reason 变成大量 `?`——`homepage_picks.json` 的中文被 ASCII 化后
  随部署上线。根因是手工用 PowerShell 管道把含中文的 JSON 写回文件时，PowerShell 5.1 默认按 ASCII 编码管道，
  中文全部变成 `?`（`$OutputEncoding` 问题），随后部署脚本把坏文件提交并同步上线。
- **数据文件写改铁律**：含中文的 JSON/文本一律用 Python 脚本或 apply_patch 写，禁止 PowerShell
  `@'...'@ | python -` 这类管道传中文（PowerShell 5.1 管道默认 ASCII，会把中文变 `?`）；
  写后必须用 `python -c` 重新读回校验。
- 防劣化守卫（已落地，改推荐逻辑时保持）：
  1. `scripts/build.py`：渲染推荐前检测 reason/tag 是否存在连续 3 个以上 `?` 或替换符 `\ufffd`；
     auto 模式检测到损坏即强制调用 `generate_picks_candidates.py` 重建（即使日期是当天）；
     仍残留损坏条目则跳过并用热门榜补足 3 个，保证推荐区不空。
  2. `scripts/generate_picks_candidates.py`：auto 模式且当天已确认时，若文案损坏也强制重建
     （原来"今天已确认过就保持"会挡住损坏自愈）。

## 2026-08-13 广告注入丢失事故（build.py 自动注入机制化）

- 事件：线上文章/资讯页全部丢失广告加载器（`/ads/loader.js` 与 `data-category`），
  推广卡全站失效（用户实测才发现）。
- 根因（机制）：
  1. 广告加载器不在模板里，是构建后由 `scripts/inject_ads.py` 注入的——build.py 每重建一次页面，
     loader 就被"洗掉"；
  2. 多个自动化（版本监控/词典/快讯/发文章等）只调 `build.py`，不调 `inject_ads.py`
     （AGENTS.md 早已记载"词典/发布等自动化只跑 build.py"）；
  3. `inject_ads.py` 一直没补 Windows 编码兜底（2026-08-09 铁律要求，实际漏了），
     直接运行会因打印 ✅ 抛 UnicodeEncodeError 中途退出，即使有人手动跑也可能半途而废；
  4. 上述"无广告产物"一旦被任何上传路径推上线，就全站丢广告（本次实际发生）。
- 修复（四层，改构建/部署时保持）：
  1. `scripts/build.py` 构建完自动补跑 `inject_ads.py`（幂等，subprocess 带 PYTHONIOENCODING）——
     build.py 作为唯一出口，任何入口（手动/自动化/deploy）构建完都自动注入，禁止只跑 build 不注入；
  2. `scripts/inject_ads.py` 补齐 stdout/stderr 编码兜底（直接运行也不再崩）；
  3. 新增 `scripts/check_ads_injected.py` 部署前守卫：deploy.sh 在 inject 步骤后校验全部内容页含
     loader，缺则 set -e 中止部署；
  4. 规则：新增"构建+发布"自动化时，产物必须从 build.py 出，禁止绕过 build.py/deploy.sh
     直接拼装或上传 HTML。

## 2026-08-12 资讯页广告位（改广告模块时注意）

- 背景：资讯页此前完全不在广告体系内——`scripts/inject_ads.py` 的 `ALLOWED_TOP` 没有 `news`，
  导致资讯页连 `/ads/loader.js` 都没注入，config.json 也无 news 页型，一个广告都出不来。
- 已修复：
  1. `scripts/inject_ads.py` 白名单新增 `news`，`page_type_for` 返回 `news`（部署时自动给资讯页注入 loader）；
  2. `ads/config.json` 新增 `news-top` / `news-inline` / `news-bottom` 三个广告位（默认关闭，
     拿到联盟代码后填 `ads/slots/news-*.html` 并翻开关即可，无需重建）；
  3. `ads/loader.js` 的 CPS 卡扩展到资讯页：`cps.news.enabled=true` 时取 `cps.json` 的
     `by_news_category` 渠道（按第一条快讯的栏目标签匹配：模型发布/论文研究→阿里云、
     产品发布/观点→腾讯混元、行业动态→百度文心；未命中回落 `default`），渲染到
     `cps.news.afterIndex`（默认 3）条快讯之后；工具页逻辑不变。
  4. CPS 卡（工具页+资讯页）新增百度统计曝光/点击上报：`_trackEvent('CPS','impression|click', 渠道|页型)`，
     改卡片文案/位置后务必看统计里的转化数据再迭代，不要靠感觉。
  5. `scripts/build.py` 资讯页模板补齐百度统计（此前资讯页全站唯一无统计的页面类型，主流量却在资讯，
     导致无法衡量广告点击率）。
  6. 文章页 CPS 推广卡（2026-08-12 新增，流量大头在文章页）：桌面端插侧边栏顶部、移动端插正文第 4 段后
     （CSS 互斥只显示其一，避免双卡）。渠道按文章 `data-category` 匹配 `cps.json` 的
     `by_category`（AI对话等工具品类直接复用）→ `by_article_category`（AI资讯/行业趋势等）→ `default`。
     `scripts/inject_ads.py` 现在也给文章页注入 `data-category`（读 `articles.json` 的 category/content_type）。
  7. CPS 卡引流钩子（2026-08-12 新增）：`cps.json` 顶层 `hooks` 按渠道配置福利条文案
     （当前阿里云="🎁 新用户赠超 1 亿 Tokens 免费额度"，千问/百炼新用户免费额度活动），
     条目可单独用 `hook` 字段覆盖。卡片模板 `ads/slots/cps-card.html` 有 `{HOOK}` 占位，
     loader 替换为空字符串时 CSS `:empty` 自动隐藏，腾讯/百度卡不受影响。
 8. **工具级专属推广位 `by_slug`（2026-08-17 新增）**：`cps.json` 顶层 `by_slug` 按工具 slug 直接映射推广卡，优先级高于 `by_category`。`loader.js` 的 tool 页选位逻辑改为：先取 `location.pathname` 正则里的 slug → 命中 `by_slug[slug]` 即用，否则回落 `by_category[cat]` → `default`。用于给单个工具（如 WorkBuddy）挂与品类不同的专属渠道/活动，不影响其所属分类页的其他工具。
     改活动口径/文案只改 `cps.json`，fetch no-store 无需重建。
- 注意：资讯页没有侧边栏（`main.container` + `.news-cards`），新增资讯广告位的 target
  必须指向 `.news-cards` 或 `main.container`，不要套用工具页的 `.content-main` / `aside` 选择器。

## 2026-08-13 暗色模式"白底灰白字"漏网兜底（改暗黑/新组件时注意）

- 事件：暗色模式下部分页面仍出现"浅色底 + 浅灰字"看不清（用户复测发现）。
- 根因（机制）：2026-07-15 那轮暗色修复是白名单式枚举（style.css 1~16 节），
  只覆盖当时已知的类名与内联写法；白名单外的浅底容器一旦出现就漏网，
  而且暗色"文字提亮"规则是全局 `!important`，遇到没转深的浅底反而制造"浅底+浅字"。
- 本次补漏的 4 处（改这些模块时保持）：
  1. `scripts/build.py` Quiz 模板：`.quiz-question/.quiz-progress/.quiz-intro/.quiz-conclusion/
     .tool-rec-detail/.quiz-option` 背景/边框/文字改走 CSS 变量（`var(--surface-2)` 等），
     悬停/选中改半透明蓝；页面级 `<style>` 仍保留 `[data-theme="dark"]` 兜底块；
  2. `scripts/build.py` 排行模板：`.rank-top3-card/.ranking-table-wrap/.ranking-table th/
     .rank-reason/.rt3-name/.rt3-reason` 与 `.ranking-analysis` 区改走变量；
     （移动端 `.ranking-table tr.rank-row` 的白底由 style.css 的暗黑 `!important` 兜底，模板长行未动）
  3. `ads/loader.js`：CPS 推广卡与侧边栏广告容器补 `[data-theme="dark"]` 分支
     （卡底 #1e293b、文案提亮、福利条转深琥珀）；
  4. `css/style.css` 新增第 17 节兜底：
     - `.article-body` 内 `pre/tr/p/div/blockquote` 带内联浅底且未显式声明
       `color` 的，暗色下统一转 `var(--surface-2)`（深底高亮行带 `color:#fff` 不会被误伤）；
     - 浅色模式下内联浅底 `<pre>` 的文字改深（原基础样式是深底浅字，被内联背景改浅后浅底浅字）；
     - `.tldr-box/.tool-summary` 内联 `color` 的 span 暗色下提亮；
     - Quiz/排行页组件、`.mobile-ad-inline` 占位条暗色兜底。
- 防复发守卫：新增 `scripts/check_dark_mode.py`，deploy.sh 在 build 后（1.56 步）自动执行，
  发现 Quiz/排行模板或 loader.js/style.min.css 出现硬编码浅底即 `set -e` 中止部署；
  正文内联浅底仅告警（CSS 已兜底，不改内容）。
- 规则：新增任何带背景的组件/页面模板时，必须给暗色模式补分支或用 CSS 变量，
  禁止"只修文字提亮、不修背景"的写法；正文内容若带内联浅底，须同时确认
  `.article-body` 第 17 节兜底能覆盖该写法。
- 验收标准（2026-08-13 已实测）：Quiz/排行/资讯/文章（含内联 pre/表格行/TL;DR）四类页面
  在暗色模式下无"浅底+浅字"；320/390/768/1280 四种视口低对比扫描全部为 0；
  浅色模式外观与修复前一致（Quiz 答题卡白底深字、CPS 卡白底深字、内联 pre 浅底深字）。

## 2026-08-15 CPS 自建 beacon 统计（改 ads/loader.js 或 nginx 时注意）

- **背景**：百度统计免费版无事件分析权限（已迁付费"分析云"），CPS 曝光/点击的主数据源是自建 beacon，`_trackEvent` 仅备用。
- **链路**：loader.js `cpsBeacon()` → `GET /ads/beacon.gif?act=impression|click&ch=渠道&pt=页型&slug=xx&ts=xx`（Image 发出）→ nginx access log 留痕 → `python scripts/analyze_beacon.py` 聚合分析（渠道/页型/slug 曝光点击率）。
- **nginx 关键配置**：静态资源 location `~* \.(gif|...)$` 带 `access_log off`，beacon 依赖 `location = /ads/beacon.gif` 精确匹配（conf.d/aitoollab.conf）单独开日志 + no-store。**改静态资源规则或 conf 时不要删掉这个块**；服务器备份 `aitoollab.conf.bak-20260815-beacon`。
- **日志路径**：站点真实流量在 `/var/www/aitoollab/logs/access.log`（www server block）；`/var/log/nginx/access.log` 只记非 www 的 301，分析别拉错文件。
- **验证线上资源一律 `curl -sL`**：aitoollab.cn 会 301 到 www，不跟随重定向会拿到 301 页误判文件内容。
- 百度统计站点 ID 实为 `7cf34c7c8b66be4564949354dbc51337`（build.py 内嵌），旧记录 6ac10754 已过时。

## 2026-08-17 TTS 朗读起点事故（改文章页模板 / tts-reader.js 时注意）

- 事件：文章朗读从「🔧 本文提到的工具」开始（用户复测发现）。根因：2026-08-13 起正文上方
  工具卡（`related_tools_top_html`）被插进 `<article class="article-body" data-tts>` 容器内、
  正文之前，而 `tts-reader.js` 的跳过名单只覆盖目录/声明块，没覆盖推荐卡。
- 三层修复（改相关模块时保持）：
  1. `js/tts-reader.js`：`getBlocks` 增加 `.related-tools` 跳过（含 `.article-top-tools`）；
  2. `scripts/build.py`：文章页两张推荐卡（`related_tools_html` / `related_tools_top_html`）
     容器类名加 `tts-skip` 显式排除标记；
  3. 新增 `scripts/check_tts_skip.py` 部署门禁：校验 JS 规则存在 + 所有 data-tts 容器内的
     related-tools 卡都带 tts-skip，deploy.sh 在 1.57 步执行，失败中止部署。
- 规则：任何把带文字区块（导航/推荐/卡片）插入 `data-tts` 容器的改动，必须同时加 `tts-skip`
  类并保持 `tts-reader.js` 跳过规则，禁止只加样式不加排除标记。

## 2026-08-18 选题写稿全自动发布（改写稿/发布自动化时注意）

- 背景：站长不再人工审核草稿，人工确认环节由机器门禁替代。写稿任务更名「SEO 选题写稿与自动发布」，
  一/三/五 7:10 全自动跑完「写稿→配图→入库→构建→门禁→上线→推送→验收」，只有门禁失败或部署异常才停下来报告。
- 链路（改任何一环时保持）：写稿 → playwright 真实截图配图（教程类 2-4 张，登录墙界面截公开页或做
  本站风格示意图并如实标注，禁止 AI 假 UI 截图）→ `scripts/publish_article.py --draft tmp/<slug>.json`
  校验入库（唯一入库入口，任一校验不过即失败且不写文件）→ `bash deploy.sh`（regenerate_data +
  optimize_css + 构建 + 广告/CPS 注入 + 暗色/TTS/闭环门禁 + rsync + 百度/IndexNow 推送）→
  `curl -sL` 验收文章页与首页包含文章链接。
- `scripts/publish_article.py` 校验项：标题与 seo_title≤60 字、正文 600-2200 字且含 h2、FAQ 3-5 条、
  配图 URL 与本地文件存在、slug 无冲突（含内容分类目录 reviews/tutorials/news/analysis/page）、
  related_tools 必须是真实工具 slug、date/dateFull=当天、无 AI 味短语（写作铁律列表）。改校验规则时
  必须同步更新 seo-daily-writer 的 automation.toml prompt 与本文档，保持口径一致。
- 选题流控制（2026-08-18 立）：A 区只收「站内无独立文章 + 展示≥1000 + CTR≥10%」潜力词，按
  展示×CTR 降序，上限 10 条，超出进观察区；已覆盖词一律不新写（可更新）；B 区收机会词与观察词。
  写稿节奏固定 3 篇/周（一/三/五），A 区待写连续两周 >10 条才建议提到 5 篇/周。
- B 区配额规则（2026-08-24 立，修复 B 区被 A 区饿死）：写稿自动化每周至少一次专做 B 区（周五保底）；
  B 区 P0/P1 待办超过 7 天自动最优先，不受 A 区影响。改优先级逻辑时必须同步
  seo-daily-writer 的 automation.toml prompt 与本文档，禁止只改一处。
- 内容差异化总原则（2026-08-24 立，站长定调）：别人没有的我有——官方站/竞品不做的教程、对比、场景指南
  就是我们的内容机会；别人有的我精——深度实测、完整 FAQ、横评做到更细。标题与选题不蹭无关品牌词
  （裸品牌词如"腾讯"不打）；带产品全名的限定词（如"腾讯朱雀ai检测"）靠页面如实描述厂商归属自然覆盖，
  不专门做标题。

## 2026-08-18 SEO+GEO 基本功（改文章模板/写稿自动化时注意）

- 原则：SEO（搜索引擎收录排名）与 GEO（AI 问答引擎，ChatGPT/Perplexity 等引用）的基本功是
  内容自动化的底线，发布前逐项自查，禁止为了跑量丢掉。模板已保证的项不要重复手写：Article/
  FAQPage/Breadcrumb/Organization 结构化数据、canonical、OG/Twitter 卡、外链 rel 属性——正文只写
  markdown，别在正文里塞 `<script>`/`<link>`/手写 schema。
- 机器已固化（`scripts/publish_article.py`，报错即拦截）：description 50-200 字、summary 20-200 字、
  标题层级≥2 个 h2/h3；[提示] 告警项（也应修正后再发）：FAQ 问句以「？」结尾、正文至少 1 条站内链
  （related_tools 也算）、description 建议 80-160 字、summary 建议 30-150 字。
- 写作自查清单（发布前逐项过）：① 标题含目标关键词且≤60 字、与站内文章不重复；② description
  80-160 字、含关键词、讲清这篇解决什么问题；③ 正文第一段直接给结论/答案（GEO 问答引擎优先抓取），
  再按 h2/h3 逐层展开；④ 关键实体首次出现给全称+常用别名（如 GPT-Live=OpenAI 新一代实时语音引擎），
  方便 AI 问答引用；⑤ FAQ 用用户和 AI 常问的自然问句；⑥ 至少 1 条站内链接，外链一律
  `target="_blank" rel="nofollow noopener"`；⑦ 数据与事实标注官方文档/发布页/新闻链接（EEAT 信号）；
  ⑧ 结构化数据交给模板输出。

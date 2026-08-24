# SYSTEM-MAP — aitoollab.cn 系统现状全图（2026-08-23 查证版）

> 本文件是**事实基线**：所有环节均经代码查证（build.py / deploy.sh / loader.js / config.json / 自动化DB）。
> 后续任何架构讨论以本图为基准，先看全图再下结论，避免顾此失彼。

---

## 一、四层全景

```
数据层  data/*.json（唯一数据源，13 类）
   │
   ▼
构建层  scripts/build.py（SSG，main → build_target，按 -t/-s 分段）
   │  ├─ 页面渲染（工具/文章/分类/对比/替代/Quiz/排行/Live/词典/快讯/首页）
   │  ├─ 后处理注入器 × 12（nav/logo/footer/PWA/fav/hreflang/统计/RSS/板块簇/坏链清理）
   │  └─ sitemap + 百度/IndexNow 推送
   │
   ▼
广告层  三重保险（模板固化 + build 自动注入 + deploy 无条件注入，均幂等）
   │  └─ loader.js（运行时 fetch config.json → 按 data-page-type 匹配 slots → 注入广告位/CPS卡）
   │
   ▼
部署层  deploy.sh（regenerate→css→picks→build→inject→校验×4→rsync→远端核验→reload→git）
   │
   ▼
线上   阿里云 121.43.144.99 /var/www/aitoollab/html（Nginx）
```

---

## 二、数据层（data/*.json）

| 文件 | 内容 | 消费方 |
|---|---|---|
| tools.json | 662 工具 | 工具页/分类/首页/排行/搜索索引/对比/替代 |
| articles.json | 165+ 文章 | 文章页/列表/分类 |
| compare_data.json | 对比+替代 | compare/、alternatives/ |
| ranking_data.json | 排行 | ranking/ |
| quiz_data.json | 选择器 | quiz/ |
| live_data.json | 实时面板 | live/ |
| dict_terms.json | 词典 124 词条 | dict/ |
| news_*.json | 每日快讯 | news/ |
| homepage_picks.json | 首页推荐 | index |
| affiliate_links.json | CPS 推广链接 | 立即使用按钮 |

**构建期写回点（唯一）**：`build.py` L236 `ensure_article_content_types` 会补写
`content_type` 字段到 articles.json（有渲染兜底，但并发时与发布自动化抢写存在竞争）。

---

## 三、构建层（scripts/build.py，9524 行单体）

### 入口 main()（L9481）
1. stdout 编码兜底（Windows GBK 防崩）
2. `check_internal_leak.py` 前置检查（泄漏 exit 1 中止构建）
3. argparse：`-t`（all|articles|tools|live|pseo|ranking|index|sitemap|dict|news|none）、`-s slug`、`--no-push`
4. `build_target(target, slug, no_push)`
5. **构建完自动调 inject_ads.py**（L9529，2026-08-13 机制化，幂等；崩溃则扫 0 字节页并中止）

### build_target()（L8422）
- 加载数据 → `_check_content_preamble`（AI 应答前缀拦截）→ `ensure_article_content_types`（写回）→ 快讯加载
- **slug 增量分支（L8502）**：
  - 文章 slug：只建 `articles/{slug}/` + 列表页 + 分类页 + sitemap + 推送（原生）
  - 工具 slug：`_build_tool_incremental`（L8378，2026-08-23 新增）→ 工具页+分类页+tools/index+首页(含搜索索引)+排行页+sitemap 单 URL 推送
- **非 slug 分段**：
  - `-t all|index|tools` → 分类页+子类目+分类总入口+tools 大全页
  - `-t all|tools` → 全部工具页（662 循环）
  - `-t all|articles` → 全部文章页+列表+文章分类
  - `-t all|pseo` → 对比+替代+Quiz（含总入口）
  - `-t all|ranking|pseo` → 排行页+总入口
  - `-t all|live|pseo` → Live 面板+总入口
  - `-t all|news` → 快讯页
  - `-t all|dict` → 词典页
  - `-t all|index|tools` → 首页 index.html
- **后处理注入器（12 个，全站遍历）**：inject_global_nav / inject_site_logo / inject_footer_links /
  inject_pwa / inject_fav_fab / inject_favicon / inject_hreflang / inject_adsense_meta /
  inject_baidu_tongji / inject_rss_link / inject_section_hub / _clean_all_broken_links
- **sitemap + 推送**：百度（.baidu_pushed.json 缓存）、IndexNow（.indexnow_pushed.json 缓存）；
  `--no-push` / `-t none` 跳过推送

### 增量构建现状（"用哪建哪"真实能力）

| 板块 | slug 增量 | 说明 |
|---|---|---|
| 文章 | ✅ 原生 | `-s <slug>` |
| 工具 | ✅ 2026-08-23 新增 | `-s <tool_slug>`（含连带聚合页） |
| 词典 | ⚠️ 段级 | `-t dict`（全量 124 页，成本低） |
| 快讯 | ⚠️ 段级 | `-t news`（每日 1 页） |
| 分类/排行/Live/对比/Quiz | ❌ 无 | 集合小（41/16/5/22/6 页），全量成本低 |

> 结论：**"全跑"不是必须**。自动化本就分段（文章 `-s`、工具 `-t tools`、词典 `-t dict+index`、快讯 `-t news`）。
> 只有改模板/CSS/全局注入时才需要 `deploy.sh` 全量。

---

## 四、广告层（三重保险，全部幂等）

### 标记来源（data-page-type / data-category / loader.js）
1. **模板固化**（2026-08-23 新增）：build_tool_page 等模板直接输出三标记 → 新建页天然自带
2. **build.py main() 自动注入**（L9529，2026-08-13）：构建完自动跑 inject_ads.py
3. **deploy.sh 无条件注入**（L61-64）：**无论是否 --skip-build 都跑**（在 if 块之外）→ 全站页面必有标记

### 运行时（loader.js，浏览器端）
- 读 `<body data-page-type="tool|article|news|...">` + `data-category="品类"`
- fetch `/ads/config.json`（no-store）→ 按 slots 矩阵的 `pageTypes` 匹配 → 注入对应广告位
- CPS 卡：按 `data-category`/slug 匹配 `cps.json` 渠道（阿里云/腾讯/百度）→ 渲染 cps-card → beacon 曝光/点击上报

### 修改广告策略
改 `ads/config.json` / `cps.json` / `slots/*.html` → **30 秒线上生效，零构建零部署**

---

## 五、部署层（deploy.sh）

| 步骤 | 命令 | 说明 |
|---|---|---|
| 0 | regenerate_data.py | 重生成排行/仪表盘数据 |
| 0.5 | optimize_css.py | min+critical CSS |
| 0.8 | generate_picks_candidates.py | 今日推荐候选池 |
| 1 | build.py | 全量构建（含自动 inject_ads） |
| 1.5 | inject_ads.py | **无条件执行**（即使 --skip-build） |
| 1.55-1.65 | check_ads_injected / check_dark_mode / check_tts_skip / fix_css_refs / check_closed_loop | 5 道门禁，失败中止 |
| 2 | rsync 增量 | git diff 文件 + 14 个强制目录 + assets 增量 + infographics 增量 + 根文件 |
| 2.9 | 远端 loader 核验 | 线上抽样 grep loader，缺则重注入重传 |
| 3 | nginx reload | — |
| 4 | git add/commit/push | 数据+产物备份 |

---

## 六、自动化层（4 个每日，均走 deploy.sh --skip-build）

| 时间 | 名称 | 命令链 |
|---|---|---|
| 07:30 | SEO 文章（seo-3） | 写文章 → `build.py -s <slug>` → `deploy.sh --skip-build` |
| 07:50 | AI 词典（automation-1782522385095） | publish_dict_terms → `build.py -t dict` + `-t index` → deploy |
| 08:00 | AI 快讯（automation-1784555527714） | fetch_aihot → `build.py -t news` → deploy |
| 08:30 | 工具发布（ai） | publish_new_tools → `build.py -t tools` → deploy |

> 关键：自动化 `--skip-build` **只跳过构建**，不跳过 inject_ads/门禁/同步。
> 且每个 build 都过 main() 的自动注入 → **广告丢失（08-21 类事故）在当前结构下被三重保险杜绝**。

---

## 七、历史事故与当前防线对照

| 事故 | 当前防线 |
|---|---|
| 08-21 全站广告丢 | ✅ 三重注入保险（模板+build+deploy 均幂等） |
| 08-16 CSS 旧版缓存 | ✅ 改 CSS 必 `-t all --no-push` + 全量部署（纪律） |
| 07-20 构建崩溃 | ⚠️ 无按页隔离（仍单点） |
| 08-05 re.compile 击穿 | ✅ 自建缓存 |
| 07-24 源码没进 git | ✅ deploy.sh L364 已加 build.py 等 |
| 08-01 自动化回退决策 | ⚠️ 无决策持久化 |
| 07-15 带病构建上线 | ⚠️ 无 staging/smoke/回滚 |

---

## 八、已知待办（架构层）

1. **按页 fail-soft 隔离**：单页渲染异常 → 跳过+报告，不拖垮整次构建
2. **构建前数据校验闸**：脏数据进 build 前拦截
3. **原子部署+回滚**：staging + smoke + 保留 last-known-good
4. **并发锁**：多自动化/多 publish 写 data 互斥
5. **决策持久化**：自动化参数/状态落盘，防默认参数回退正确决策

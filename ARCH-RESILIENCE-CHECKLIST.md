# 架构抗压改造清单（aitoollab.cn 静态站）

> ⚠️ **口径更新（2026-08-28）**：本文以下出现 `data/tools.json` / `data/articles.json` 的地方均为历史写法。单体已于 2026-08-26 退役删除，真源是 `data/tools/<slug>.json`、`data/articles/<slug>.json`、`data/dict_terms/<term>.json` 分片目录；读写一律走 `scripts/data_store.py`。权威口径见 [AGENTS.md](AGENTS.md)「数据架构：分片即真源，单体已退役」，部署链路由 `scripts/check_mono_retired.py` 硬阻断单体复活。


> 目标：让站点"越臃肿越稳"。无论未来功能多、内容多、上游怎么炸，线上不被污染、更新不被一处坏全卡死。
> 原则：不是物理拆 `build.py`，而是**职责分层 + 每段 fail-soft 隔离 + 旁路幂等自治 + 原子上线**。
> 状态：2026-08-23 推演产出，待评审。依据见 `.workbuddy/memory/2026-08-23.md` 与 MEMORY.md 工程铁律。

---

## 一、6 条不变量总纲（方案优劣的唯一判据）

| # | 不变量 | 解决的核心担忧 |
|---|---|---|
| I1 | 局部化：任一单点失败 → 仅该段/该页缺内容+报错，不阻断其他更新 | 一处坏全崩（模式 A） |
| I2 | 生产不可污染：带病构建永不直接覆盖线上（atomic + smoke + 回滚） | 带病上线（模式 B，最危险） |
| I3 | 链接一致：交叉链接始终有效（reference graph 保证） | 拆分后死链 |
| I4 | 源头拦截：脏数据进构建前被校验闸拦下 | 上游数据污染 |
| I5 | 并发安全：多自动化/多 publish 不互踩（锁 + 队列） | 自动化冲突丢数据 |
| I6 | 可回溯：任何变更有备份 + last-known-good | 无法回滚 |
| I7 | 可复现：seed 固定 + 无随机/时间 diff，同输入逐字节同输出 | 内容漂移（用户 Q2） |

---

## 二、目标架构（职责分层，非物理拆文件）

```
lib/                         # 抽出的纯函数，单一真相
  ├─ render_core.py          # markdown/schema 渲染（build/各 builder 共用）
  ├─ site_shell.py           # header/footer/logo/PWA 注入（幂等标记复用）
  ├─ reference_graph.py      # 构建前算全量链接关系图，各段共享 → I3
  └─ ad_tags.py              # 输出 data-page-type + data-category + loader.js 引用
builders/                    # 每段自包含单元，独立 staging + fail-soft + 校验
  ├─ build_tools.py          → dist/tools/    (try/except 包单页，坏记录跳过+报告)
  ├─ build_articles.py       → dist/articles/
  ├─ build_category.py       → dist/category/
  └─ build_aggregators.py    → dist/(首页/排行/搜索索引)  依赖 tools+articles 输出
orchestrator.py              # 跑校验闸 → 调度各段 → merge dist/ → smoke → 原子 promote/回滚
ads/loader.js + config.json  # 广告/ CPS 纯运行时，零构建（已落地大半，见 T3/T6）
```

---

## 三、任务清单（按优先级，每条带改动点/不变量/验收）

### P0 — 地基（必须先做，否则模块化会污染共享状态）⚠️ 最高杠杆

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T1 ✅已完成 | **build.py 严格只读数据**（非"防内容漂移"，是并发安全+构建纯净） | 唯一写回在 `build.py:236 ensure_article_content_types`（仅补 `content_type` 分类标签，且有渲染兜底 L231）。**改法**：把 content_type 补全挪到**发布管线/regenerate_data.py**（文章创建时即写好），build 不再写 `data/*.json`。⚠️ 注意：此改**不会**改变页面内容（渲染本就有兜底），真实收益是消除"build 与发布自动化 07:30 抢写 articles.json"的并发竞争(S5)+让部分构建安全 | I5 + I7 + 数据不可变 | 跑全量 build，确认 `data/*.json` mtime 不变、内容零改动；新文章 content_type 在发布时已存在 |
| T2 | **外部化构建时间戳 + 日期兜底改"数据派生"（⚠️ 不是"剔除所有 now()"）** | 21 处 `now()` 绝大多数是"数据缺日期时的安全网"，盲删会砸：footer「更新于」空白(L2932/3204)、Schema dateModified 空(L1750/1954/2218/2738/3165)、sitemap lastmod 空(L7935)、文章日期兜底失效(L4882/5665)、实时面板「数据截至」空白(L2685)。**正确改法**：① 新增 `data/last_build.json`（orchestrator/deploy 每次写一次构建时间戳，build 只读）→ footer「更新于」用此值；② Schema/sitemap/文章日期兜底改读 `updated_date`/`last_updated`，真缺失用站点固定发布日(2026-03-21)常量，**绝不填今天**；③ `BUILD_YEAR`(L131)保留或硬编码 | I7 + 日期纪律 | 同输入构建→产物逐字节一致；footer/schema/sitemap 日期均非空且源于数据而非今天 |
| T3 | **广告标记固化进模板（低风险高收益）** | `build.py` 模板直接输出 3 个静态标记：loader.js 引用 + `data-page-type` + `data-category`（build 渲染时本知页型/品类，零成本）；`inject_ads.py` 日常不再需跑 → 根除 08-21"--skip-build 跳过注入丢广告"。⚠️ 例外：wwads(L180-264)/AdSense(L140-177) 是"div 必须写死 HTML"的静态烤入，目前 config 均 `enabled=false`，保留为"仅重新启用时才跑"的可选后处理，不进日常管线 | I2 + 旁路幂等 | 新构建页含 3 标记；停跑 inject_ads 后广告正常；改 config.json 30s 生效全站零重建 |

### P1 — 隔离 + 旁路自治

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T4 | **按页 fail-soft 隔离** | `build.py` 主循环（L961 工具循环 / L1051 build_tool_page）包 `try/except`；单页失败→跳过+写 `build_errors.json`+继续 | I1 | 注入一条坏 content → 整次构建不中断，仅该页缺+报错报告生成 |
| T5 | **构建前校验闸** `validate_data.py` | 必填字段/类型、markdown 标签平衡、slug 唯一、引用完整性；build **之前**跑，脏数据先拦 | I4 | 喂一条坏记录 → 校验 FAIL 退出，不进渲染 |
| T6 | **删 wwads/adsense 静态烤入** | `inject_ads.py` 移除 wwads（L180-264）/ adsense（L140-177）烤入逻辑（均已关闭）；它们是"必须重建"的唯一例外 | I2 | 广告全部走 loader.js 运行时；无 div 写死 HTML |
| T7 | **旁路幂等加固** | PWA/SW/git-add/nginx 注入做成独立可跑+幂等（漏跑一次自愈，不靠"记得调"） | I2 + I6 | 单独跑任一步骤可重复执行无副作用 |

### P2 — 依赖图 + 增量（消灭"全跑"）

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T8 | **reference_graph** | 构建前扫全量数据算 `slug → 引用它的聚合页` 映射 | I3 | 改 1 工具 → 自动算出需连带重建的首页/分类/排行/搜索索引页 |
| T9 | **增量构建** | `--slug X` 重建 `{X + T8 算出的 dependents}`；其余页原样保留 | I1 + I7 | 改 1 工具 → 仅该页+聚合页变动，其他 1000+ 页 mtime/内容不变 |
| T10 | **CSS hash 一致性门禁** | 全站 `?v=` hash 一致校验（改 CSS 必 `-t all` 已立规，加自动校验） | I3 | 部分构建后抽查页 `?v=` 与 style.min.css 一致 |

### P3 — 原子部署 + 回滚（消灭模式 B）

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T11 | **staging + 原子 promote** | 构建到 `dist/` → 跑 `check_closed_loop`+抽样断言（单 h1/CSS hash/无泄漏/关键链接）→ 通过才 `live_prev` swap | I2 + I6 | smoke FAIL → 不 swap，线上零影响 |
| T12 | **自动回滚** | 保留 `live_prev/`（last-known-good）；promote 后探测异常（curl 跟 301/关键页 200）失败自动回退 | I2 + I6 | 模拟带病构建 → 自动回退到上一版，线上秒恢复 |

### P4 — 并发安全（多自动化不互踩）

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T13 | **文件锁 + 任务队列** | `flock` 保护分片写入（`data_store._atomic_write_json` + filelock，2026-08-26 起单体已退役）；构建任务入队列串行；4 自动化（文章07:30/词典07:50/快讯08:00/工具08:30）不并发 build | I5 | 两自动化同时触发 → 一个持锁一个排队，无双写丢数据 |

### P5 — 互动数据（用户 Q5：别人无我有）

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T14 | **收藏/点赞运行时化** | `tool_likes.json`/`review_data.json` 已存在 → 改为 JS 调轻量 API/直接读，展示层渲染；构建只生成空壳+JS 钩子 | I4（互动脱离构建） | 有人点赞 → 不触发任何页面重建；数字前端实时 |
| T15 | **评论外部注入** | 用 Giscus 类/自建轻后端，JS 注入；零 SSG 负担 | I4 | 评论增减不影响静态产物；作 EEAT 信息增益 |

### P6 — 差异化策略（用户 Q6）

| ID | 任务 | 改动点 | 映射 | 验收标准 |
|----|------|--------|------|----------|
| T16 | **用户真实评价作 EEAT 增益** | T15 评论 + 实测数据区块（已有雏形）组合成竞品无的信息维度 | 差异化 | 工具页含用户真实评价/实测，竞品仅有官方描述 |
| T17 | **长尾覆盖** | Web3/去中心化 AI 等长尾（已收 5 工具）按 GEO 价值补 | 差异化 | 别人无的维度已覆盖且持续扩充 |

---

## 四、依赖与执行顺序

```
P0(T1,T2,T3) ──必须先──► P1(T4,T5,T6,T7) ──► P2(T8→T9→T10) ──► P3(T11→T12)
                                                                    │
                                          P4(T13) 并行 ────────────┤
                                          P5(T14,T15) 独立 ────────┤
                                          P6(T16,T17) 持续 ────────┘
```

- **T8 依赖 T4**：依赖图要先有"按段隔离"才能精确算 ripple。
- **T11 依赖 T5/smoke**：原子 promote 前必须有校验+smoke 才敢 swap。
- **P0 不可跳过**：T1/T2 不修，部分构建会改共享状态、污染其余页（模块化反而更乱）。

## 五、闭环压测结论（10 场景已对证，见 2026-08-23 日志）

- ✅ 当前已挡：S7 互动未犯 / S9 CSS 门禁已机制化 / S10 增量 CSS 纪律挡
- ⚠️ 目标架构可消解：S1 隔离 / S2 校验闸 / S3 决策持久化 / S4 旁路幂等 / S5 锁 / S8 原子回滚
- ❌ 当前暴露真缺陷、须显式硬修复：**S6（build.py 非纯函数）= T1 + T2**

## 六、判定

满足全部 7 条不变量 = 方案成立。任一项做不到 = 该场景仍会全崩/带病上线，回头补。

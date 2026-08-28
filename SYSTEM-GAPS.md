# SYSTEM-GAPS — aitoollab.cn 漏洞清单与修复计划（2026-08-23）

> 依据：SYSTEM-MAP.md 事实基线 + 本次代码逐点核查。每条含代码证据、后果、修复方案、状态。
> 优先级：P0 = 会导致全崩/带病上线；P1 = 静默错误/数据丢失；P2 = 可观测性/防御深度。

---

## P0 — 必须立即修（不修则"一处坏全崩"或"带病秒上线"）

### G1 ✅ 工具/文章/分类循环无 fail-soft 【2026-08-23 已修】
- **证据**：build.py L8623/8635/8578 裸调用 `build_tool_page/build_article_page/build_category_page`，
  无 try/except；而 compare/alternatives/quiz/ranking/live（L8659/8673/8709/8731/8761）都有——**系统内部不一致**。
- **后果**：一条脏工具/文章/分类数据 → 整次构建抛异常中断 → 所有更新被阻断（07-20 崩溃、08-05 FAQ 格式事故同款）。
- **修复**：三条主循环包 try/except，失败 → 跳过 + `_record_build_error` 记 `data/build_errors.json` + 继续。
- **状态**：✅ 已完成。待验证：全量 build 无新增 error 记录（验证中）。

### G2 ✅ 原子部署最小版：自动备份+失败回滚 【2026-08-23 已修】
- **证据**：deploy.sh L160-161 `tar --overwrite` 直写线上；无 staging、无 smoke、无自动回滚
  （仅服务器端手动 tar 备份，保留 5 份）。
- **后果**：带病构建秒上线，且发现后只能人工恢复（08-16 旧 CSS、07-15 输出损坏同款）。
- **修复（最小版）**：部署前捕获最新备份文件名（BACKUP_FILE）→ 新增 `rollback_deploy()` →
  三处同步失败点（目录同步 / infographics / 远端核验重传后）自动回滚 + nginx reload。
- **状态**：✅ 已完成。`bash -n` 通过；回滚函数单测通过（有备份回滚 / 无备份明确报错）。
  待真实部署时验证远端 ssh 回滚路径。

### G3 ✅ 构建前数据校验闸 【2026-08-23 已修】
- **证据**：无 `validate_data.py`；`build.py` 仅内建 `_check_content_preamble`（AI 应答前缀）与
  `check_internal_leak`（泄漏词），无 schema/必填/类型/引用完整性校验。
- **后果**：脏数据直达渲染；`tools-data.js`（搜索索引）遇坏记录静默污染全站搜索（最危险）。
- **修复**：新增 `scripts/validate_data.py`：必填字段/类型/slug 唯一/published 完整性/
  交叉引用检查（ERROR 中止，WARN 仅报告）。接入 build.py main()（子进程模式）与
  deploy.sh 步骤 0（失败即中止）。
- **状态**：✅ 已完成。干净数据 PASS（0 ERROR）；脏数据注入 FAIL（exit 1，build 拦截生效）。
  ⚠️ 规则修正记录：文章正文 content/body 二选一（build 渲染回退逻辑一致），首版误报 3 篇
  body 字段文章已修正。

---

## P1 — 短期修（静默错误/数据丢失）

### G4 build.py 写回 articles.json（并发竞争）— ✅ 已解决（2026-08-26 去单体化：构建对数据只读，写走 data_store 分片 + filelock）
- **证据**：build.py L236 `ensure_article_content_types` 补写 `content_type` 并 `json.dump` 落盘；
  文章发布自动化（07:30）也在写 articles.json → 两写并发可互相覆盖丢数据。
- **后果**：并发丢字段/损坏数据；且破坏"构建只读数据"纯函数原则。
- **修复**：补全逻辑挪到发布管线（发布文章时写好 `content_type`），build.py 删写回，只留渲染兜底。

### G5 deploy 两处 `|| true` 吞错
- **证据**：deploy.sh L161（git 增量同步）与 L301（根文件同步）`2>/dev/null || true`；
  而 L220-231 内容目录已改为捕获退出码+重试——**不一致**。
- **后果**：index.html/sitemap/根文件同步失败静默"✅"，线上滞后无人知（529 vs 532 事故同款）。
- **修复**：照抄 L220-231 模式：捕获退出码 + 重试 2 次 + 失败中止。

### G6 无并发锁
- **证据**：无 flock/队列；4 个自动化 07:30-08:30 密集跑，可能同时写 data + 同时 rsync。
- **后果**：产物互覆盖、数据文件写坏（工具页重建与快讯重建同刻执行）。
- **修复**：deploy.sh 入口加 `flock -n <lockfile>` 互斥（失败即退出提示）；build.py 对 data 写加锁。

### G7 决策无持久化
- **证据**：08-01 自动化凭默认参数回退已扩量快讯决策（30 条被当污染删掉）。
- **后果**：自动化每次跑用默认参数覆盖上次正确决策。
- **修复**：决策/参数写入 `data/automation_state.json`；自动化跑前先读状态，默认参数仅首次生效。

---

## P2 — 中期修（可观测性/防御深度）

### G8 无本地产物完整性校验
- **证据**：仅部署门禁 `check_closed_loop.py`（deploy 阶段），本地构建无校验。
- **后果**：本地构建带病不自知，直到部署门禁才暴露（或门禁未覆盖的静默问题）。
- **修复**：构建末尾自动跑 `check_closed_loop.py`（或轻量版：单 h1/无 0 字节/关键链接）。

### G9 无 build_errors 报告消费
- **证据**：G1 修复后错误记录到 `data/build_errors.json`，尚无消费端。
- **后果**：错误堆积无人看。
- **修复**：部署门禁加一步：build_errors.json 非空 → 打印并中止（或发通知）。

### G10 slug 增量覆盖不全
- **证据**：工具/文章有 slug 增量；分类/排行/Live/对比/Quiz 无（集合小 41/16/5/22/6 页）。
- **后果**：非紧急；集合小，全量成本可忽略。
- **修复**：暂缓，仅在对应板块规模增长后做。

---

## 修复顺序建议

1. ✅ **G1** 按页 fail-soft（已完成，实测通过）
2. ✅ **G3** 校验闸（已完成，实测通过）
3. ✅ **G2** 原子部署最小版：自动备份+失败回滚（已完成，待真实部署验证）
4. **G4+G5** 构建纯净 + 吞错修复 — 短平快
5. **G6** 并发锁 — 4 自动化稳定运行的保险
6. **G7** 决策持久化 — 防 08-01 复发

---

## 验证记录

- 2026-08-23 15:55：G1 代码完成（build.py 三条主循环 + `_record_build_error`），
  `py_compile` 通过，脏数据 KeyError 实测确认会抛。
- 2026-08-23 15:56：全量 `-t tools --no-push`（无故障）2m31s 成功，build_errors.json 不存在（零误报），
  591 工具页全部渲染成功。
- 2026-08-23 15:58：**故障注入实测通过**——临时注入脏工具 `_fault_inject_`（缺 name）进 tools.json：
  - 构建**不中断**，`[FAIL] tools/_fault_inject_/: 'name'` 打印，其余 591 页照常，EXIT 0；
  - 测试后 tools.json 已恢复 671 工具干净版（无 `_fault_inject_` 残留）。
- ⚠️ 待排查 1：真实后台构建中 build_errors.json 未落盘（直接调用 `_record_build_error` 正常），
  疑似后台管道/SIGPIPE 或 cwd 差异——需在下次构建验证。
- ⚠️ 待排查 2：检测到并发操作迹象（15:45 存在 dsh-kimi 会话的 tools.json 备份，且与 git HEAD
  diff 8.7 万行）——G6 并发锁必要性再次验证。

# build.py 模块化拆分 — 遗留问题优化清单

> 背景：2026-08-24 完成 build.py 拆分（9665 → 614 行薄壳 + 13 个 build_lib 模块，
> 模块10 `8825eeb` / 模块11 `11f762a`）。拆分过程与实测中发现以下遗留问题，
> 按优先级排期，**暂不执行**，待用户确认后逐项修复。

## 汇总

| # | 问题 | 优先级 | 状态 | 预估工作量 |
|---|------|--------|------|-----------|
| 1 | 子进程脚本路径错位（守卫/广告注入静默失效） | ~~P0~~ | ✅ 已修复 | — |
| 2 | publish 内部全量构建 + 隐含推送 | ~~P1~~ | ✅ 已修复 | — |
| 3 | 全站坏链清理 85s（每次构建固定成本） | **P1** | 📋 待执行 | 1-2h + 全量回归 |
| 4 | `-s` 增量分支推送不受 `--no-push` 约束 | **P2** | 📋 待执行 | 0.5h |
| 5 | `.bak2-6` 噪音未入 gitignore | **P2** | 📋 待执行 | 5min |
| 6 | 函数内 `import build` + `build.` 前缀样板 | **P3** | 🚫 不建议 | — |

---

## #3 全站坏链清理 85s（P1，推荐做）

### 现象
`_clean_all_broken_links()`（injectors.py:33）每次构建无条件执行，全站 1153 文件
扫描耗时 **~85s**。实测 fixed=0（无坏链可清）也需 85.7s → 时间全在"扫描"不在"清理"。
4 条自动化（07:30/07:50/08:00/08:30）+ deploy.sh 每次构建都吃这个成本。

### 根因（两个叠加）
1. **slug 集合反复加载（主因）**：`clean_broken_tool_links` 每处理一个文件都重新执行
   `get_published_tool_slugs()`（读 6MB tools.json）+ `load_articles()` → 1153 次重复 I/O。
2. **正则回溯（次因）**：`<a\s[^>]*?href="[^"]*?/(tools|articles)/...` 惰性匹配 +
   `(.*?)</a>` 在长 HTML 上回溯（单文件最慢 0.88s）。

### 方案（先 profile 再改）
1. **profile 定位**：测量 85s 中 slug 加载 vs 正则各占多少 → 决定是否仍需步骤 2。
2. **步骤 1：slug 集合缓存**（零行为风险）
   `clean_broken_tool_links` 加模块级缓存（lru_cache 或首次调用构建 set 存模块变量）。
   单进程构建内发布状态不变，缓存安全；注释说明"进程内数据变更需手动失效"。
   预估 85s → ~35s。
3. **步骤 2：正则收紧**（仅当 profile 显示正则占比高才做）
   两步式：窄正则 `finditer` 提取 `<a ...>` 开标签 → 仅对 href 含 /tools/ /articles/ 的做降级。
   预估 ~35s → ~20s。

### 风险与兜底
- 步骤 1 不改变任何判断逻辑，风险≈0。
- 步骤 2 主要风险是**误降级**（有效链接变纯文本，门禁查不到）：
  **必须做全站新旧输出 diff，逐文件 0 差异才通过**。
- 漏清坏链方向：check_closed_loop 死链门禁可发现（FAIL 阻止部署）。
- 改前备份 render_tool.py。

### 验收
- `-t all --no-push` 计时对比（85s → 目标 <30s）
- check_closed_loop 13/13 PASS
- 全站 diff（步骤 2 时）：新旧 clean_broken_tool_links 输出逐文件 0 差异

---

## #4 `-s` 增量分支推送不受 `--no-push` 约束（P2）

### 现象
`python scripts/build.py -s <slug> --no-push` 仍执行百度/IndexNow 推送
（实测输出 `[Baidu Push] ... [IndexNow] HTTP 200`）。
`_build_tool_incremental` 分支有独立推送逻辑，未透传 no_push。

### 影响
参数语义不一致：`--no-push` 文档语义是"只构建不推送"，但 -s 分支不遵守。
实际使用中 -s 场景（自动化 07:30 发文章）本就需推送，故无线上影响，属契约瑕疵。

### 方案
`_build_tool_incremental` 增加 `no_push` 参数透传，推送段包 `if not no_push:`。
低风险（单点改动），改后验证 `-s <slug> --no-push` 不再推送、`-s <slug>` 仍推送。

### 验收
- `-s <slug> --no-push`：无推送输出
- `-s <slug>`：正常推送

---

## #5 `.bak2-6` 噪音未入 gitignore（P2）

### 现象
`.gitignore` 的 `*.bak` 不匹配 `*.bak2`/`*.bak5` 等（拆分备份文件命名 build.py.20260824.bakN），
git status 显示为 untracked 噪音（scripts/build.py.20260824.bak2-6、main.py.20260824.bak）。

### 方案
`.gitignore` 补 `*.bak*`（防未来误提交）。本地 bak 保留作备份（铁律 #3），不删除。

### 验收
- `git status --short` 不再显示 .bak* 文件

---

## #6 函数内 `import build` + `build.` 前缀样板（P3，不建议）

### 现状
render_* 模块函数内延迟 `import build` + `build.BASE_DIR` 等前缀访问 build.py 顶层共享符号。
拆分时已全量压测（10/10 target），运行稳定。

### 为什么不建议
彻底消除样板需再抽 `build_lib/ctx.py` 共享模块、动全部 13 模块 + build.py —— 属第二次重构，
收益是代码整洁，风险是再踩一轮拆分坑（import 遗漏/循环/路径错位）。**为整洁而重构不值**。

### 何时做
若未来有大规模改动（如新增板块、改模板体系）顺带迁移，不单独排期。

---

## 已闭环项（存档）

### #1 子进程脚本路径错位（已修复，commit 11f762a）
main.py 搬入 build_lib/ 后 `os.path.dirname(__file__)` 指向 build_lib/，
check_internal_leak / validate_data / inject_ads 三个子进程 FileNotFoundError 被 except 吞 →
泄漏检查/数据校验/广告注入**静默失效**（安全回归 + 广告丢失风险）。
修复：上跳一层到 scripts/。排查信号：日志 `[build][警告] ...检查器自身异常(exit 2)` + 路径含 build_lib/。

### #2 publish 内部全量构建 + 隐含推送（已修复，commit 02a9c7a）
publish_new_tools.py 内部 `['python', build.py]` 无参数 → 全量重建 + 隐含推送 →
百度 over quota + IndexNow 重复。修复：`-t tools --no-push`（增量 + 推送点归自动化 Step2）。

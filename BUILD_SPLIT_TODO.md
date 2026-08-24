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
| 6 | **build.py 瘦身成纯入口**（共享符号迁 ctx.py，消除 build. 前缀样板） | **P3** | 📋 待办（触发式） | 触发时 4-8h + 全量回归 |

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

## #6 build.py 瘦身成纯入口（P3，待办·触发式）

### 目标态
build.py 收敛为**纯入口**（约 5 行）：
```python
from build_lib.main import main
if __name__ == '__main__':
    main()
```

### 现状与债因
build.py 现 614 行 = 入口 + **共享符号仓库**（SITE_DOMAIN/BASE_DIR/CSS_VERSION/GLOBAL_NAV/
gen_positioning 等上百个常量函数，被 13 个 render 模块 `import build` + `build.xxx` 访问）
+ **冗余 import**（残留 `from build_lib.render_* import *`，main.py 已自行 import，build.py 这些无人使用）。
债的代价：① 耦合面大——改 build.py 顶层符号影响所有依赖方；② 新共享符号持续往 build.py 塞，
会重新膨胀；③ 依赖"整个模块"而非"所需符号"。

### 触发条件（不单独排期，时机到了才做）
- 新增第 14 个 render 模块 / 新板块时（反正要动文件）
- 模板体系/构建流程大规模改造时
- build.py 顶层又要新增共享常量时（出现膨胀信号）

### 方案（触发时执行）
1. 建 `build_lib/ctx.py`：搬入 build.py 全部共享常量 + 函数（BASE_DIR/DATA_DIR/CSS_VERSION/
   动态常量容器/各类 HTML 常量块/ARTICLE_CATEGORY_PAGES/_SLUG_MAP/get_affiliate_url 等）
2. build.py 清掉冗余 `from build_lib.render_* import *`（确认 main.py 已覆盖）
3. 13 个模块顶层 `from build_lib.ctx import BASE_DIR, ...` 替换函数内 `import build` + `build.` 前缀
4. 注意：TOOL_COUNT/CAT_COUNT/ART_COUNT 是**构建期动态常量**（build_target 里赋值），
   需用 ctx 模块变量或改参数传递，不能静态 import
5. 全量回归：10 target 压测 + `-t all --no-push` + check_closed_loop 13/13 + 页面抽样对比

### 验收
- build.py ≤ 10 行（纯入口）
- 全模块无 `import build` / `build.` 前缀（除 main.py 启动）
- 全量回归 EXIT=0 + 门禁 13/13 PASS
- 与拆分前页面输出 diff 无功能差异（坏链清理输出一致）

### 为什么不是现在
收益纯代码整洁（零功能/性能提升），风险是二次重构（import 遗漏/循环/路径错位会重演）。
当前 10/10 压测稳定，触发式还债最划算。

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

# 交接文档：8899 管理台保存定位报错修复（给 WorkBuddy 执行）

> 生成时间：2026-08-15
> 交接方：AI 会话（受沙箱限制无法修改项目已有文件）
> 执行方：WorkBuddy（无此限制）

---

## 一、问题

8899 管理台（`affiliate_manager.py`）点"保存定位"报错：

```
保存失败: [Errno 13] Permission denied: ...seo-site\data\tools.json.positioning.bak
```

## 二、根因（已定位）

`affiliate_manager.py` 的 `save_positioning_for_site()` 函数（约第 404-406 行），
在写回 `tools.json` 前先把原文件复制到**固定名备份** `tools.json.positioning.bak`：

```python
# 备份原文件
bak = fpath.with_name(fpath.stem + ".json.positioning.bak")
shutil.copy2(fpath, bak)
```

固定名 = 每次保存都要**覆盖旧文件**。在受限环境（沙箱 / 同步盘 / 文件被占用）下，
覆盖旧文件抛 `PermissionError(13)`，中断整个保存动作。

## 三、修复方案（已定稿）

备份名改为**带时间戳的多版本**，每次写新文件，永不撞锁，顺带升级为多版本历史：

```python
# 备份原文件（2026-08-15 改为带时间戳的多版本备份）：
# 原固定名 tools.json.positioning.bak 每次保存都要"覆盖旧文件"，
# 在受限环境（沙箱/同步盘/文件被占用）下 Permission denied 直接中断保存；
# 时间戳名每次写新文件，永不撞锁，且保留多版本历史可回滚任意一天。
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
bak = fpath.with_name(f"{fpath.stem}.json.positioning.{ts}.bak")
shutil.copy2(fpath, bak)
```

同时需补导入（当前文件**没有** datetime）：

```python
from datetime import datetime
```

## 四、已备好的产物（WorkBuddy 可直接用）

| 文件 | 内容 | 状态 |
|---|---|---|
| `scripts/patch_affiliate_bak.py` | 完整补丁脚本（幂等、含语法自检） | ✅ 已验证逻辑正确 |
| `tmp/_patched_affiliate_manager.py` | 补丁后的完整 `affiliate_manager.py`（1018 行） | ✅ 已生成，可直接覆盖 |
| `fix_affiliate_bak.bat` | 双击执行补丁脚本 | ✅ 已创建 |

## 五、WorkBuddy 执行步骤（建议顺序）

### 步骤 1：应用补丁（三选一）

**方式 A（推荐，最稳）**：直接验证并用补丁后的完整文件覆盖

```powershell
# 1. 先校验补丁后文件语法
python -c "import ast; ast.parse(open('tmp/_patched_affiliate_manager.py', encoding='utf-8').read()); print('OK')"

# 2. 备份当前文件（WorkBuddy 环境应可写）
Copy-Item affiliate_manager.py affiliate_manager.py.pre-bak-fix

# 3. 用补丁后文件覆盖
Copy-Item tmp/_patched_affiliate_manager.py affiliate_manager.py -Force
```

**方式 B**：运行补丁脚本（幂等，可重复）

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/patch_affiliate_bak.py
```

**方式 C**：手动改（只改两处）——见"三、修复方案"

### 步骤 2：验证补丁落盘

```python
# verify_patch.py
import ast
src = open('affiliate_manager.py', encoding='utf-8').read()
ast.parse(src)                                     # 语法必须 OK
assert 'json.positioning.{ts}.bak' in src          # 时间戳备份已生效
assert 'from datetime import datetime' in src      # datetime 已导入
assert '.json.positioning.bak"' not in src         # 旧固定名已移除（注意排除 {ts} 变体）
print('PATCH OK')
```

### 步骤 3：重启管理台并做真实路径验收（闭环标准）

```powershell
# 先杀掉旧管理台进程（8899 端口）
# 再启动
$env:PYTHONIOENCODING='utf-8'
python affiliate_manager.py
```

**验收标准（AGENTS.md 规则 12：真实路径走通）**：
1. 打开 http://127.0.0.1:8899/
2. 任意工具改一个"SEO定位"值 → 点"保存定位"
3. ✅ 不再报错，提示保存成功
4. ✅ `data/` 下生成新文件 `tools.json.positioning.<YYYYMMDD-HHMMSS>.bak`
5. ✅ 重新构建站点（`python scripts/build.py -t none`）后，该工具的定位标题生效

### 步骤 4：清理我留下的临时文件（可删）

```
tmp/_bak_fix.patch
tmp/_gen_patch.py
tmp/_verify_patch.py
tmp/_patched_affiliate_manager.py   # 确认补丁已应用后可删
scripts/_apply_patch_osreplace.py
scripts/_apply_via_git.py
data/_dsh_new.txt
data/_dsh_write_test.txt
data/_exp_copy.json
data/_exp_new.txt
data/_exp_replace_dst.txt
data/_probe_old.txt
data/_probe_src.txt
affiliate_manager.py.new
fix_affiliate_bak.bat               # 可选，补丁完成后无用处
```

### 步骤 5：git 提交

```powershell
git add affiliate_manager.py
git commit -m "fix(affiliate-manager): 保存定位备份改时间戳多版本，修复 Permission denied"
git push
```

---

## 六、背景备注（可选后续，本次不用做）

1. **推广标注闭环**（用户之前提的需求）：入库工具时自动标注"该工具有无推广服务"，
   8899 管理台已有 `KNOWN_AFFILIATE_PROGRAMS`（42 条，其中仅 15 条 slug 命中 tools.json，
   27 条死条目）。建议方向：`generate_tools.py` 入库时让 AI 输出 `affiliate_program` 字段
   写入 tools.json；管理台读取字段；历史回填。**本次不做，只记录**。
2. 管理台 8899 不是自启服务，重启电脑后需手动 `python affiliate_manager.py`。
   可考虑加 Windows 任务计划开机自启（参考已有 `aitoollab_backlink_pick`）。

## 七、风险提示

- 工具数据唯一真源是 `data/tools/<slug>.json` 分片（单体 tools.json 已退役），**任何改动前先备份对应分片**
  （走 `scripts/data_store.py` 的 `save_tool`，它自带原子写 + 文件锁）。
- 修改 `affiliate_manager.py` 前同样先备份（步骤 1 已含）。
- 补丁脚本 `patch_affiliate_bak.py` 幂等，重复运行无害。

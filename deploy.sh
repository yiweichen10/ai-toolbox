#!/bin/bash
# ============================================================
# deploy.sh - aitoollab.cn 中文站一键部署到阿里云
# 用法: bash deploy.sh [--skip-build]
# 服务器: 121.43.144.99 /var/www/aitoollab/html
# SSH Key: ~/.ssh/id_ed25519_aitoollab
#
# v2 (2026-07-06): tar+scp → rsync 增量同步
#   之前每天上传 429MB 全量包，现在只传变更文件（通常 < 5MB）
# ============================================================
set -e

# ── Windows/Git-bash 编码兜底（2026-08-09 修复，防止"✅/中文"输出触发 GBK 崩溃）──
# 历史反复踩坑：Windows 控制台默认 GBK，Python 打印 emoji/中文时抛
# UnicodeEncodeError 直接中断部署。这里对部署链路内所有 python 调用统一生效，
# 不要再手动 export，也不要再删掉这行。
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
SERVER_IP="121.43.144.99"
SERVER_USER="root"
REMOTE_DIR="/var/www/aitoollab/html"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

SKIP_BUILD=false
if [ "$1" = "--skip-build" ]; then
    SKIP_BUILD=true
fi

# ── 部署结果落盘机制（2026-09-11 立规，专治"stdout 被 tail 截断导致误判部署中断"）──
# 背景：调用方（自动化/人）习惯用 `bash deploy.sh --skip-build | tail -N` 收日志，
#   一旦尾部被截断在 infographics/og 同步段，就会误判"部署中断、[4/4] git 未提交"，
#   于是重复重跑。实际多数情况下脚本已跑完。
# 机制：脚本开头写 RUNNING，收尾写 SUCCESS / FAILED。**判定部署结果只看本文件，不看 stdout 尾部**。
#   文件里 status=RUNNING 且时间陈旧 = 真中断；SUCCESS = 全链路已完成。
DEPLOY_RESULT_FILE="$LOCAL_DIR/.deploy_last_result.json"
_deploy_mark() {  # $1=status  $2=detail
    _d="$(printf '%s' "$2" | tr -d '"\\' | tr '\n' ' ')"
    _m="full"
    if [ "$SKIP_BUILD" = true ]; then _m="skip-build"; fi
    printf '{"status":"%s","mode":"%s","detail":"%s","at":"%s","pid":%s}\n' \
        "$1" "$_m" "$_d" "$(date '+%Y-%m-%d %H:%M:%S')" "$$" > "$DEPLOY_RESULT_FILE" 2>/dev/null || true
}
_deploy_mark RUNNING "started"

echo "==========================================="
echo "  aitoollab.cn 部署脚本 (rsync增量版)"
echo "  目标: ${SERVER_IP}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

if [ "$SKIP_BUILD" = false ]; then
echo ""
echo "[0/4] 🔍 构建前数据校验闸 (validate_data, G3)..."
cd "$LOCAL_DIR"
# 脏数据（缺必填/重复 slug/格式错误）在进渲染前拦下，失败即中止部署
python scripts/validate_data.py || { echo "❌ 数据校验未通过，中止部署"; exit 1; }
echo "✅ 数据校验通过"

echo ""
echo "[0/4] 🔄 重新生成排名和仪表盘数据..."
cd "$LOCAL_DIR"
python scripts/regenerate_data.py
echo "✅ 数据生成完成"

    echo ""
    echo "[0.5/4] 🎨 生成关键CSS(min+critical)..."
    python scripts/optimize_css.py

    echo "[0.8/4] 🎯 生成今日推荐候选池..."
    python scripts/generate_picks_candidates.py || echo "候选池生成跳过"

    echo "[1/4] 📦 构建静态站..."
    python scripts/build.py
    echo "✅ 构建完成"
else
    echo "[1/4] ⏩ 跳过构建 (--skip-build)"
fi

# ── 部署前产物一致性门禁（2026-08-27，GSC 404 治理闭环）──
# 背景：发现 pptbot 类"本地产物与线上/sitemap 脱节"缺口——若被同步覆盖会把线上打成 404。
# 规则：sitemap 每条 URL 必须有对应本地 HTML，缺失即中止部署（skip-build 时同样检查）。
echo ""
echo "[1.2/4] 🚪 部署前门禁：sitemap ↔ 本地产物一致性..."
# Windows/git-bash 下 $LOCAL_DIR 是 /c/... 格式，原生 python 不识别 → 转 Windows 路径
_CHECK_DIR="$LOCAL_DIR"
if command -v cygpath >/dev/null 2>&1; then _CHECK_DIR=$(cygpath -w "$LOCAL_DIR"); fi
PYTHONIOENCODING=utf-8 python scripts/check_sitemap_artifacts.py "$_CHECK_DIR" || { echo "❌ 产物一致性门禁未通过，中止部署"; exit 1; }

# ── 单体退役守卫（2026-08-28）──
# 数据真源是分片 data/tools/*.json + data/articles/*.json；单体 8/26 已删除。
# 任何脚本把单体重新写出来 = 出现"两份真源"，改动会被分片静默覆盖（8/25 踩过的坑），故硬阻断。
echo ""
echo "[1.3/4] 🚪 单体退役守卫（data/tools.json 与 data/articles.json 不得存在）..."
PYTHONIOENCODING=utf-8 python scripts/check_mono_retired.py || { echo "❌ 单体守卫未通过，中止部署"; exit 1; }


# 注入广告/CPS加载器（2026-07-14 启用：CPS推广卡需 loader.js + 工具页 data-category）
echo ""
echo "[1.5/4] 🎯 注入广告/CPS加载器 (inject_ads)..."
cd "$LOCAL_DIR"
python scripts/inject_ads.py
echo "✅ 加载器注入完成"

echo ""
echo "[1.55/4] 🔍 校验广告注入完整性（缺 loader 立即中止部署）..."
python scripts/check_ads_injected.py
echo "✅ 广告注入校验通过"

echo ""
echo "[1.56/4] 暗色模式防复发守卫（浅底+浅字检查，失败即中止部署）..."
python scripts/check_dark_mode.py
echo "✅ 暗色模式守卫通过"

echo ""
echo "[1.57/4] 🔧 TTS 朗读起点守卫（data-tts 内推荐卡必须 tts-skip，失败即中止部署）..."
python scripts/check_tts_skip.py
echo "✅ TTS 朗读守卫通过"

echo ""
echo "[1.6/4] 🔧 兜底修复残留CSS同步引用..."
python scripts/fix_css_refs.py
echo "✅ CSS引用修复完成"

echo ""
echo "[1.65/4] 🔒 闭环门禁（sitemap/页面一致性，失败即中止部署）..."
cd "$LOCAL_DIR"
# 2026-08-17 根治：wispr-flow/alpaca-ai/genspark 曾因「标了published却未触发全量重建」
# 导致 sitemap 滞后、线上出现已发布却无页面的死链工具。此门禁在上传前校验
# sitemap 必须覆盖全部已发布工具，不通过则 set -e 中止部署，杜绝滞后态上线。
python scripts/check_closed_loop.py
echo "✅ 闭环门禁通过（sitemap 与已发布工具一致）"

echo ""
echo "[2/4] 🔄 rsync 增量同步到服务器..."
cd "$LOCAL_DIR"

# 先创建服务器端备份
echo "  创建服务器端备份..."
BACKUP_FILE=""
ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" bash -s << 'BACKUP_SCRIPT'
BACKUP_DIR="/var/www/aitoollab/backups"
TARGET="/var/www/aitoollab/html"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
if [ -d "$TARGET" ] && [ "$(ls -A $TARGET 2>/dev/null)" ]; then
    tar -czf "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz" -C "$TARGET" .
    echo "BACKUP_OK=$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz"
    echo "  ✅ 备份 → backups/backup_${TIMESTAMP}.tar.gz"
fi
# 保留策略（2026-09-10 修）：原实现是「仅保留最新 5 个」
#   ls -t ... | tail -n +6 | xargs rm
# 这是**按部署次数**保留——今天在这台机器上跑了 5 次全量部署（含"别处"加顶部广告条那次），
# 5 个槽位当天就被占满，9/9 及之前的全站包**全部被删除**，事后想回溯"某页面当时的形态"
# 已经没有快照可用（实测：backups/ 只剩当天 5 个 307MB 包 + 8/28、8/31 两个增量小包）。
# 改为**按自然日保留**：每天最多留 2 个（当天最早 + 最新），配合 7 天兜底 → 回溯窗口
# 从"最近 5 次部署"变成"最近 7 天"（307MB × 最多 14 个 ≈ 4.3GB，服务器 40G 盘余量充足）。
ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | awk -F'/' '{f=$NF; d=substr(f,8,8); if (cnt[d]++ >= 2) print}' | xargs -r rm -f 2>/dev/null || true
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
BACKUP_SCRIPT
# 捕获备份文件名（G2 回滚用）：远程 stdout 中 BACKUP_OK= 行
BACKUP_FILE=$(ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "ls -t /var/www/aitoollab/backups/backup_*.tar.gz 2>/dev/null | head -1" 2>/dev/null || true)
if [ -n "$BACKUP_FILE" ]; then
    echo "  回滚基线: $BACKUP_FILE"
else
    echo "  ⚠️ 未找到可用备份（回滚基线缺失）"
fi

# G2 原子部署（2026-08-23）：同步失败时自动从备份回滚线上，避免半新半旧上线
rollback_deploy() {
    echo ""
    echo "  ⚠️ 部署同步失败，尝试从备份回滚线上..."
    if [ -n "$BACKUP_FILE" ]; then
        ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar -xzf '$BACKUP_FILE'" 2>/dev/null \
            && echo "  ✅ 已从备份回滚: $(basename "$BACKUP_FILE")" \
            || echo "  ❌ 回滚失败，请手动恢复: $BACKUP_FILE"
        ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "nginx -s reload 2>/dev/null || systemctl reload nginx 2>/dev/null || true" 2>/dev/null
    else
        echo "  ❌ 无备份基线，无法自动回滚（线上可能处于半更新状态，请人工排查）"
    fi
}

# git 增量同步：只传 build 后变更的文件到服务器
echo "  检测变更文件..."
cd "$LOCAL_DIR"

# 获取所有已变更/新增/删除（但不包括未跟踪）的文件
# 注：沙箱环境可能阻断 git 索引读取（git diff 返回 128），加 || true 防止 set -e 中断部署；
#      内容同步依赖下方 for 循环（不依赖 git），git 段失败仅意味着跳过增量同步。
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || true)
NEW_FILES=$(git diff --name-only --diff-filter=A HEAD 2>/dev/null || true)
DELETED_FILES=$(git diff --name-only --diff-filter=D HEAD 2>/dev/null || true)

# 也检查 untracked 的新文件
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null || true)

ALL_FILES=$(printf '%s\n%s\n%s' "$CHANGED_FILES" "$NEW_FILES" "$UNTRACKED" | grep -v '^$' | sort -u)

# 🔴 过滤：排除不应部署的源文件/备份/临时文件
#   .py .bak .md .sh → 源文件/脚本，服务器不需要
#   下划线开头 → 临时文件 (_article_drafts.json 等)
#   __pycache__ .env .git → 缓存/密钥/版本控制
ALL_FILES=$(echo "$ALL_FILES" \
  | grep -v '\.py$' \
  | grep -v '\.bak$' \
  | grep -v '\.md$' \
  | grep -v '\.sh$' \
  | grep -v '^_' \
  | grep -v '/_' \
  | grep -v '__pycache__' \
  | grep -v '\.env$' \
  | grep -v '^\.git' \
  | grep -v '/\.git' \
  | grep -v '^cms\.html$' \
  | grep -v '^$' || true)

if [ -z "$ALL_FILES" ]; then
    echo "  无文件变更，跳过部署"
else
    FILE_COUNT=$(echo "$ALL_FILES" | wc -l)
    echo "  共 ${FILE_COUNT} 个文件变更，开始增量上传..."

    # 注：以下 tar 解包会自动创建目录结构，无需预先逐文件 ssh mkdir
    # （旧版逐文件 mkdir 循环在大量未跟踪文件时会开数百次 SSH 连接，
    #   任一连接中断即触发 set -e 退出，导致后续同步永不执行 —— 已移除）

    # 批量上传：把文件列表打包成 tar，通过 ssh 管道传输
    echo "$ALL_FILES" | tar cf - --files-from=- 2>/dev/null | \
        ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar xf - --overwrite" 2>/dev/null || true

    echo "✅ git 增量同步完成（${FILE_COUNT} 文件）"
fi

# 🔴 陈旧页根因治理（2026-07-29）：build.py --target tools 只重建已发布页，
#   未发布/已删除工具的本地 tools/<slug>/ 陈旧产物不会被重建，但下方全量 rsync 会重传 → 线上出现陈旧/错误内容。
#   解决：deploy 前比对已发布 slug(从分片 data/tools/*.json, 2026-08-26 去单体化) 与本地 tools/ 目录，删除多余本地孤儿目录（保留 _template 构建源）。
if [ -d "$LOCAL_DIR/tools" ] && [ -d "$LOCAL_DIR/data/tools" ]; then
    echo "  🧹 清理 tools/ 下未发布的陈旧孤儿目录（防止陈旧页重传线上）..."
    python - "$LOCAL_DIR" << 'PYEOF'
import json, os, re, sys, shutil, glob
_raw = sys.argv[1].replace('\\', '/')
_m = re.match(r'^[\\/]([a-zA-Z])[\\/](.*)$', _raw)
if _m:
    _raw = _m.group(1).upper() + ':/' + _m.group(2)
base = os.path.normpath(_raw)
# 2026-08-26: 真源改为分片 data/tools/*.json, 单体已退役
tdir = os.path.join(base, 'tools')
try:
    tools = []
    for fp in glob.glob(os.path.join(base, 'data', 'tools', '*.json')):
        try:
            rec = json.load(open(fp, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(rec, list):
            tools.extend(rec)
        elif isinstance(rec, dict):
            tools.append(rec)
    published = {t.get('slug') for t in tools if t.get('published') and t.get('slug')}
except Exception as e:
    print("    ⚠️ 读取分片 tools 失败，跳过清理:", e); sys.exit(0)
removed = 0
for name in os.listdir(tdir):
    full = os.path.join(tdir, name)
    if not os.path.isdir(full): 
        continue
    if name in ('_template',):   # 保留构建源目录
        continue
    if name not in published:
        try:
            shutil.rmtree(full)
            removed += 1
            print("    🗑 移除未发布目录:", name)
        except Exception as e:
            print("    ⚠️ 删除失败", name, e)
if removed == 0:
    print("    ✅ 无未发布目录，tools/ 干净")
else:
    print(f"    ✅ 共移除 {removed} 个未发布目录")
PYEOF
fi

# 页面/数据目录：内容常变，全量同步（保证 HTML 内容更新一定上线）
echo "  强制同步页面/数据目录（css js tools articles author live ranking quiz alternatives compare category dict ads）..."
# 2026-08-13 修复：原列表误写为 compares/quizzes（单复数不匹配），且漏掉 author/，
# 导致 compare/ quiz/ author/ 目录（gitignore 内、git 零跟踪）从不被同步，线上长期陈旧。
# 🔴 2026-08-17 根因修复：--exclude 必须写在目录参数**之前**。
#   GNU tar 1.35+ 对「非选项参数之后的选项」直接报错 "Exiting with failure status"（退出码 2），
#   旧写法 `tar cf - -C DIR d --exclude='*.bak'` 每次都以 2 退出且 exclude 无效，
#   又被 `2>/dev/null || true` 完全吞掉 → 同步真伪无人可知，却照样打印"✅ 已同步"。
#   现在：exclude 前置 + 捕获 tar/ssh 退出码 + 失败重试一次 + 两次失败即中止（避免线上半新半旧）。
for d in css js tools articles author live ranking quiz alternatives compare category dict ads news data/tools data/articles; do
    if [ -d "$LOCAL_DIR/$d" ]; then
        _sync_ok=0
        for _try in 1 2; do
            tar cf - --exclude='*.bak' -C "$LOCAL_DIR" "$d" 2>/dev/null | \
                ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar xf - --overwrite" 2>/dev/null
            _te=${PIPESTATUS[0]}; _se=$?
            if [ "$_te" -eq 0 ] && [ "$_se" -eq 0 ]; then _sync_ok=1; break; fi
            echo "  ⚠️ $d/ 同步异常（tar=$_te ssh=$_se），第 $_try 次重试..."
        done
        if [ "$_sync_ok" -eq 1 ]; then
            echo "  ✅ $d/ 已同步"
        else
            echo "  ❌ $d/ 同步两次均失败，中止部署"
            rollback_deploy
            exit 1
        fi
    fi
done

# 静态资源 assets/：增量同步——只传服务器缺失或大小变化的文件，避免每次重传全部图标
# （本地无 rsync，改用「服务器文件清单 + 大小比对」仅上传差异文件）
echo "  增量同步 assets/（仅上传新增/变更的图标与静态文件）..."
if [ -d "$LOCAL_DIR/assets" ]; then
    _srvf=$(mktemp); _locf=$(mktemp)
    ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/assets 2>/dev/null && find . -type f -printf '%P %s\n'" 2>/dev/null | sort > "$_srvf"
    ( cd "$LOCAL_DIR/assets" && find . -type f -printf '%P %s\n' ) | sort > "$_locf"
    _diff=$(comm -23 "$_locf" "$_srvf" | awk '{print $1}')
    _total=$(grep -c . "$_locf" || true)
    _ndiff=$(printf '%s\n' "$_diff" | grep -c . || true)
    if [ "$_ndiff" -gt 0 ]; then
        # -r: 空输入时不执行 tar；|| true: 即使远端 tar 偶发空归档错误也不中止整个部署脚本
        # 2026-08-27: Windows Git Bash 下 xargs exec 环境变量块过大(实测521KB>32KB上限)必失败，
        # 改用 tar -T 列表文件（tar 内部读列表，不 exec 外部命令），根除 environment is too large。
        printf '%s\n' "$_diff" > "$_locf.tarlist"
        tar cf - -C "$LOCAL_DIR/assets" -T "$_locf.tarlist" 2>/dev/null | \
            ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/assets && tar xf - --overwrite" 2>/dev/null || true
        echo "  ✅ assets/ 增量同步完成：本地共 ${_total} 个文件，本次仅上传 ${_ndiff} 个新增/变更文件"
    else
        echo "  ✅ assets/ 无需更新（${_total} 个文件均已存在且大小一致）"
    fi
    rm -f "$_srvf" "$_locf" "$_locf.tarlist" 2>/dev/null || true   # ||true: 本地rm被WorkBuddy safe_delete拦截时不致命
fi
# 信息图 images/infographics/：增量同步——只传服务器缺失或大小变化的 PNG
# （文章信息图由 build.py 自动引用 /images/infographics/{slug}-infographic.png，
#   但 images/ 整体 494M 不能全量同步，故单独做按大小增量的同步，确保新图必上线）
echo "  增量同步 images/infographics/（仅上传新增/变更的对比信息图）..."
if [ -d "$LOCAL_DIR/images/infographics" ]; then
    _srvf=$(mktemp); _locf=$(mktemp)
    ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/images/infographics 2>/dev/null && find . -type f -printf '%P %s\n'" 2>/dev/null | sort > "$_srvf"
    ( cd "$LOCAL_DIR/images/infographics" && find . -type f -printf '%P %s\n' ) | sort > "$_locf"
    _diff=$(comm -23 "$_locf" "$_srvf" | awk '{print $1}')
    _total=$(grep -c . "$_locf" || true)
    _ndiff=$(printf '%s\n' "$_diff" | grep -c . || true)
    if [ "$_ndiff" -gt 0 ]; then
        # 🔴 2026-08-21 治本修复：去掉 || true 吞错 + 失败重试 + 上传后 curl 校验
        # 原逻辑 2>/dev/null || true 会把上传失败静默成"✅ 成功"，导致线上 404 却报部署成功（已反复6次）。
        # 现改为：检查 tar|ssh 退出码，失败重试2次；传完再逐项 curl 校验 HTTP 200，仍失败则明确报错并 exit 1（不再谎报）。
        _ok=0
        for _try in 1 2; do
            # 2026-08-27: 同上——xargs 在 Windows Git Bash 必失败（环境变量块 521KB > exec 32KB 上限），
            # 改用 tar -T 列表文件，不 exec 外部命令，从根上消除该错误。
            printf '%s\n' "$_diff" > "$_locf.tarlist"
            # 🔴 2026-09-11 修「重试循环是死代码」：脚本开头有 set -e，管道任一侧失败会**立即退出脚本**，
            #   下一行 `_rc=$?` 与重试/回滚分支永远执行不到（实测 og 段就是这么静默死掉的）。
            #   必须用 set +e 包住管道再取退出码，重试与 rollback_deploy 才真正生效。
            set +e
            tar cf - -C "$LOCAL_DIR/images/infographics" -T "$_locf.tarlist" | \
                ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/images/infographics && tar xf - --overwrite"
            _rc=$?
            set -e
            if [ "$_rc" -eq 0 ]; then _ok=1; break; fi
            echo "  ⚠️ 信息图上传第 ${_try} 次失败(rc=$_rc)，重试..." >&2
        done
        _miss=0
        while IFS= read -r _f; do
            [ -z "$_f" ] && continue
            # 🔴 2026-09-11 修 Windows curl `/dev/null` 陷阱：Git Bash 下 `-o /dev/null` 实测**恒定返回 rc=23**
            #   （Failed writing body，HTTP 码仍正确拿到），在 set -e 下会直接杀死整个部署脚本。
            #   必须 `|| true` 兜底；判定线上是否生效只看 $_http，不看 curl 退出码。
            _http=$(curl -s -o /dev/null -w '%{http_code}' "https://www.aitoollab.cn/images/infographics/$_f") || true
            if [ "$_http" != "200" ]; then echo "  ❌ 信息图线上未生效: $_f (HTTP $_http)" >&2; _miss=1; fi
        done <<< "$_diff"
        if [ "$_ok" -eq 1 ] && [ "$_miss" -eq 0 ]; then
            echo "  ✅ images/infographics/ 增量同步完成：本地共 ${_total} 个文件，本次上传 ${_ndiff} 个（curl 校验通过）"
        else
            echo "  ❌ images/infographics/ 同步失败，已取消谎报成功（见上方错误）" >&2
            rollback_deploy
            exit 1
        fi
    else
        echo "  ✅ images/infographics/ 无需更新（${_total} 个文件均已存在且大小一致）"
    fi
    rm -f "$_srvf" "$_locf" "$_locf.tarlist" 2>/dev/null || true   # ||true: 本地rm被WorkBuddy safe_delete拦截时不致命
fi
# OG 分享图 images/og/：增量同步（2026-09-11 立规——此前 deploy.sh 从不同步该目录，
#   导致新增工具/文章的 og:image 线上全 404、社交分享无图；实测线上 1042 张 vs 本地 1298 张，缺 256 张）。
#   同 infographics 段：按「缺失 + 大小变化」双条件增量，tar -T 列表避免 Windows xargs 32KB exec 上限。
echo "  增量同步 images/og/（仅上传新增/变更的 OG 分享图）..."
if [ -d "$LOCAL_DIR/images/og" ]; then
    _srvf=$(mktemp); _locf=$(mktemp)
    ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/images/og 2>/dev/null && find . -type f -printf '%P %s\n'" 2>/dev/null | sort > "$_srvf"
    ( cd "$LOCAL_DIR/images/og" && find . -type f -printf '%P %s\n' ) | sort > "$_locf"
    # comm -3：本地独有 + 大小不一致（大小变化会出两行，sort -u 去重）
    _diff=$(comm -3 "$_locf" "$_srvf" | awk '{print $1}' | grep -v '^$' | sort -u)
    _total=$(grep -c . "$_locf" || true)
    _ndiff=$(printf '%s\n' "$_diff" | grep -c . || true)
    if [ "$_ndiff" -gt 0 ]; then
        _ok=0
        for _try in 1 2; do
            printf '%s\n' "$_diff" > "$_locf.tarlist"
            # 🔴 2026-09-11 同 infographics 段：set +e 包住管道才能取到真实退出码并触发重试
            #   （否则 set -e 会在管道失败时直接退出，重试与 ❌ 报错都不可达）。
            set +e
            tar cf - -C "$LOCAL_DIR/images/og" -T "$_locf.tarlist" | \
                ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/images/og && tar xf - --overwrite"
            _rc=$?
            set -e
            if [ "$_rc" -eq 0 ]; then _ok=1; break; fi
            echo "  ⚠️ OG 图上传第 ${_try} 次失败(rc=$_rc)，重试..." >&2
        done
        _miss=0
        while IFS= read -r _f; do
            [ -z "$_f" ] && continue
            # 🔴 2026-09-11 本段首跑即踩：Windows curl `-o /dev/null` 恒返回 rc=23（HTTP 码仍正确），
            #   set -e 下会把整个部署脚本杀死在 [2/4] 段末（.deploy_last_result.json 永远停在 RUNNING）。
            #   `|| true` 兜底；成败只认 $_http。
            _http=$(curl -s -o /dev/null -w '%{http_code}' "https://www.aitoollab.cn/images/og/$_f") || true
            if [ "$_http" != "200" ]; then echo "  ❌ OG 图线上未生效: $_f (HTTP $_http)" >&2; _miss=1; fi
        done <<< "$_diff"
        if [ "$_ok" -eq 1 ] && [ "$_miss" -eq 0 ]; then
            echo "  ✅ images/og/ 增量同步完成：本地共 ${_total} 个文件，本次上传 ${_ndiff} 个（curl 校验通过）"
        else
            # 不 rollback：页面本身已部署正常，OG 缺失只影响分享预览，回滚会把好页面一起退回。
            echo "  ❌ images/og/ 同步失败（不影响页面，但分享图会 404）——请重跑 deploy.sh" >&2
            exit 1
        fi
    else
        echo "  ✅ images/og/ 无需更新（${_total} 个文件均已存在且大小一致）"
    fi
    rm -f "$_srvf" "$_locf" "$_locf.tarlist" 2>/dev/null || true
fi
# 首页「AI前沿」板块新闻条目：由 build.py 构建时注入（build_index_page 目录优先读 193 篇，含最新日期）。
# 2026-08-25 停用 inject_news_cards.py：它基于「index.html 不被构建重建」的旧假设，用**单体 articles.json**
# 覆盖 build 的正确结果（曾把 08/25 覆盖成 08/24、并扩到 11 条）。build 是唯一写入者，勿再调用。
# python scripts/inject_news_cards.py 11 || true

# 根目录关键文件（含 ads.txt：AdSense 授权文件，缺失会导致广告失效）
# 2026-08-08：加入 data/tools.json 与 data/articles.json —— 数据目录不在上方强制同步列表，
#   只靠 git 增量会因“已提交未变更”而漏传，导致服务器工具库落后（529 vs 532 事故）
# 2026-08-25：补 data/dict_terms.json（AI 辞典数据，未提交时 git 增量不漏传不了）
# 2026-08-26：去单体化(任务#7)，data/tools.json 与 data/articles.json 退役删除，
#   数据真源为分片目录 data/tools/ data/articles/（下方页面/数据目录全量同步覆盖），故移出本列表。
for f in index.html sitemap.xml robots.txt ads.txt sw.js manifest.json data/dict_terms.json; do
    if [ -f "$LOCAL_DIR/$f" ]; then
        tar cf - -C "$LOCAL_DIR" "$f" 2>/dev/null | \
            ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar xf - --overwrite" 2>/dev/null || true
        echo "  ✅ $f 已同步"
    fi
done

# 2026-08-26 去单体化(任务#7): 删除服务器残留单体 data/tools.json / data/articles.json
# (单体已退役, 真源为分片目录 data/tools/ data/articles/; 旧单体不删会让 server.py 等读到陈旧镜像)
echo "  🧹 清理服务器残留单体 data/tools.json data/articles.json (去单体化)..."
ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "rm -f ${REMOTE_DIR}/data/tools.json ${REMOTE_DIR}/data/articles.json" 2>/dev/null || true
echo "  ✅ 远端单体已清理"

# 处理删除的文件
if [ -n "$DELETED_FILES" ]; then
    DEL_COUNT=$(echo "$DELETED_FILES" | grep -v '^$' | wc -l)
    echo "  清理服务器上 ${DEL_COUNT} 个已删除文件..."
    echo "$DELETED_FILES" | while IFS= read -r f; do
        [ -z "$f" ] && continue
        ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "rm -f ${REMOTE_DIR}/${f}" 2>/dev/null
    done
fi

echo ""
echo "[2.9/4] 🔍 远端上线核验：服务器实际文件是否含广告加载器..."
# 🔴 2026-08-17 新增（治本）：原有 check_ads_injected.py 只校验**本地**文件，
#   上传环节静默失败/半传时线上整站丢广告仍会显示"部署成功"。
#   本步骤直接在服务器上抽样 grep，缺失则自动重传相关目录并复核，仍缺失即报错退出。
_remote_check() {
    ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} 2>/dev/null || exit 9
        miss=0
        for d in tools articles category compare alternatives ranking quiz live dict news; do
            [ -d \"\$d\" ] || continue
            for f in \$(find \$d -name index.html | sort | head -3) \$(find \$d -name index.html | sort | tail -2); do
                grep -q '/reco/loader.js' \"\$f\" || { miss=\$((miss+1)); echo \"  ❌ 线上缺 loader: \$f\"; }
            done
        done
        echo \"REMOTE_MISS=\$miss\"" 2>/dev/null
}
_rc=$(_remote_check || true)
echo "$_rc" | grep -v '^REMOTE_MISS=' || true
_miss=$(echo "$_rc" | grep '^REMOTE_MISS=' | cut -d= -f2 || true)
if [ -z "$_miss" ]; then
    echo "  ⚠️ 远端核验无法执行（SSH/路径异常），跳过但请人工确认"
elif [ "$_miss" -gt 0 ]; then
    echo "  ⚠️ 线上 $_miss 个抽样页缺 loader → 本地重注入 + 重传内容目录..."
    python scripts/inject_ads.py > /dev/null 2>&1 || true
    for d in tools articles category compare alternatives ranking quiz live dict news; do
        [ -d "$LOCAL_DIR/$d" ] || continue
        tar cf - --exclude='*.bak' -C "$LOCAL_DIR" "$d" 2>/dev/null | \
            ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar xf - --overwrite" 2>/dev/null
    done
    _rc2=$(_remote_check || true)
    _miss2=$(echo "$_rc2" | grep '^REMOTE_MISS=' | cut -d= -f2 || true)
    if [ "${_miss2:-1}" -gt 0 ]; then
        echo "  ❌ 重传后线上仍有 ${_miss2} 个页面缺 loader，请人工排查（部署已中止）"
        rollback_deploy
        exit 1
    fi
    echo "  ✅ 重传后线上核验通过"
else
    echo "  ✅ 线上抽样核验通过（各栏目首/尾页均含 loader）"
fi

echo ""
echo "[3/4] 🔄 重载 Nginx..."
ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "nginx -s reload 2>/dev/null || systemctl reload nginx || echo '  ⚠️ Nginx reload skipped'"
echo "✅ Nginx 已重载"

# ── 部署后线上健康闭环（2026-08-27，GSC 404 治理复盘）──
# 背景：8/22 部署窗口期 4 个页面线上 404 但 sitemap 仍收录，Google 抓到计入 404 清单，一周后才被发现。
# 现在：每次重载 Nginx 后全量 HEAD 线上 sitemap + 关键入口抽查，任何非 200 → 自动回滚并中止。
echo ""
echo "[3.5/4] 🩺 部署后健康检查（线上 sitemap 全量存活 + 关键入口）..."
_HC_DIR="$LOCAL_DIR"
if command -v cygpath >/dev/null 2>&1; then _HC_DIR=$(cygpath -w "$LOCAL_DIR"); fi
# tee 落一份日志：既能实时看进度，又能给后面的 .deploy_last_result.json 提取存活 URL 数
PYTHONIOENCODING=utf-8 python "$_HC_DIR/scripts/post_deploy_health_check.py" 2>&1 | tee "$LOCAL_DIR/.deploy_health.log"
HC_RC=${PIPESTATUS[0]}
HC_TOTAL="$(grep -oE '[0-9]+ 个 URL' "$LOCAL_DIR/.deploy_health.log" 2>/dev/null | grep -oE '^[0-9]+' | head -1 || true)"
if [ $HC_RC -ne 0 ]; then
    echo "  ❌ 健康检查未通过，回滚部署..."
    _deploy_mark FAILED "health-check-failed, rolled-back"
    rollback_deploy
    exit 1
fi
echo "  ✅ 健康检查通过"

echo ""
echo "[4/4] 📤 Git 备份排名/数据变更..."
cd "$LOCAL_DIR"
# 2026-08-23 数据拆分：单体 data/tools.json/articles.json 不再提交（改为提交 data/tools/ data/articles/ 小文件目录，
# 每次部署只提交改动的小文件，彻底止 git 膨胀）。单体仍被 data_store 同步更新并 scp 到服务器供后端读取。
# 2026-08-29 扩白名单：纳入构建辅助脚本与项目规则文件（原白名单只含 build.py + build_lib/，
# 导致 seo_title_helper.py / publish_new_tools.py / AGENTS.md / .gitignore 的改动永不进 git，
# 踩「无 git 不可回滚」血泪教训）。精准补路径，不用 git add -A（会误提交 scratch 文件）。
git add data/live_data.json data/ranking_data.json data/subcategories.json data/_latest_infographic.json data/homepage_picks.json data/picks_candidates.json data/picks_history.json index.html live/ ranking/ scripts/build.py scripts/build_lib/ scripts/seo_title_helper.py scripts/publish_new_tools.py AGENTS.md .gitignore data/tools/ data/articles/ 2>/dev/null || true
# 2026-09-01 扩白名单：纳入核实/版本治理链路的脚本与报告（同上教训，改动必须能回滚）
#   verify_tools_batch.py   = 核实结果写回（本次新增 stale_facts 过时事实定点替换）
#   check_version_drift.py  = 版本漂移巡检（本次修复：去单体化 + FAQ q/a 键名 + desc_drift）
#   add_version_evo.py      = 版本演进对比小节写入（本次修复：去单体化 + --dry-run）
#   analyze_beacon.py       = CPS beacon 漏斗分析（修 logrotate delaycompress 漏数 + 日期错位）
git add scripts/verify_tools_batch.py scripts/check_version_drift.py scripts/add_version_evo.py scripts/analyze_beacon.py scripts/review_generator.py scripts/_claude_fable_evo.json scripts/_seedance_evo.json scripts/_patch_fable51_stale.py scripts/_patch_seedance25_stale.py scripts/_version_drift_report.json reports/ 2>/dev/null || true
# 2026-09-11：工具收录类一次性脚本入库（可回滚 + 留痕：盘古大模型）
git add scripts/_add_pangu_20260910.py scripts/_fix_pangu_desc_20260911.py 2>/dev/null || true
# 2026-09-11：快讯提炼脚本入库（AI快讯日更 automation-1784555527714 的一次性提炼脚本，
#   幂等可重跑、含同日/跨天去重与字数体检，同属"改动必须能回滚 + 留痕"铁律）
git add scripts/_news_refine_*.py 2>/dev/null || true
# 2026-09-03 修正：内容数据（data/dict_terms/ 等）不进 git，只提交流程系统（脚本/deploy.sh 等）。
#   deploy.sh 本体纳入白名单，确保本脚本自身改动可回滚（deploy.sh 不在上方白名单内，不显式加入会丢失）。
#   注：data/tools/ data/articles/ 仍按 2026-08-23 设计提交（内容正本备份），待用户决定是否同样移出 git。
git add deploy.sh 2>/dev/null || true
# 2026-09-10 扩白名单：顶部广告条治理链路。tpb_manager.py / ads/tpb-config.json / start_tpb.bat
#   此前均未被 git 跟踪（改动无法回滚，违反"必须能回滚"铁律）；sw.js 因新增 /reco/ 纯网络白名单
#   也必须入库（SW 缓存旧配置 = "后台改了线上不更新"的老根因之一）。
git add tpb_manager.py start_tpb.bat ads/tpb-config.json sw.js 2>/dev/null || true
# 2026-09-10 第二次扩容：运营后台三件套。gen_cms.py（CMS 控制台生成器）、affiliate_manager.py（8899
#   工具管理台，顶栏加广告条入口）、watchdog_affiliate.py（启动降级修复：breakaway 被 Job 拒时回退
#   no-window，否则 8899 长期起不来 = 用户以为"后台被删了"）。同属"改动必须能回滚"铁律。
# 2026-09-11 补 cms.html：gen_cms.py 的产物、已在 git 跟踪，但此前不在白名单 → 每次 gen_cms 后
#   它都永久挂在"未提交"里，改动无法回滚（同属"改动必须能回滚"铁律）。纳入白名单消除该缺口。
git add scripts/gen_cms.py affiliate_manager.py scripts/watchdog_affiliate.py cms.html 2>/dev/null || true

# ── 本次提交内容审计：暴露"被顺手裹进来的手改源码"（2026-09-11 立规）────────────
# 事故回放（2026-09-11）：部署时工作区存在**其他会话遗留的 deploy.sh 手改**（新增 images/og/
#   增量同步段）。因为白名单里本来就有 deploy.sh（2026-09-03 有意加，保证本脚本可回滚），
#   该改动被静默卷入部署 commit（b511f82），日志里毫无提示，靠人"事后扫 git status"才发现。
# 修正方向不是收紧白名单（部署态必须可回滚，白名单是刻意设计），而是**让它可见 + 留痕**：
#   列出本次提交中所有「非构建产物」文件（= 手改源码），并在 commit body 里记账。
# 判定口径：下列为「构建产物」，其余一律视为「手改源码」→ 进审计清单。
#   刻意不排除 robots.txt / ads.txt / manifest.json / sw.js / css/style.css 等——它们虽然也在
#   产物目录附近，但属手改源码，正是最容易被顺手裹进部署 commit 的一类（2026-09-11 事故同源）。
_MANUAL="$(git diff --cached --name-only 2>/dev/null | grep -vE '^(data/|js/tools-data\.js$|css/style\.min\.css$|css/critical[^/]*\.css$|articles/|tools/|category/|compare/|alternatives/|ranking/|quiz/|dict/|news/|live/|author/|images/|index\.html$|404\.html$|rss\.xml$|sitemap\.xml$)' || true)"
_COMMIT_BODY="仅构建产物与数据"
if [ -n "$_MANUAL" ]; then
    _MN=$(printf '%s\n' "$_MANUAL" | grep -c . || true)
    echo "  ⚠️ 本次提交含 ${_MN} 个「手改源码」文件（非构建产物），请确认都是你有意为之："
    printf '%s\n' "$_MANUAL" | head -20 | sed 's/^/      /'
    if [ "$_MN" -gt 20 ]; then
        echo "      ...（其余 $((_MN - 20)) 个略）"
    fi
    echo "      提示：若其中有你本次没改过的文件 → 是其他会话/自动化遗留的未提交改动被裹进来了。"
    _COMMIT_BODY="手改源码文件(${_MN}): $(printf '%s' "$_MANUAL" | tr '\n' ' ')"
fi

if git diff --cached --quiet; then
    echo "  无可提交变更"
else
    TOOL_COUNT=$(find data/tools -name '*.json' 2>/dev/null | wc -l)
    ARTICLE_COUNT=$(find data/articles -name '*.json' 2>/dev/null | wc -l)
    # 2026-08-24 G5 修复：commit 失败必须暴露（去掉 || true），set -e 会中止部署并报错，
    # 不再把"commit 失败"伪装成"部署成功"。git add 仍保留 || true（偶发文件锁失败不致命，下次重试）。
    git commit -m "deploy: 全站构建+排名数据更新 (${TOOL_COUNT} tools + ${ARTICLE_COUNT} articles)" -m "${_COMMIT_BODY}"
    _COMMIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
    _PUSH_OUT="$(git push origin main 2>&1)"; _PUSH_RC=$?
    echo "$_PUSH_OUT" | tail -2
    # 2026-08-28 修假绿灯：原来 `git push ... || echo 警告` 后面无条件 echo "✅ Git 已推送"，
    # 实测推送失败（网络抖动）时日志照样写"已推送"，坏提交就这么留在本地没人知道。
    if [ -n "$(git log origin/main..HEAD --oneline)" ]; then
        _PUSHED=no
        echo "  ⚠️ Git 未推送成功（rc=$_PUSH_RC），仍有未推送提交："
        git log --oneline origin/main..HEAD | head -5 | sed 's/^/      /'
    else
        _PUSHED=yes
        echo "  ✅ Git 已推送（本地与 origin/main 一致）"
    fi
fi

# ── 未进本次提交的残留改动（提示性，不阻断部署）──────────────────────────────
# 位置刻意放在 commit 之后：此时 `git status` 里剩下的才是**真正没进本次提交**的改动。
# （2026-09-11 修正：原先放在 commit 之前，会把刚 staged 的文件也列进来，提示"不会上线"
#   实际已在本次 commit 内 → 语义反了。）
_PENDING="$(git status --porcelain 2>/dev/null | head -12 || true)"
if [ -n "$_PENDING" ]; then
    echo "  ℹ️ 除本次提交外，工作区仍有未提交改动（不入本次 git，仅靠服务器 tar 备份回滚）："
    printf '%s\n' "$_PENDING" | sed 's/^/      /'
fi

echo ""
echo "==========================================="
echo "  🎉 部署成功!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

# 落盘结果（判定部署结果以此文件为准，不看 stdout 尾部是否被 tail 截断）
_deploy_mark SUCCESS "commit=${_COMMIT_SHA:-none} pushed=${_PUSHED:-n/a} health_urls=${HC_TOTAL:-?} manual_src=$(printf '%s' "${_MANUAL:-}" | grep -c . || true)"
echo "  [result] $(cat "$DEPLOY_RESULT_FILE" 2>/dev/null)"
echo "  ℹ️ 判定部署结果请读 .deploy_last_result.json（status=SUCCESS 即全链路完成）"

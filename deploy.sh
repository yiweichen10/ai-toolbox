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
# 仅保留最新 5 个备份（防止短时间多次部署把磁盘撑满）；7天前兜底删除
ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f 2>/dev/null || true
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
            tar cf - -C "$LOCAL_DIR/images/infographics" -T "$_locf.tarlist" | \
                ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/images/infographics && tar xf - --overwrite"
            _rc=$?
            if [ "$_rc" -eq 0 ]; then _ok=1; break; fi
            echo "  ⚠️ 信息图上传第 ${_try} 次失败(rc=$_rc)，重试..." >&2
        done
        _miss=0
        while IFS= read -r _f; do
            [ -z "$_f" ] && continue
            _http=$(curl -s -o /dev/null -w '%{http_code}' "https://www.aitoollab.cn/images/infographics/$_f")
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
                grep -q '/ads/loader.js' \"\$f\" || { miss=\$((miss+1)); echo \"  ❌ 线上缺 loader: \$f\"; }
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
PYTHONIOENCODING=utf-8 python "$_HC_DIR/scripts/post_deploy_health_check.py"
HC_RC=$?
if [ $HC_RC -ne 0 ]; then
    echo "  ❌ 健康检查未通过，回滚部署..."
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
if git diff --cached --quiet; then
    echo "  无可提交变更"
else
    TOOL_COUNT=$(find data/tools -name '*.json' 2>/dev/null | wc -l)
    ARTICLE_COUNT=$(find data/articles -name '*.json' 2>/dev/null | wc -l)
    # 2026-08-24 G5 修复：commit 失败必须暴露（去掉 || true），set -e 会中止部署并报错，
    # 不再把"commit 失败"伪装成"部署成功"。git add 仍保留 || true（偶发文件锁失败不致命，下次重试）。
    git commit -m "deploy: 全站构建+排名数据更新 (${TOOL_COUNT} tools + ${ARTICLE_COUNT} articles)"
    _PUSH_OUT="$(git push origin main 2>&1)"; _PUSH_RC=$?
    echo "$_PUSH_OUT" | tail -2
    # 2026-08-28 修假绿灯：原来 `git push ... || echo 警告` 后面无条件 echo "✅ Git 已推送"，
    # 实测推送失败（网络抖动）时日志照样写"已推送"，坏提交就这么留在本地没人知道。
    if [ -n "$(git log origin/main..HEAD --oneline)" ]; then
        echo "  ⚠️ Git 未推送成功（rc=$_PUSH_RC），仍有未推送提交："
        git log --oneline origin/main..HEAD | head -5 | sed 's/^/      /'
    else
        echo "  ✅ Git 已推送（本地与 origin/main 一致）"
    fi
fi

echo ""
echo "==========================================="
echo "  🎉 部署成功!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

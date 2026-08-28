#!/usr/bin/env bash
# ============================================================
# deploy_fast.sh — 单篇文章增量发布通道（2026-08-28 新增）
#
# 用法:
#   bash deploy_fast.sh <article-slug>            # 构建+门禁+上传+线上验收+git
#   bash deploy_fast.sh <article-slug> --dry-run  # 只构建+门禁+列出待传文件，不上传不提交
#
# 适用边界（不满足就必须回 bash deploy.sh 全量）:
#   OK   只新增/修改 data/articles/<slug>.json 一篇文章
#   NO   改模板 / build_lib / CSS / js  -> 全站页面都要重出，必须全量
#   NO   改 data/tools/*.json、dict_terms/、news_*.json、compare/ranking -> 必须全量
#   NO   删页 / 改 slug -> 必须全量并在 nginx-old-url-redirects.conf 补 301
#
# 为什么敢增量：build.py -s 现在会重建「新文章页 + 日期邻居页 + related_tools 工具页 +
#   首页 + 文章列表/分类页 + 全量 sitemap + 与全量同一份全站后处理注入链」。
#   2026-08-28 实测：增量产物与全量产物逐字节一致（唯一差异是 index.html 的 ?v= 缓存戳），
#   sitemap 1141 条 == 全量 1141 条（修复前增量只有 1000 条，会掉 137 条）。
#
# 与 deploy.sh 的差异（省时间）: 不跑 regenerate_data / optimize_css / 今日推荐候选池，
#   不渲染 1100+ 页面，上传改为"本次实际变更文件"的 tar 精准同步，
#   健康检查只查受影响 URL（全量版会 HEAD 整张 sitemap）。
# ============================================================
set -eo pipefail   # 2026-08-28：管道里 build 失败必须被看见（见下方断言）
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

SLUG="${1:-}"
DRY_RUN=false
if [ "${2:-}" = "--dry-run" ]; then DRY_RUN=true; fi
if [ -z "$SLUG" ]; then
    echo "用法: bash deploy_fast.sh <article-slug> [--dry-run]"; exit 2
fi

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
SERVER_IP="121.43.144.99"
SERVER_USER="root"
REMOTE_DIR="/var/www/aitoollab/html"
SITE="https://www.aitoollab.cn"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LOCAL_DIR"

if [ ! -f "data/articles/${SLUG}.json" ]; then
    echo "❌ 找不到 data/articles/${SLUG}.json —— 分片才是真源（AGENTS.md 2026-08-25 数据架构）"
    exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
TS="$(date +%Y%m%d-%H%M%S)"

echo "==========================================="
echo "  增量发布（单篇文章）: ${SLUG}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')  DRY_RUN=${DRY_RUN}"
echo "==========================================="

echo ""
echo "[f1/5] 📦 增量构建 build.py -s ${SLUG}"
# 构建前快照 git 状态，构建后用差集精确算出"这次真正改了什么"
git status --porcelain -uall | sort > "$WORK/before"
_BUILD_FLAG=""
if [ "$DRY_RUN" = true ]; then _BUILD_FLAG="--no-push"; fi  # 演练不重复推送
python scripts/build.py -s "$SLUG" $_BUILD_FLAG | tee "$WORK/build.log"

# 断言构建真的收尾了：以前只 set -e，管道里 build 崩了 tee 仍返回 0，
# 结果"门禁全过 + 待上传只剩强制项"的假成功差点把半成品传上线（2026-08-28 实测踩到）。
if ! grep -q '\[完成\] 增量构建' "$WORK/build.log"; then
    echo "❌ 增量构建未正常收尾（日志缺 [完成] 标记），中止发布。日志尾部："
    tail -15 "$WORK/build.log"
    exit 1
fi
if [ ! -s "articles/${SLUG}/index.html" ] || [ "$(wc -c < "articles/${SLUG}/index.html")" -lt 5000 ]; then
    echo "❌ 产物异常：articles/${SLUG}/index.html 缺失或过小，中止发布"
    exit 1
fi

echo ""
echo "[f2/5] 🚪 门禁（与全量部署同一批，任一失败即中止，不绕过）"
python scripts/check_sitemap_artifacts.py "$LOCAL_DIR"
python scripts/check_ads_injected.py
python scripts/check_dark_mode.py
python scripts/check_tts_skip.py
python scripts/check_mono_retired.py || { echo "❌ 单体守卫未通过，中止发布"; exit 1; }
python scripts/check_closed_loop.py
echo "✅ 门禁全部通过"

echo ""
echo "[f3/5] 🧾 采集待上传文件"
git status --porcelain -uall | sort > "$WORK/after"
: > "$WORK/list"
# (a) 本次构建造成的 git 可见变更（含新增未跟踪文件）
comm -13 "$WORK/before" "$WORK/after" \
    | sed -E 's/^.{1,4}//; s/^"//; s/"$//' >> "$WORK/list"
# (b) 构建自己声明写出的页面（[OK] xxx/index.html）
grep -oE '^\[OK\] [^ ]+' "$WORK/build.log" | sed 's/^\[OK\] //' >> "$WORK/list" || true
# (c) 关键枢纽页强制纳入：首页/sitemap/rss/搜索索引 + 本文分片
#     （防"该文件构建前就是脏的"导致差集漏掉，首页漏了就等于文章没入口）
printf '%s\n' index.html sitemap.xml rss.xml js/tools-data.js "data/articles/${SLUG}.json" >> "$WORK/list"
# (d) 文章配图与 OG 图：images/ 被 gitignore，git 采不到，必须显式加
for f in images/articles/"$SLUG"/*.png images/og/"$SLUG"-og.png; do
    [ -f "$f" ] && echo "$f" >> "$WORK/list"
done
# 去重 + 只保留真实存在的文件
sort -u "$WORK/list" | while IFS= read -r f; do
    f="$(printf '%s' "$f" | tr -d '\r')"
    # 注意：必须用 if 而不是 "A && B && C"，否则末次迭代测试失败会让 while 整体返回非 0，
    # 在 set -e 下直接把部署脚本打断（2026-08-28 首跑就栽在这）。
    if [ -n "$f" ] && [ -f "$f" ]; then printf '%s\n' "$f"; fi
done > "$WORK/upload"
N="$(wc -l < "$WORK/upload" | tr -d ' ')"
echo "  待上传 ${N} 个文件:"
sed 's/^/    /' "$WORK/upload" | head -40
if [ "$N" -gt 40 ]; then echo "    ...（共 ${N} 个）"; fi
if [ "$DRY_RUN" = true ]; then
    echo ""; echo "--dry-run：到此为止，不上传、不提交。"; exit 0
fi

echo ""
echo "[f4/5] 🔄 备份远端将被覆盖的文件 + tar 精准上传"
# 远端备份（只备本次要覆盖的那批，回滚一条命令）
tar -tzf /dev/null 2>/dev/null || true
ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" \
    "cd ${REMOTE_DIR} && tar czf /var/www/aitoollab/backups/fast_${TS}.tar.gz -T - --ignore-failed-read 2>/dev/null || true" \
    < <(sed 's#^#./#' "$WORK/upload") || echo "  ⚠️ 远端备份跳过（不影响上传）"
# 注意：Windows 环境变量块远超 CreateProcess 32KB 上限，禁用 xargs 传列表（AGENTS.md 铁律），
# 一律用 tar -T 列表文件，由 tar 内部读取。
_upload_ok=true
for _try in 1 2; do
    if tar cf - -C "$LOCAL_DIR" -T "$WORK/upload" 2>/dev/null \
        | ssh $SSH_OPTS "${SERVER_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && tar xf - --overwrite"; then
        break
    fi
    _upload_ok=false; echo "  ⚠️ 第 ${_try} 次上传失败，重试..."; sleep 2
done
if [ "$_upload_ok" = false ]; then
    echo "  ❌ 上传两次均失败，中止（线上未变更）"; exit 1
fi
echo "  ✅ 已上传 ${N} 个文件"

echo ""
echo "[f5/5] 🩺 线上验收（真实用户路径 + 逐文件字节校验）"
python - "$SITE" "$SLUG" "$WORK/upload" "$SSH_KEY" "$SERVER_IP" << 'PYCHK'
import hashlib, os, subprocess, sys, urllib.request

site, slug, listfile, ssh_key, server_ip = sys.argv[1:6]
paths = [l.strip() for l in open(listfile, encoding="utf-8") if l.strip()]
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"}

def head(u, want=200):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H, method="GET"), timeout=40)
        return r.status, r.read()
    except Exception as e:
        return getattr(e, "code", 0), b""

fail = []
# 1) 关键 URL 存活
for u in [f"{site}/articles/{slug}/", f"{site}/", f"{site}/sitemap.xml", f"{site}/rss.xml"]:
    st, body = head(u)
    print(f"  {'OK ' if st == 200 else 'FAIL'} {st} {u} ({len(body)} B)")
    if st != 200:
        fail.append(u)
# 2) 首页必须能点到新文章（真实入口，不是"文件存在"）
st, home = head(f"{site}/")
if slug.encode() not in home:
    print("  FAIL 首页未包含新文章链接"); fail.append("homepage-link")
else:
    print("  OK  首页包含新文章链接")
# 3) 文章页标题与结构化数据
st, art = head(f"{site}/articles/{slug}/")
txt = art.decode("utf-8", "ignore")
for token in ["Article", "FAQPage", "BreadcrumbList", "canonical", "/ads/loader.js"]:
    ok = token in txt
    print(f"  {'OK ' if ok else 'FAIL'} 文章页含 {token}")
    if not ok:
        fail.append(token)
# 4) 逐文件字节校验：本地 sha1 == 远端 sha1
remote = {}
# 逐批把路径塞进远端命令（不要用 stdin + while read：Windows OpenSSH 客户端下
# stdin 传不进远程循环，2026-08-28 首跑就是被这个假失败坑了）
for i in range(0, len(paths), 40):
    chunk = paths[i:i + 40]
    joined = " ".join("'" + c.replace("'", "'\\''") + "'" for c in chunk)
    cmd = ["ssh", "-i", ssh_key, "-o", "StrictHostKeyChecking=no", f"root@{server_ip}",
           f"cd /var/www/aitoollab/html && sha1sum {joined} 2>/dev/null"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (p.stdout or "").splitlines():
        if len(line) > 42 and line[40:42] == "  ":
            remote[line[42:].strip()] = line[:40]
bad = []
for f in paths:
    local = hashlib.sha1(open(f, "rb").read()).hexdigest()
    if remote.get(f.replace(os.sep, "/")) != local:
        bad.append(f)
print(f"  {'OK ' if not bad else 'FAIL'} 远端字节校验 {len(paths) - len(bad)}/{len(paths)} 一致")
for f in bad[:10]:
    print("     MISMATCH", f)
fail += bad

if fail:
    print("\n❌ 线上验收未通过:", fail[:8])
    print(f"   回滚命令: ssh -i {ssh_key} root@{server_ip} \"cd /var/www/aitoollab/html && tar xzf /var/www/aitoollab/backups/<fast_备份>.tar.gz\"")
    sys.exit(1)
print("  ✅ 线上验收全部通过")
PYCHK

echo ""
echo "[f6/6] 📤 Git 备份（只提交本次相关文件）"
# 只提交本次真正上传的那批文件 + 文章分片（不用 git add 整目录：
# 那会把别的自动化未完成的改动一起打包上线，责任边界要清楚）
if git add --pathspec-from-file="$WORK/upload" 2>/dev/null; then
    :
else
    # 老版本 git 兜底（本仓库路径无空格）
    # shellcheck disable=SC2046
    git add $(cat "$WORK/upload") 2>/dev/null || true
fi
git add "data/articles/${SLUG}.json" 2>/dev/null || true
if git diff --cached --quiet; then
    echo "  无可提交变更"
else
    git commit -m "deploy(fast): 增量发布文章 ${SLUG}（build -s + 门禁 + 定向上传）"
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
echo "  🎉 增量发布完成!  ${SITE}/articles/${SLUG}/"
echo "==========================================="

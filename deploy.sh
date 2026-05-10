#!/bin/bash
# ============================================================
# deploy.sh - 中文站一键部署到阿里云（增量+Git备份）
# 用法:
#   bash deploy.sh            # 增量部署（日常使用）
#   bash deploy.sh --publish  # 发布新工具 + 构建 + 部署 + Git备份
#   bash deploy.sh --full     # 全量部署（大改后使用）
# ============================================================
set -e

# ====== 配置区 ======
SERVER="aitoollab"
REMOTE_DIR="/var/www/aitoollab/html"
LOCAL_DIR="C:/Users/27040/WorkBuddy/20260321092139/seo-site"
REPO_REMOTE="origin"
REPO_BRANCH="main"
# ===================

MODE="incremental"
if [[ "$1" == "--full" ]]; then
    MODE="full"
elif [[ "$1" == "--publish" ]]; then
    MODE="publish"
fi

cd "$LOCAL_DIR"

# ====== Step 0: 发布新工具（仅 --publish 模式） ======
if [[ "$MODE" == "publish" ]]; then
    echo "[0/4] 发布新工具..."
    python scripts/publish_new_tools.py
    echo "✅ 新工具发布完成"
fi

# ====== Step 1: 构建全站 ======
echo "[1/4] 构建静态站..."
python scripts/build.py
if [ $? -ne 0 ]; then
    echo "❌ 构建失败！"
    exit 1
fi
echo "✅ 构建完成"

# ====== Step 2: 部署到服务器 ======
echo "[2/4] 部署到阿里云..."

if [[ "$MODE" == "full" ]]; then
    # --- 全量部署 ---
    echo "  模式: 全量部署"
    tar -czf /tmp/aitoollab-deploy.tar.gz \
        --exclude='.env' --exclude='.git' --exclude='*.bak' \
        --exclude='data' --exclude='scripts' --exclude='images' \
        --exclude='_archive' --exclude='backup' --exclude='__pycache__' \
        --exclude='*.md' \
        tools articles category compare alternatives quiz ranking live \
        index.html sitemap.xml 404.html css/ js/ images/og/
    echo "  打包完成: $(du -h /tmp/aitoollab-deploy.tar.gz | cut -f1)"

    scp /tmp/aitoollab-deploy.tar.gz ${SERVER}:/tmp/

    ssh ${SERVER} bash -s << 'DEPLOY_SCRIPT'
set -e
TARGET="/var/www/aitoollab/html"
BACKUP_DIR="/var/www/aitoollab/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
if [ -d "$TARGET" ] && [ "$(ls -A $TARGET 2>/dev/null)" ]; then
    tar -czf "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz" -C "$TARGET" .
    echo "  备份 → backups/backup_${TIMESTAMP}.tar.gz"
fi
tar -xzf /tmp/aitoollab-deploy.tar.gz -C "$TARGET"
rm -f /tmp/aitoollab-deploy.tar.gz
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
DEPLOY_SCRIPT

    rm -f /tmp/aitoollab-deploy.tar.gz
else
    # --- 增量部署：只传变化的文件 ---
    echo "  模式: 增量部署"

    # 获取需要同步的文件列表（排除非部署文件）
    CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null | grep -v \
        -E '^(\.env|\.git|\.github|scripts/|data/|images/|_archive/|backup/|__pycache__|.*\.bak|.*\.md|vercel\.json)' \
        || true)

    # 也检查未跟踪的新文件
    NEW_FILES=$(git ls-files --others --exclude-standard | grep -v \
        -E '^(\.env|\.git|\.github|scripts/|data/|images/|_archive/|backup/|__pycache__|.*\.bak|.*\.md|vercel\.json)' \
        || true)

    ALL_FILES=$(echo -e "${CHANGED_FILES}\n${NEW_FILES}" | sed '/^$/d' | sort -u)

    if [ -z "$ALL_FILES" ]; then
        echo "  没有文件变化，跳过部署"
    else
        FILE_COUNT=$(echo "$ALL_FILES" | wc -l)
        echo "  变化文件: $FILE_COUNT 个"
        echo "$ALL_FILES" | head -20

        # 用 tar 打包变化的文件，保持目录结构
        echo "$ALL_FILES" | tar -czf /tmp/aitoollab-incremental.tar.gz -T -

        # 上传并解压
        scp /tmp/aitoollab-incremental.tar.gz ${SERVER}:/tmp/
        ssh ${SERVER} "tar -xzf /tmp/aitoollab-incremental.tar.gz -C $REMOTE_DIR && rm -f /tmp/aitoollab-incremental.tar.gz"

        rm -f /tmp/aitoollab-incremental.tar.gz
        echo "  ✅ 增量部署完成"
    fi
fi

# ====== Step 3: Git 备份 ======
echo "[3/4] Git 备份..."
# 添加所有变化（.gitignore 已过滤敏感文件）
git add -A
# 检查是否有需要提交的内容
if git diff --cached --quiet; then
    echo "  没有新的变更需要提交"
else
    DATE=$(date +%Y-%m-%d)
    # 生成提交信息
    if [[ "$MODE" == "publish" ]]; then
        NEW_COUNT=$(git diff --cached --name-only | grep '^tools/' | grep '/index.html$' | wc -l)
        COMMIT_MSG="deploy: ${DATE} +${NEW_COUNT} tools, rebuild & deploy"
    else
        COMMIT_MSG="deploy: ${DATE} rebuild & deploy"
    fi
    git commit -m "$COMMIT_MSG"
    git push ${REPO_REMOTE} ${REPO_BRANCH}
    echo "  ✅ Git 备份完成: $COMMIT_MSG"
fi

# ====== Step 4: 汇总 ======
echo ""
echo "==========================================="
echo "  部署完成!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

#!/bin/bash
# ============================================================
# deploy.sh - aitoollab.cn 中文站一键部署到阿里云
# 用法: bash deploy.sh [--skip-build]
# 服务器: 121.43.144.99 /var/www/aitoollab/html
# SSH Key: ~/.ssh/id_ed25519_aitoollab
# ============================================================
set -e

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
SERVER_IP="121.43.144.99"
SERVER_USER="root"
REMOTE_DIR="/var/www/aitoollab/html"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
TARBALL="/tmp/aitoollab-deploy-$(date +%Y%m%d_%H%M%S).tar.gz"

SKIP_BUILD=false
if [ "$1" = "--skip-build" ]; then
    SKIP_BUILD=true
fi

echo "==========================================="
echo "  aitoollab.cn 部署脚本"
echo "  目标: ${SERVER_IP}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo "[1/4] 📦 构建静态站..."
    cd "$LOCAL_DIR"
    python scripts/build.py
    echo "✅ 构建完成"
else
    echo "[1/4] ⏩ 跳过构建 (--skip-build)"
fi

echo ""
echo "[2/4] 🗜️ 打包静态文件..."
cd "$LOCAL_DIR"
tar -czf "$TARBALL" \
    --exclude='_*' \
    --exclude='*.py' \
    --exclude='*.pyc' \
    --exclude='*.bak' \
    --exclude='*.md' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='*.toml' \
    --exclude='cookies.json' \
    --exclude='__pycache__' \
    --exclude='images' \
    --exclude='ai_tool_covers' \
    --exclude='ai_inner_pages' \
    --exclude='viral_covers' \
    --exclude='xhs-publish-package-*' \
    --exclude='seo-site' \
    --exclude='seo-site-en' \
    --exclude='seo-articles' \
    --exclude='seo-site-backup-*' \
    .
SIZE=$(du -h "$TARBALL" | cut -f1)
echo "✅ 打包完成: ${SIZE}"

echo ""
echo "[3/4] 🚀 上传到服务器..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$TARBALL" "${SERVER_USER}@${SERVER_IP}:/tmp/"
echo "✅ 上传完成"

echo ""
echo "[4/4] 📂 服务器端部署..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SERVER_USER}@${SERVER_IP}" bash -s << DEPLOY_SCRIPT
set -e
TARGET="$REMOTE_DIR"
BACKUP_DIR="/var/www/aitoollab/backups"
TARBALL="$TARBALL"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

echo "  创建备份..."
mkdir -p "\$BACKUP_DIR"
if [ -d "\$TARGET" ] && [ "\$(ls -A \$TARGET 2>/dev/null)" ]; then
    tar -czf "\$BACKUP_DIR/backup_\${TIMESTAMP}.tar.gz" -C "\$TARGET" .
    echo "  ✅ 备份 → backups/backup_\${TIMESTAMP}.tar.gz"
fi

echo "  解压新文件..."
tar -xzf "\$TARBALL" -C "\$TARGET"
rm -f "\$TARBALL"

# 清理超过7天的备份
find "\$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo "  🔄 重载 Nginx..."
nginx -s reload 2>/dev/null || systemctl reload nginx || echo "  ⚠️ Nginx reload skipped"

echo "  ✅ 部署完成!"
DEPLOY_SCRIPT

# 清理本地临时文件
rm -f "$TARBALL"

echo ""
echo "==========================================="
echo "  🎉 部署成功!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

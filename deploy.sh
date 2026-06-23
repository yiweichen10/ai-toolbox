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
    echo "[0/4] 🔄 重新生成排名和仪表盘数据..."
    cd "$LOCAL_DIR"
    python scripts/regenerate_data.py
    echo "✅ 数据生成完成"

    echo ""
    echo "[1/4] 📦 构建静态站..."
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

# 部署 Nginx 安全头配置（首次部署时写入，已存在则跳过）
NGINX_SECURITY_CONF="/etc/nginx/conf.d/security-headers.conf"
if [ ! -f "\$NGINX_SECURITY_CONF" ]; then
    echo "  📝 写入 Nginx 安全头配置..."
    cat > "\$NGINX_SECURITY_CONF" << 'SECURITY_CONF'
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://hm.baidu.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'self'" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
SECURITY_CONF
    echo "  ✅ 安全头配置已写入"
else
    echo "  ℹ️  安全头配置已存在，跳过"
fi

echo "  🔄 重载 Nginx..."
nginx -s reload 2>/dev/null || systemctl reload nginx || echo "  ⚠️ Nginx reload skipped"

echo "  ✅ 部署完成!"
DEPLOY_SCRIPT

echo ""
echo "[5/5] 📤 Git 备份排名/数据变更..."
cd "$LOCAL_DIR"
git add data/live_data.json data/ranking_data.json index.html live/ ranking/ 2>/dev/null
if git diff --cached --quiet; then
    echo "  无可提交变更"
else
    TOOL_COUNT=$(grep -c '"published": true' data/tools.json 2>/dev/null || echo "?")
    ARTICLE_COUNT=$(grep -c '"published": true' data/articles.json 2>/dev/null || echo "?")
    git commit -m "deploy: 全站构建+排名数据更新 (${TOOL_COUNT} tools + ${ARTICLE_COUNT} articles)" || true
    git push origin main 2>&1 || echo "  ⚠️ Git push failed (network may be down)"
    echo "  ✅ Git 已推送"
fi

# 清理本地临时文件
rm -f "$TARBALL"

echo ""
echo "==========================================="
echo "  🎉 部署成功!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

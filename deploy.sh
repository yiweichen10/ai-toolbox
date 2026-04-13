#!/bin/bash
# ============================================================
# deploy.sh - 中文站一键部署到阿里云
# 用法: bash deploy.sh
# ============================================================
set -e  # 出错即停

# ====== 配置区 ======
SERVER_IP="121.43.144.99"
SERVER_USER="root"
REMOTE_DIR="/var/www/aitoollab/html"
LOCAL_DIR="C:/Users/27040/WorkBuddy/20260321092139/seo-site"
# ===================

echo "==========================================="
echo "  aitoollab.cn 部署脚本"
echo "  目标: ${SERVER_IP}"
echo "==========================================="

echo ""
echo "[1/4] 📦 构建静态站..."
cd "$LOCAL_DIR"
python build.py
if [ $? -ne 0 ]; then
    echo "❌ 构建失败！"
    exit 1
fi
echo "✅ 构建完成"

echo ""
echo "[2/4] 🗜️ 打包文件..."
tar -czf /tmp/aitoollab-deploy.tar.gz -C output .
echo "✅ 打包完成: $(du -h /tmp/aitoollab-deploy.tar.gz | cut -f1)"

echo ""
echo "[3/4] 🚀 上传到服务器..."
scp /tmp/aitoollab-deploy.tar.gz ${SERVER_USER}@${SERVER_IP}:/tmp/
echo "✅ 上传完成"

echo ""
echo "[4/4] 📂 服务器端部署..."
ssh ${SERVER_USER}@${SERVER_IP} bash -s << 'DEPLOY_SCRIPT'
set -e
TARGET="/var/www/aitoollab/html"
BACKUP_DIR="/var/www/aitoollab/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "  创建备份..."
mkdir -p "$BACKUP_DIR"
if [ -d "$TARGET" ] && [ "$(ls -A $TARGET 2>/dev/null)" ]; then
    tar -czf "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz" -C "$TARGET" .
    echo "  ✅ 备份 → backups/backup_${TIMESTAMP}.tar.gz"
fi

echo "  解压新文件..."
tar -xzf /tmp/aitoollab-deploy.tar.gz -C "$TARGET"
rm -f /tmp/aitoollab-deploy.tar.gz

# 清理超过7天的备份
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo "  ✅ 部署完成！"
DEPLOY_SCRIPT

# 清理本地临时文件
rm -f /tmp/aitoollab-deploy.tar.gz

echo ""
echo "==========================================="
echo "  🎉 部署成功!"
echo "  https://www.aitoollab.cn"
echo "==========================================="

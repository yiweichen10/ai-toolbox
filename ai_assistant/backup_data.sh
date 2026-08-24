#!/bin/bash
# 每日备份 AI 助手运行时数据（点赞/反馈等），保留最近 14 份
# 由 /etc/cron.d/aitoollab-data 定时调用（每天 03:00）
set -euo pipefail

SRC_DIR="/var/www/aitoollab/data"
DST_DIR="/var/www/aitoollab/backups/data"

mkdir -p "$DST_DIR"
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "$DST_DIR/data_${TS}.tar.gz" -C "$(dirname "$SRC_DIR")" "$(basename "$SRC_DIR")" 2>/dev/null || true

# 只保留最近 14 份
ls -t "$DST_DIR"/data_*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "backup ok: $DST_DIR/data_${TS}.tar.gz"

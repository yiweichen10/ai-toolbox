#!/usr/bin/env bash
# 本地一键配置钉钉群机器人 Webhook（内容走 stdin，不进入命令行/历史）
# 用法1（仅 Webhook）：
#   echo 'https://oapi.dingtalk.com/robot/send?access_token=xxx' | bash scripts/set_dingtalk_webhook.sh
# 用法2（加签模式，第二行为密钥）：
#   printf '%s\n%s' 'https://oapi.dingtalk.com/robot/send?access_token=xxx' 'SECxxx' | bash scripts/set_dingtalk_webhook.sh
set -uo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
SERVER_IP="121.43.144.99"
REMOTE_DIR="/opt/aitoollab-assistant"
ENV_FILE="/etc/aitoollab/health-alert.env"

if [ -t 0 ]; then
  echo "错误：请通过管道传入 Webhook，例如："
  echo "  echo 'https://oapi.dingtalk.com/robot/send?access_token=xxx' | bash $0"
  exit 1
fi

cat | ssh $SSH_OPTS "root@${SERVER_IP}" "mkdir -p ${REMOTE_DIR} && python3 ${REMOTE_DIR}/set_alert_key.py ${ENV_FILE}"

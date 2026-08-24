#!/usr/bin/env bash
# 重置服务器 AI 助手配置文件（清空 Key，保留 600 权限）——用于 Key 写坏后重新来
set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
ENV_FILE="/etc/aitoollab/ai-assistant.env"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no root@121.43.144.99 \
  "printf '%s\n' '# AI 工具助手配置' > ${ENV_FILE} && chmod 600 ${ENV_FILE} && echo OK && cat ${ENV_FILE}"

#!/usr/bin/env bash
# ============================================================
# deploy_assistant.sh - 部署 AI 工具助手后端服务到服务器
# 用法:
#   bash scripts/deploy_assistant.sh                  # 部署服务（无 Key，mock 模式）
#   echo 'sk-xxx' | bash scripts/deploy_assistant.sh --key       # 写入智谱 GLM Key
#   echo 'sk-xxx' | bash scripts/deploy_assistant.sh --qwen-key  # 写入千问（DashScope）Key
#   bash scripts/deploy_assistant.sh --reload         # 仅重启服务（改配置后）
# 安全说明：
#   Key 通过 stdin 传入（见上方 --key 用法），不会出现在命令行参数、
#   进程列表、shell 历史或 git 中；服务器端权限锁定为 600（仅 root 可读）。
# 服务器: 121.43.144.99 / /opt/aitoollab-assistant
# ============================================================
set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519_aitoollab"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
SERVER_IP="121.43.144.99"
REMOTE_DIR="/opt/aitoollab-assistant"
ENV_FILE="/etc/aitoollab/ai-assistant.env"
SERVICE="aitoollab-assistant"

MODE="deploy"
KEY=""
KEY_NAME="ZHIPU_API_KEY"
if [ "${1:-}" = "--key" ] || [ "${1:-}" = "--qwen-key" ]; then
  MODE="key"
  if [ "${1:-}" = "--qwen-key" ]; then
    KEY_NAME="DASHSCOPE_API_KEY"
  fi
  if [ -t 0 ]; then
    # 交互模式：不回显输入
    echo -n "粘贴 ${KEY_NAME}（输入不回显）: "
    read -r -s KEY
    echo ""
  else
    read -r KEY
  fi
  if [ -z "$KEY" ]; then
    echo "错误：未读取到 Key（可用 echo 'sk-xxx' | bash $0 ${1:-}）"
    exit 1
  fi
  # 本地先校验，避免把带空格/中文的脏内容送到服务器
  if ! printf '%s' "$KEY" | grep -Eq '^[A-Za-z0-9._-]{10,200}$'; then
    echo "错误：Key 格式非法——只能包含字母/数字/._-，且不能有空格或中文。"
    echo "      请确认只粘贴 Key 本身（可先运行: printf '%s' \"\$KEY\" | od -c | head）"
    exit 1
  fi
elif [ "${1:-}" = "--reload" ]; then
  MODE="reload"
fi

echo "==========================================="
echo "  AI 工具助手后端部署 (${MODE})"
echo "  目标: ${SERVER_IP}:${REMOTE_DIR}"
echo "==========================================="

# ---------- 0) 上传服务代码 ----------
echo "[1/4] 上传服务代码..."
ssh $SSH_OPTS "root@${SERVER_IP}" "mkdir -p ${REMOTE_DIR} /etc/aitoollab /var/www/aitoollab/data"
scp -q $SSH_OPTS "$(dirname "$0")/../ai_assistant/server.py" "root@${SERVER_IP}:${REMOTE_DIR}/server.py"
scp -q $SSH_OPTS "$(dirname "$0")/../ai_assistant/set_key.py" "root@${SERVER_IP}:${REMOTE_DIR}/set_key.py"
scp -q $SSH_OPTS "$(dirname "$0")/../ai_assistant/health_alert.py" "root@${SERVER_IP}:${REMOTE_DIR}/health_alert.py"
scp -q $SSH_OPTS "$(dirname "$0")/../ai_assistant/set_alert_key.py" "root@${SERVER_IP}:${REMOTE_DIR}/set_alert_key.py"
echo "  OK server.py + set_key.py + health_alert.py + set_alert_key.py"

# ---------- 1) 配置文件：存在性 + 权限 ----------
echo "[2/4] 检查配置文件..."
ssh $SSH_OPTS "root@${SERVER_IP}" "test -f ${ENV_FILE} || { echo '# AI 工具助手配置' > ${ENV_FILE}; echo '  (已创建空配置)'; }; chmod 600 ${ENV_FILE}"

if [ "$MODE" = "key" ]; then
  echo "  写入 API Key（stdin 传入，不回显）..."
  # 通过管道把 Key 喂给服务器上的 set_key.py（Key 不出现在任何命令行参数中）
  printf '%s' "$KEY" | ssh $SSH_OPTS "root@${SERVER_IP}" "python3 ${REMOTE_DIR}/set_key.py ${ENV_FILE} ${KEY_NAME}"
fi

echo "  安装日志轮转 + 数据备份（P0-3）..."
ssh $SSH_OPTS "root@${SERVER_IP}" "cat > /etc/logrotate.d/aitoollab" << 'LOGROT'
/var/www/aitoollab/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LOGROT
scp -q $SSH_OPTS "$(dirname "$0")/../ai_assistant/backup_data.sh" "root@${SERVER_IP}:${REMOTE_DIR}/backup_data.sh"
ssh $SSH_OPTS "root@${SERVER_IP}" "chmod +x ${REMOTE_DIR}/backup_data.sh && cat > /etc/cron.d/aitoollab-data" << 'CRON'
SHELL=/bin/bash
0 3 * * * root /opt/aitoollab-assistant/backup_data.sh >/dev/null 2>&1
CRON
echo "  OK logrotate + backup cron"

echo "  安装健康自查 + 钉钉告警（P3-10）..."
ssh $SSH_OPTS "root@${SERVER_IP}" "test -f /etc/aitoollab/health-alert.env || touch /etc/aitoollab/health-alert.env; chmod 600 /etc/aitoollab/health-alert.env; cat > /etc/cron.d/aitoollab-health" << 'CRON2'
SHELL=/bin/bash
*/5 * * * * root /usr/bin/python3 /opt/aitoollab-assistant/health_alert.py >/dev/null 2>&1
CRON2
echo "  OK 健康告警 cron（每 5 分钟）"

# ---------- 2) systemd 服务（幂等） ----------
echo "[3/4] 安装 systemd 服务..."
ssh $SSH_OPTS "root@${SERVER_IP}" "cat > /etc/systemd/system/${SERVICE}.service" << UNIT
[Unit]
Description=AI Tool Assistant (aitoollab.cn)
After=network.target

[Service]
Type=simple
WorkingDirectory=${REMOTE_DIR}
ExecStart=/usr/bin/python3 ${REMOTE_DIR}/server.py
Restart=always
RestartSec=3
EnvironmentFile=${ENV_FILE}
NoNewPrivileges=true
ProtectSystem=full
ReadWritePaths=/var/www/aitoollab/logs /var/www/aitoollab/data

[Install]
WantedBy=multi-user.target
UNIT

if [ "$MODE" != "reload" ]; then
  # ---------- 3) nginx /api/ 反代（幂等） ----------
  echo "  配置 nginx /api/ 反代..."
  ssh $SSH_OPTS "root@${SERVER_IP}" "python3 -" << 'PYEOF'
import io
path = '/etc/nginx/conf.d/aitoollab.conf'
marker = '# ====== AI Assistant API ======'
with io.open(path, 'r', encoding='utf-8') as fh:
    s = fh.read()
if marker in s:
    print('  OK 已存在，跳过')
else:
    block = '''    # ====== AI Assistant API ======
    location /api/ {
        proxy_pass http://127.0.0.1:8123;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 180s;
    }

'''
    idx = s.find('    location / {')
    if idx == -1:
        raise SystemExit('ERROR: 未找到 location / { 插入点')
    s = s[:idx] + block + s[idx:]
    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.write(s)
    print('  OK 已插入 /api/ 反代配置')
PYEOF

  ssh $SSH_OPTS "root@${SERVER_IP}" "nginx -t && nginx -s reload"
  echo "  OK nginx 配置通过并已重载"
fi

# ---------- 4) 启动/重启服务 ----------
echo "[4/4] 启动服务..."
ssh $SSH_OPTS "root@${SERVER_IP}" "systemctl daemon-reload && systemctl enable ${SERVICE} >/dev/null 2>&1; systemctl restart ${SERVICE} && sleep 2 && systemctl is-active ${SERVICE}"

echo ""
echo "  线上健康检查: https://www.aitoollab.cn/api/health"
echo "==========================================="

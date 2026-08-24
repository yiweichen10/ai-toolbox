#!/usr/bin/env bash
# 验证线上 /tools/ 挂件（默认 mock 状态应显示“即将上线”并禁用输入）
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

URL="${1:-https://www.aitoollab.cn/tools/}"
LOG="${2:-/tmp/ai_live_check.log}"

{
  echo "OPEN $URL"
  "$PWCLI" open "$URL"
  echo "OPEN_DONE rc=$?"
  sleep 3
  echo "CLICK"
  "$PWCLI" click "button[name='AI 工具助手']"
  echo "CLICK_DONE rc=$?"
  sleep 1
  echo "EVAL"
  "$PWCLI" eval "JSON.stringify({url:location.href,hasFab:!!document.getElementById('aiFab'),hasPanel:!!document.getElementById('aiPanel'),sub:document.getElementById('aiPanelSub')?document.getElementById('aiPanelSub').textContent:null,inputDisabled:document.getElementById('aiInput')?document.getElementById('aiInput').disabled:null,sendText:document.getElementById('aiSend')?document.getElementById('aiSend').textContent:null,msgCount:document.querySelectorAll('.ai-msg').length})"
  echo "EVAL_DONE rc=$?"
  echo "CONSOLE"
  "$PWCLI" console
  echo "ALL_DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

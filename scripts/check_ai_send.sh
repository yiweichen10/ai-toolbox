#!/usr/bin/env bash
# 调试：当前浏览器状态下手动发送并观察
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/ai_send_check.log}"

{
  echo "OPEN_DETAIL"
  "$PWCLI" open "http://127.0.0.1:8090/tools/chatgpt/"
  sleep 3
  echo "OPEN_FAB"
  "$PWCLI" click "#aiFab"
  sleep 1
  echo "STATE_AFTER_OPEN"
  "$PWCLI" eval "JSON.stringify({panelHidden:document.getElementById('aiPanel').hidden,inputDisabled:document.getElementById('aiInput').disabled,sendDisabled:document.getElementById('aiSend').disabled})"
  echo "FILL"
  "$PWCLI" fill "#aiInput" "推荐一个写作工具"
  "$PWCLI" eval "JSON.stringify({inputValue:document.getElementById('aiInput').value})"
  echo "CLICK_SEND"
  "$PWCLI" click "#aiSend"
  echo "STATE_AFTER_CLICK"
  "$PWCLI" eval "JSON.stringify({sendDisabled:document.getElementById('aiSend').disabled,inputValue:document.getElementById('aiInput').value,typing:!!document.querySelector('.ai-typing')})"
  sleep 3
  echo "AFTER"
  "$PWCLI" eval "JSON.stringify({msgs:[].slice.call(document.querySelectorAll('.ai-msg')).map(function(x){return x.textContent.slice(0,30);}),hasFb:!!document.querySelector('.ai-feedback')})"
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

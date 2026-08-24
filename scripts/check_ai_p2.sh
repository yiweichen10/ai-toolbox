#!/usr/bin/env bash
# P2 验证：详情页语境化提问 + 修正提示
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/ai_p2_check.log}"

{
  echo "OPEN_DETAIL"
  "$PWCLI" open "http://127.0.0.1:8090/tools/chatgpt/"
  sleep 3
  echo "OPEN_FAB"
  "$PWCLI" click "#aiFab"
  sleep 1
  echo "CHIPS"
  "$PWCLI" eval "JSON.stringify({chips:[].slice.call(document.querySelectorAll('.ai-chip')).map(function(x){return x.textContent;})})"
  echo "ASK"
  "$PWCLI" fill "#aiInput" "这个工具怎么样"
  "$PWCLI" click "#aiSend"
  sleep 3
  echo "NOTE"
  "$PWCLI" eval "JSON.stringify({note:document.querySelector('.ai-note')?document.querySelector('.ai-note').textContent:null,hasFb:!!document.querySelector('.ai-feedback')})"
  echo "CONSOLE"
  "$PWCLI" console
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

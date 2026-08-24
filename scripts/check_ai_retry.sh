#!/usr/bin/env bash
# 验证 429 排队重试：假后端前两次 429，第三次成功
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/ai_retry_check.log}"

{
  echo "OPEN"
  "$PWCLI" open "http://127.0.0.1:8090/tools/"
  sleep 2
  echo "OPEN_FAB"
  "$PWCLI" click "#aiFab"
  sleep 1
  echo "SEND_QUESTION"
  "$PWCLI" fill "#aiInput" "推荐一个写作工具"
  "$PWCLI" click "#aiSend"
  sleep 2
  echo "CHECK_QUEUE_MSG"
  "$PWCLI" eval "JSON.stringify({queue:!!document.querySelector('.ai-queue'),text:document.querySelector('.ai-queue-text')?document.querySelector('.ai-queue-text').textContent:null})"
  sleep 8
  echo "CHECK_FINAL"
  "$PWCLI" eval "JSON.stringify({msgs:[].slice.call(document.querySelectorAll('.ai-msg')).map(function(x){return x.textContent.slice(0,40);})})"
  echo "CONSOLE"
  "$PWCLI" console
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

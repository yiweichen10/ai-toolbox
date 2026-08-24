#!/usr/bin/env bash
# P1 验证：首页/详情页挂件、反馈按钮、会话记忆、清空
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/ai_p1_check.log}"

{
  echo "HOME_FAB"
  "$PWCLI" open "http://127.0.0.1:8090/"
  sleep 3
  "$PWCLI" eval "JSON.stringify({url:location.pathname,hasFab:!!document.getElementById('aiFab')})"

  echo "DETAIL_FAB"
  "$PWCLI" open "http://127.0.0.1:8090/tools/chatgpt/"
  sleep 3
  "$PWCLI" eval "JSON.stringify({url:location.pathname,hasFab:!!document.getElementById('aiFab')})"

  echo "ASK"
  "$PWCLI" click "#aiFab"
  sleep 1
  "$PWCLI" fill "#aiInput" "推荐一个写作工具"
  "$PWCLI" click "#aiSend"
  sleep 3
  "$PWCLI" eval "JSON.stringify({hasFeedback:!!document.querySelector('.ai-feedback'),fbBtns:document.querySelectorAll('.ai-fb-btn').length,answer:document.querySelector('.ai-assistant:not(.ai-typing)')?document.querySelector('.ai-assistant:not(.ai-typing)').textContent.slice(0,30):null})"

  echo "CLICK_UP"
  "$PWCLI" click ".ai-fb-up"
  sleep 1
  "$PWCLI" eval "JSON.stringify({upOn:document.querySelector('.ai-fb-up')?document.querySelector('.ai-fb-up').classList.contains('on'):null})"

  echo "RELOAD_RESTORE"
  "$PWCLI" reload
  sleep 3
  "$PWCLI" eval "JSON.stringify({msgs:[].slice.call(document.querySelectorAll('.ai-msg')).map(function(x){return x.textContent.slice(0,20);})})"

  echo "CLEAR"
  "$PWCLI" click "#aiFab"
  sleep 1
  "$PWCLI" click "#aiPanelClear"
  sleep 1
  "$PWCLI" eval "JSON.stringify({msgCount:document.querySelectorAll('.ai-msg').length})"
  echo "CONSOLE"
  "$PWCLI" console
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

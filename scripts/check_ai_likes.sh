#!/usr/bin/env bash
# 本地验证工具点赞按钮：渲染、点击、计数、不跳转、刷新后保持
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/ai_likes_check.log}"

{
  echo "OPEN"
  "$PWCLI" open "http://127.0.0.1:8090/tools/"
  sleep 3
  echo "CHECK_BTNS"
  "$PWCLI" eval "JSON.stringify({count:document.querySelectorAll('.tool-like').length,firstSlug:document.querySelector('.tool-like')?document.querySelector('.tool-like').getAttribute('data-slug'):null,firstCount:document.querySelector('.tool-like-count')?document.querySelector('.tool-like-count').textContent:null})"
  echo "CLICK_DEEPSEEK"
  "$PWCLI" click "#hot .tool-like[data-slug='deepseek']"
  sleep 2
  echo "AFTER_CLICK"
  "$PWCLI" eval "JSON.stringify({url:location.href,liked:document.querySelector('.tool-like')?document.querySelector('.tool-like').classList.contains('liked'):null,count:document.querySelector('.tool-like-count')?document.querySelector('.tool-like-count').textContent:null})"
  echo "RELOAD"
  "$PWCLI" reload
  sleep 3
  echo "AFTER_RELOAD"
  "$PWCLI" eval "JSON.stringify({liked:document.querySelector('.tool-like')?document.querySelector('.tool-like').classList.contains('liked'):null,count:document.querySelector('.tool-like-count')?document.querySelector('.tool-like-count').textContent:null})"
  echo "CONSOLE"
  "$PWCLI" console
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

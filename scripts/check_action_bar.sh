#!/usr/bin/env bash
# 详情页操作按钮版式检查：桌面/移动端高度、圆角、颜色一致性
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

LOG="${2:-/tmp/action_bar_check.log}"

{
  echo "OPEN_DETAIL"
  "$PWCLI" open "http://127.0.0.1:8090/tools/chatgpt/"
  sleep 3
  echo "DESKTOP_CHECK"
  "$PWCLI" eval "JSON.stringify((function(){var r=function(s){var el=document.querySelector('.tool-header .action-bar '+s);if(!el)return null;var c=getComputedStyle(el);var b=el.getBoundingClientRect();return {h:Math.round(b.height),radius:c.borderRadius,padding:c.padding,font:c.fontSize,bg:c.backgroundColor,border:c.borderColor,color:c.color,cls:el.className};};return {primary:r('.action-btn-primary'),fav:r('.fav-btn'),like:r('.tool-like'),tools:r('a.action-btn-ghost'),bar:document.querySelector('.tool-header .action-bar')?getComputedStyle(document.querySelector('.tool-header .action-bar')).flexWrap:null};})())"
  echo "LIKE_CLICK"
  "$PWCLI" click ".tool-header .action-bar .tool-like"
  sleep 1.5
  echo "AFTER_LIKE"
  "$PWCLI" eval "JSON.stringify((function(){var el=document.querySelector('.tool-header .action-bar .tool-like');var c=getComputedStyle(el);return {liked:el.classList.contains('liked'),bg:c.backgroundColor,color:c.color,border:c.borderColor,count:el.querySelector('.tool-like-count').textContent};})())"
  echo "MOBILE_CHECK"
  "$PWCLI" resize 390 844
  sleep 1
  "$PWCLI" eval "JSON.stringify((function(){var r=function(s){var el=document.querySelector('.tool-header .action-bar '+s);if(!el)return null;var b=el.getBoundingClientRect();var c=getComputedStyle(el);return {x:Math.round(b.x),w:Math.round(b.width),h:Math.round(b.height),flex:c.flex};};return {primary:r('.action-btn-primary'),fav:r('.fav-btn'),like:r('.tool-like'),tools:r('a.action-btn-ghost')};})())"
  echo "CONSOLE"
  "$PWCLI" console
  echo "DONE"
} > "$LOG" 2>&1

echo "LOG=$LOG"

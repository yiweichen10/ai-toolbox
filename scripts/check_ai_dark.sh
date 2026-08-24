#!/usr/bin/env bash
# 暗色模式下 AI 助手面板样式检查
set -euo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

# 切到暗色
"$PWCLI" eval "(function(){var r=document.documentElement;r.setAttribute('data-theme','dark');try{localStorage.setItem('theme','dark');}catch(e){}return r.getAttribute('data-theme');})()"

"$PWCLI" eval "JSON.stringify({theme:document.documentElement.getAttribute('data-theme'),panelBg:getComputedStyle(document.getElementById('aiPanel')).backgroundColor,msgsBg:getComputedStyle(document.getElementById('aiMsgs')).backgroundColor,fabBg:getComputedStyle(document.getElementById('aiFab')).backgroundImage,userBubble:getComputedStyle(document.querySelector('.ai-user')).color,footColor:getComputedStyle(document.querySelector('.ai-foot')).color})"

# 切回亮色
"$PWCLI" eval "(function(){document.documentElement.setAttribute('data-theme','light');try{localStorage.setItem('theme','light');}catch(e){}return 'ok';})()"

#!/usr/bin/env bash
# 本地浏览器布局检查：AI 助手挂件在桌面/手机/暗色模式下的坐标与遮挡
set -euo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

check() {
  local label="$1"
  local js="$2"
  echo "===== $label ====="
  "$PWCLI" eval "$js"
}

"$PWCLI" resize 390 844
check "MOBILE(390x844)" "JSON.stringify({vw:innerWidth,vh:innerHeight,fab:(document.getElementById('aiFab')||{}).getBoundingClientRect?document.getElementById('aiFab').getBoundingClientRect().toJSON():null,panel:(document.getElementById('aiPanel')||{}).getBoundingClientRect?document.getElementById('aiPanel').getBoundingClientRect().toJSON():null,fav:(document.getElementById('favFab')||{}).getBoundingClientRect?document.getElementById('favFab').getBoundingClientRect().toJSON():null,moon:(document.querySelector('.dark-toggle-fab')||{}).getBoundingClientRect?document.querySelector('.dark-toggle-fab').getBoundingClientRect().toJSON():null,top:(document.getElementById('backToTop')||{}).getBoundingClientRect?document.getElementById('backToTop').getBoundingClientRect().toJSON():null,panelHidden:document.getElementById('aiPanel')?document.getElementById('aiPanel').hidden:null,bodyScrollW:document.documentElement.scrollWidth})"

"$PWCLI" resize 1280 800
check "DESKTOP(1280x800)" "JSON.stringify({vw:innerWidth,vh:innerHeight,fab:(document.getElementById('aiFab')||{}).getBoundingClientRect?document.getElementById('aiFab').getBoundingClientRect().toJSON():null,panel:(document.getElementById('aiPanel')||{}).getBoundingClientRect?document.getElementById('aiPanel').getBoundingClientRect().toJSON():null,fav:(document.getElementById('favFab')||{}).getBoundingClientRect?document.getElementById('favFab').getBoundingClientRect().toJSON():null,moon:(document.querySelector('.dark-toggle-fab')||{}).getBoundingClientRect?document.querySelector('.dark-toggle-fab').getBoundingClientRect().toJSON():null,top:(document.getElementById('backToTop')||{}).getBoundingClientRect?document.getElementById('backToTop').getBoundingClientRect().toJSON():null,panelHidden:document.getElementById('aiPanel')?document.getElementById('aiPanel').hidden:null,bodyScrollW:document.documentElement.scrollWidth})"

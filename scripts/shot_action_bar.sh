#!/usr/bin/env bash
# 详情页按钮版式截图（桌面 + 移动端）
set -uo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

"$PWCLI" resize 1280 900
sleep 1
"$PWCLI" screenshot > /tmp/shot_desktop.txt 2>&1
"$PWCLI" resize 390 844
sleep 1
"$PWCLI" screenshot > /tmp/shot_mobile.txt 2>&1
echo DONE

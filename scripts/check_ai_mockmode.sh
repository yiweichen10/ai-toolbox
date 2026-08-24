#!/usr/bin/env bash
# 验证 mock 模式下挂件降级表现（应显示“即将上线”并禁用输入）
set -euo pipefail

PWCLI="/c/Users/27040/.codex/skills/playwright/scripts/playwright_cli.sh"
cd "$(dirname "$0")/.."

"$PWCLI" open "http://127.0.0.1:8090/tools/"
sleep 2
"$PWCLI" click "button[name='AI 工具助手']"
sleep 1
"$PWCLI" snapshot

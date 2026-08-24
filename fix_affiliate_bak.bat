@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === 修复 8899 管理台保存定位 Permission denied ===
python scripts\patch_affiliate_bak.py
echo.
echo 补丁执行完毕。若显示"补丁完成"，请重启管理台：
echo   python affiliate_manager.py
pause

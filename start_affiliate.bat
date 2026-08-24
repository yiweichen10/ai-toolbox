@echo off
cd /d "C:\Users\27040\WorkBuddy\20260321092139\seo-site"
netstat -ano 2>nul | findstr ":8899" | findstr "LISTENING" >nul && (
  echo %date% %time% 8899 already running, skip >> _affiliate_manager.log
  goto :eof
)
echo %date% %time% Starting watchdog... >> _affiliate_manager.log
REM watchdog 会用 CREATE_BREAKAWAY_FROM_JOB 启动 affiliate_manager，避免被父进程会话一起杀掉
start "" "C:\Users\27040\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" scripts\watchdog_affiliate.py
timeout /t 4 >nul

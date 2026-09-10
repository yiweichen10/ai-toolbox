@echo off
chcp 65001 >nul
cd /d "C:\Users\27040\WorkBuddy\20260321092139\seo-site"
netstat -ano 2>nul | findstr ":8898" | findstr "LISTENING" >nul && (
  echo 广告条管理台已在运行，直接打开浏览器...
  start "" http://127.0.0.1:8898
  goto :eof
)
echo 正在启动「顶部广告条管理台」...
start "" "C:\Users\27040\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" tpb_manager.py
timeout /t 3 >nul
start "" http://127.0.0.1:8898

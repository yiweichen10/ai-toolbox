"""保持 127.0.0.1:8899 管理页进程存活。开机自启由 start_affiliate.bat 调用本脚本。"""
import http.client
import os
import subprocess
import sys
import time

HOST = "127.0.0.1"
PORT = 8899
CHECK_INTERVAL = 30  # 秒
PYTHONW = r"C:\Users\27040\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
MANAGER = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\affiliate_manager.py"
LOG = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\_affiliate_manager.log"


def is_alive():
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=3)
        conn.request("GET", "/")
        resp = conn.getresponse()
        ok = resp.status == 200
        conn.close()
        return ok
    except Exception:
        return False


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def start_manager():
    """启动管理台。按「breakaway → 无窗口 → 普通」逐级降级。

    2026-09-10 修：原先只试 CREATE_BREAKAWAY_FROM_JOB，在受限的 Job 环境（如被上层沙箱/会话
    包在 Job 对象里）会直接抛 [WinError 5] 拒绝访问，导致 watchdog 每 60 秒重试一次仍起不来，
    8899 长期打不开——表现就是"工具管理台怎么没有了"。降级后至少能起来。"""
    attempts = [
        (subprocess.CREATE_BREAKAWAY_FROM_JOB | subprocess.CREATE_NO_WINDOW, 'breakaway'),
        (subprocess.CREATE_NO_WINDOW, 'no-window'),
        (0, 'plain'),
    ]
    for flags, tag in attempts:
        try:
            subprocess.Popen(
                [PYTHONW, MANAGER],
                cwd=os.path.dirname(MANAGER),
                creationflags=flags,
                close_fds=True,
            )
            log(f"watchdog: started affiliate_manager ({tag})")
            return True
        except OSError as e:
            log(f"watchdog: start failed ({tag}): {e}")
    return False


def main():
    log("watchdog: started")
    fail_count = 0
    while True:
        if is_alive():
            fail_count = 0
        else:
            fail_count += 1
            log(f"watchdog: health check failed ({fail_count})")
            if fail_count >= 2:
                start_manager()
                fail_count = 0
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

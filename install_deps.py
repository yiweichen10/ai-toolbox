import subprocess
import sys

def install(package):
    print(f"Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "--timeout", "60"])
        print(f"Successfully installed {package}")
    except Exception as e:
        print(f"Failed to install {package}: {e}")

if __name__ == "__main__":
    install("httpx")
    install("pypinyin")

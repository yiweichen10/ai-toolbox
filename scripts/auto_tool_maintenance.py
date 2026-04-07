import os
import json
import subprocess
import sys
from datetime import datetime

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISH_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'publish_new_tools.py')
GENERATE_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'generate_tools.py')
TOOLS_JSON = os.path.join(BASE_DIR, 'data', 'tools.json')

def get_unpublished_count():
    if not os.path.exists(TOOLS_JSON):
        return 0
    with open(TOOLS_JSON, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    return sum(1 for t in tools if not t.get('published', False))

def run_step(name, cmd):
    print(f"\n>>> 正在执行: {name}")
    print(f"命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"❌ {name} 失败 (exit code: {result.returncode})")
        return False
    print(f"✅ {name} 成功")
    return True

def main():
    print(f"[{datetime.now()}] === 开始工具库自动维护任务 ===")
    
    # 1. 检查库存
    count = get_unpublished_count()
    print(f"当前未发布工具库存: {count}")
    
    # 2. 如果库存低，先补充
    if count < 5:
        print("⚠️ 库存不足 (低于 5 个)，正在自动补充...")
        if not run_step("补充新工具", [sys.executable, GENERATE_SCRIPT, '--count', '20']):
            print("停止后续流程。")
            return
    
    # 3. 执行发布 (包含 build 和 git push)
    if not run_step("发布新工具", [sys.executable, PUBLISH_SCRIPT]):
        return

    print(f"[{datetime.now()}] === 工具库维护任务全部完成 ===")

if __name__ == "__main__":
    main()

import json
import os
import random
import subprocess
from datetime import datetime

# 定义文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_JSON_PATH = os.path.join(DATA_DIR, 'tools.json')
BUILD_SCRIPT_PATH = os.path.join(BASE_DIR, 'scripts', 'build.py')

def publish_new_tools(num_to_publish=3):
    """
    发布新的AI工具。
    从tools.json中找到未发布的工具，随机选择num_to_publish个设置为已发布，
    然后运行build.py重新生成网站。
    """
    print(f"[{datetime.now()}] 正在尝试发布 {num_to_publish} 个新工具...")

    # 1. 读取tools.json
    all_tools = []
    if os.path.exists(TOOLS_JSON_PATH):
        with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
            all_tools = json.load(f)
    else:
        print(f"错误: {TOOLS_JSON_PATH} 文件不存在。")
        return

    unpublished_tools = [tool for tool in all_tools if not tool.get('published', False)]
    
    if not unpublished_tools:
        print("没有未发布的工具了，任务结束。")
        return

    # 2. 随机选择num_to_publish个工具进行发布
    tools_to_publish_now = random.sample(unpublished_tools, min(num_to_publish, len(unpublished_tools)))

    for tool in tools_to_publish_now:
        tool['published'] = True
        print(f"  - 标记工具为已发布: {tool['name']} ({tool['slug']})")
    
    # 3. 将更新后的数据写回tools.json
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_tools, f, ensure_ascii=False, indent=4)
    print(f"已更新 {len(tools_to_publish_now)} 个工具的发布状态到 {TOOLS_JSON_PATH}")

    # 4. 运行build.py重新生成网站
    print(f"正在运行 {BUILD_SCRIPT_PATH} 重新生成网站...")
    result = subprocess.run(['python', BUILD_SCRIPT_PATH], capture_output=False)
    if result.returncode != 0:
        print("网站构建失败！")
        return
    print("网站重新生成完成。")

    # 5. Git commit + push 部署到 Vercel
    tool_names = [t['name'] for t in tools_to_publish_now]
    commit_msg = f"publish: 发布新工具 {', '.join(tool_names)}"
    print(f"正在 git commit + push: {commit_msg}")
    try:
        subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, check=True)
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=BASE_DIR, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR, check=True)
        print("Git commit + push 成功，Vercel 将自动部署。")
    except subprocess.CalledProcessError as e:
        print(f"Git 操作失败: {e}")

    print(f"[{datetime.now()}] 新工具发布任务完成。")

if __name__ == '__main__':
    publish_new_tools(num_to_publish=3)

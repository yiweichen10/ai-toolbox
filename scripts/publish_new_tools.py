import json
import os
import random
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
    os.system(f"python {BUILD_SCRIPT_PATH}") # 使用os.system执行，确保build.py的输出可见
    print("网站重新生成完成。")

    print(f"[{datetime.now()}] 新工具发布任务完成。")

if __name__ == '__main__':
    publish_new_tools(num_to_publish=3)

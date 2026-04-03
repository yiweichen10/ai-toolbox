import json
import os
import random
import subprocess
import sys
from datetime import datetime

# 定义文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
TOOLS_JSON_PATH = os.path.join(DATA_DIR, 'tools.json')
BUILD_SCRIPT_PATH = os.path.join(BASE_DIR, 'scripts', 'build.py')

# OG 图片生成函数
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gen_seo_images import make_og_image, generate_image

def generate_tool_og_images(tools):
    """为工具列表生成 OG 图片和信息图，返回 (成功数, 跳过数)"""
    count = 0
    skip = 0
    for tool in tools:
        slug = tool['slug']
        og_path = os.path.join(IMAGES_DIR, 'og', f'{slug}-og.png')
        inf_path = os.path.join(IMAGES_DIR, 'infographics', f'{slug}-infographic.png')
        if not os.path.exists(og_path):
            print(f"    生成 OG 图片: {tool['name']}...", end=' ', flush=True)
            og_html = make_og_image(tool, tools)
            if generate_image(og_html, og_path):
                print('OK')
                count += 1
            else:
                print('FAIL')
        else:
            print(f"    OG 图片已存在: {tool['name']}，跳过")
            skip += 1
        if not os.path.exists(inf_path):
            # 信息图暂不强制要求，只确保 OG 必成
            pass
    return count, skip

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

    published_tools = [tool for tool in all_tools if tool.get('published', False)]
    unpublished_tools = [tool for tool in all_tools if not tool.get('published', False)]
    
    print(f"  库存状态: 已发布 {len(published_tools)} 个, 未发布 {len(unpublished_tools)} 个, 总计 {len(all_tools)} 个")
    
    if not unpublished_tools:
        print("⚠️ 库存已耗尽！没有未发布的工具了，需要补充新工具。")
        print("  → 运行 python scripts/generate_tools.py --count 20 来补充")
        return

    if len(unpublished_tools) < 10:
        print(f"⚠️ 低库存预警！仅剩 {len(unpublished_tools)} 个未发布工具，建议尽快补充。")
        print(f"  → 预计还能发布 {len(unpublished_tools) // num_to_publish} 天")
        print(f"  → 运行 python scripts/generate_tools.py --count 20 来补充")

    # 2. 随机选择num_to_publish个工具进行发布
    tools_to_publish_now = random.sample(unpublished_tools, min(num_to_publish, len(unpublished_tools)))

    for tool in tools_to_publish_now:
        tool['published'] = True
        print(f"  - 标记工具为已发布: {tool['name']} ({tool['slug']})")
    
    # 3. 将更新后的数据写回tools.json
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_tools, f, ensure_ascii=False, indent=4)
    print(f"已更新 {len(tools_to_publish_now)} 个工具的发布状态到 {TOOLS_JSON_PATH}")

    # 4. 为本次发布工具生成 OG 图片（关键！防止死链）
    print(f"正在为本次发布的 {len(tools_to_publish_now)} 个工具生成 OG 图片...")
    og_count, og_skip = generate_tool_og_images(tools_to_publish_now)
    print(f"OG 图片生成完成: {og_count} 个成功, {og_skip} 个跳过(已存在)")

    # 5. 运行build.py重新生成网站
    print(f"正在运行 {BUILD_SCRIPT_PATH} 重新生成网站...")
    result = subprocess.run(['python', BUILD_SCRIPT_PATH], capture_output=False)
    if result.returncode != 0:
        print("网站构建失败！")
        return
    print("网站重新生成完成。")

    # 6. Git commit + push 部署到 Vercel
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

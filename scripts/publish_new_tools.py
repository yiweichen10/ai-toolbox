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

    # 4.5 [Phase3] 自动为新发布的工具生成替代方案页 + 对比页
    print(f"正在为本次发布的工具生成替代方案页 + 对比页...")
    try:
        from generate_compare_pages import (
            generate_alternatives_prompt, call_ai, 
            load_compare_data, save_compare_data, build_compare_slug
        )
        import re as _re
        import time as _time
        
        compare_file = os.path.join(DATA_DIR, 'compare_data.json')
        existing = load_compare_data() if os.path.exists(compare_file) else {"compares": [], "alternatives": [], "metadata": {}}
        existing_alts = existing.get("alternatives", [])
        existing_compares = existing.get("compares", [])
        existing_alt_slugs = set([a.get('slug', '') for a in existing_alts])
        
        new_alt_count = 0
        new_compare_count = 0
        
        for tool in tools_to_publish_now:
            alt_slug = f"{tool['slug']}-alternatives"
            
            # 生成替代方案页（如果还没有）
            if alt_slug not in existing_alt_slugs:
                print(f"  [ALT] 生成 {tool['name']} 替代方案页...")
                prompt = generate_alternatives_prompt(tool)
                result = call_ai(prompt, max_tokens=3500)
                if result:
                    try:
                        json_match = _re.search(r'\{[\s\S]*\}', result)
                        if json_match:
                            alt_data = json.loads(json_match.group())
                            existing_alts.append(alt_data)
                            new_alt_count += 1
                            print(f"       [OK] {alt_data.get('title', 'N/A')[:40]}")
                    except Exception as e:
                        print(f"       [WARN] Parse error: {e}")
                
                _time.sleep(2)  # API限速
            
            # 生成与热门工具的对比页
            hot_tools = ['chatgpt', 'claude', 'deepseek', 'kimi', 'midjourney', 'cursor', 'copilot']
            published_slugs = [t['slug'] for t in published_tools] + [t['slug'] for t in tools_to_publish_now]
            
            for hot_slug in hot_tools:
                if hot_slug == tool['slug']:
                    continue
                if hot_slug not in published_slugs:
                    continue
                
                combo_slug = build_compare_slug([tool['slug'], hot_slug])
                existing_compare_slugs = set([c.get('slug', '') for c in existing_compares])
                
                if combo_slug not in existing_compare_slugs:
                    hot_tool_obj = next((t for t in all_tools if t['slug'] == hot_slug), None)
                    if not hot_tool_obj:
                        continue
                    
                    from generate_compare_pages import generate_compare_prompt
                    print(f"  [CMP] 生成 {tool['name']} vs {hot_tool_obj['name']} 对比页...")
                    cmp_prompt = generate_compare_prompt([tool, hot_tool_obj])
                    cmp_result = call_ai(cmp_prompt, max_tokens=3500)
                    if cmp_result:
                        try:
                            jmatch = _re.search(r'\{[\s\S]*\}', cmp_result)
                            if jmatch:
                                cmp_data = json.loads(jmatch.group())
                                cmp_data['page_type'] = 'compare'
                                cmp_data['priority'] = 'medium'
                                cmp_data['source'] = 'auto-publish'
                                existing_compares.append(cmp_data)
                                new_compare_count += 1
                                print(f"           [OK]")
                        except Exception as e:
                            print(f"           [WARN] {e}")
                    
                    _time.sleep(2)
        
        # 保存更新后的数据
        if new_alt_count > 0 or new_compare_count > 0:
            existing["alternatives"] = existing_alts
            existing["compares"] = existing_compares
            existing["metadata"] = {
                "total_compares": len(existing_compares),
                "total_alternatives": len(existing_alts),
                "last_updated": datetime.now().isoformat(),
            }
            save_compare_data(existing)
            print(f"  Phase3 完成: +{new_alt_count} 替代方案页, +{new_compare_count} 对比页")
        else:
            print(f"  Phase3: 所有替代/对比页已存在，无需新建")
            
    except ImportError:
        print("  [INFO] generate_compare_pages module not found, skip Phase3")
    except Exception as e:
        print(f"  [WARN] Phase3 自动生成失败 (非致命): {e}")

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

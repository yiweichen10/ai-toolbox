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

    # 1. 读取工具（目录优先：data/tools/*.json 聚合，回退单体）
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from data_store import load_all_tools
    all_tools = load_all_tools()
    if not all_tools:
        print(f"错误: 无工具数据（data/tools/ 与 {TOOLS_JSON_PATH} 均为空）。")
        return

    published_tools = [tool for tool in all_tools if tool.get('published', False)]
    unpublished_tools = [tool for tool in all_tools if not tool.get('published', False)]

    # 🔴 发布闸门（2026-07-29 落地）：仅选"已通过 Agent 事实核查"的未发布工具
    # 防再犯 gpt-live 类幻觉：未核验 / 冲突存疑的工具绝不自动上线。
    verified_unpublished = [
        t for t in unpublished_tools
        if t.get('content_verified') is True and not t.get('conflict')
    ]
    unverified_unpublished = [t for t in unpublished_tools if t not in verified_unpublished]

    print(f"  库存状态: 已发布 {len(published_tools)} 个, 未发布 {len(unpublished_tools)} 个, 总计 {len(all_tools)} 个")
    print(f"  🔎 Agent核验合格(可发布): {len(verified_unpublished)} 个 | 未核验/存疑(禁发布): {len(unverified_unpublished)} 个")

    # 闸门：没有合格工具时不发布任何内容，避免幻觉上线
    if not verified_unpublished:
        print("⛔ 库存无通过 Agent 核验的工具！为防止幻觉上线，本次不发布任何工具。")
        print(f"  → 请先对 {len(unverified_unpublished)} 个未核验工具跑 Agent 事实核查批次（见 skill: agent-tool-author）。")
        return

    # 后续选取改用 verified_unpublished
    unpublished_tools = verified_unpublished

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

    today_iso = datetime.now().strftime('%Y-%m-%d')
    for tool in tools_to_publish_now:
        tool['published'] = True
        # 2026-08-01 修复: 不再覆盖 created_date(真实收录日期保持不变)
        # created_date = 入库/收录时间, 永不改写; published_date = 首次发布时间
        # 首页"今日推荐"改用 published_date,"最近更新"改用 updated_date(见 build.py)
        if not tool.get('published_date'):
            tool['published_date'] = today_iso
        if not tool.get('created_date'):
            tool['created_date'] = today_iso  # 仅当收录日期缺失时兜底
        print(f"  - 标记工具为已发布: {tool['name']} ({tool['slug']})")
    
    # 3. 将更新后的数据保存（目录优先：写 data/tools/<slug>.json + 原子同步单体）
    from data_store import save_tool
    for tool in tools_to_publish_now:
        save_tool(tool)
    print(f"已发布 {len(tools_to_publish_now)} 个工具到 data/tools/（并同步 {TOOLS_JSON_PATH}）")

    # 3.5 自动抓取工具官方 favicon/logo（治本 LOGO 未闭环，2026-08-17）
    # 背景：入库只写 emoji、从不核实真实 LOGO，导致大量工具回退 emoji 色块。
    print(f"正在为本次发布的工具抓取官方图标...")
    try:
        from fetch_icons import fetch_icon
        for t in tools_to_publish_now:
            r, src = fetch_icon(t['slug'], t.get('url', ''))
            print(f"  {'✅' if r else '❌'} {t['slug']} ({src})")
    except Exception as e:
        print(f"  [WARN] 图标抓取失败(非致命): {e}")

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
    # 2026-08-24：-t tools --no-push（拆分后实测优化）
    #   -t tools：只重建工具相关页（详情/分类/首页/tools-data/sitemap），发布工具不涉及文章/词典/快讯，全量重建属浪费
    #   --no-push：发布链路后续自动化会 build --target tools（推送点）或 deploy.sh，此处推送会造成百度 over quota + IndexNow 重复推送
    print(f"正在运行 {BUILD_SCRIPT_PATH} -t tools --no-push 重新生成网站...")
    result = subprocess.run(['python', BUILD_SCRIPT_PATH, '-t', 'tools', '--no-push'], capture_output=False)
    if result.returncode != 0:
        print("网站构建失败！")
        return
    print("网站重新生成完成。")

    # 6. Git commit + push 部署到 Vercel
    tool_names = [t['name'] for t in tools_to_publish_now]
    commit_msg = f"publish: 发布新工具 {', '.join(tool_names)}"
    print(f"正在 git commit + push: {commit_msg}")
    try:
        # 只 add 已跟踪文件 + 本次新增的工具页，避免误提交临时文件
        subprocess.run(['git', 'add', '-u'], cwd=BASE_DIR, check=True)  # only tracked modified files
        for t in tools_to_publish_now:
            tool_dir = os.path.join(BASE_DIR, 'tools', t['slug'])
            if os.path.exists(tool_dir):
                subprocess.run(['git', 'add', 'tools/' + t['slug'] + '/'], cwd=BASE_DIR, check=False)
        # 确保关键生成文件被跟踪
        for path in ['data/tools.json', 'images/og/', 'sitemap.xml', 'js/tools-data.js', 'index.html']:
            subprocess.run(['git', 'add', path], cwd=BASE_DIR, check=False)
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=BASE_DIR, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR, check=True)
        print("Git commit + push 成功，Vercel 将自动部署。")
    except subprocess.CalledProcessError as e:
        print(f"Git 操作失败: {e}")

    print(f"[{datetime.now()}] 新工具发布任务完成。")

if __name__ == '__main__':
    publish_new_tools(num_to_publish=3)

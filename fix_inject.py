
import os
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
content = open(file_path, 'r', encoding='utf-8').read()

new_func = '''def inject_global_nav():
    """后处理：将全局导航栏注入到header内部，支持中英文双语切换"""
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        # 排除系统目录
        if any(x in root.lower() for x in ['node_modules', '.git', 'scripts', 'data']):
            continue
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # 只有在没有注入过导航栏的情况下才注入
                if '</header>' in file_content and 'class="global-nav"' not in file_content:
                    # 探测语言：通过 <html lang="en"> 标签
                    lang = 'en' if 'lang="en"' in file_content.lower() else 'zh-CN'
                    nav_html = get_global_nav(lang)
                    
                    # 在 </header> 标签之前插入，使其成为 header 的子元素
                    file_content = file_content.replace('</header>', nav_html + '\\n    </header>', 1)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    injected += 1
            except Exception as e:
                print(f"Error injecting into {fpath}: {e}")
    if injected > 0:
        print(f'[Post] Injected dynamic global nav into {injected} HTML files.')
    return injected'''

# Use regex to find and replace the function
pattern = r'def inject_global_nav\(\):[\s\S]*?return injected'
if re.search(pattern, content):
    new_content = re.sub(pattern, new_func, content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Success')
else:
    print('Failed to find inject_global_nav with regex')


import os
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
content = open(file_path, 'r', encoding='utf-8').read()

def update_index(m):
    body = m.group(0)
    # Inject helper
    if "t = lambda k: get_ui_text(k, 'zh-CN')" not in body:
        body = body.replace("lang = 'zh-CN'", "lang = 'zh-CN'\n    t = lambda k: get_ui_text(k, lang)")
    
    # Replace header in the template string 'html'
    header_old_pattern = r'<header class="header">[\s\S]*?<h1>.*?AI工具宝箱.*?<span>.*?</span></h1>[\s\S]*?</header>'
    header_new = '''<header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ {t('header_title')} <span>{t('header_subtitle')}</span></h1></a>
        </div>
    </header>'''
    
    # We need to replace it in the 'html' variable after it's read from file
    body = body.replace('html = f.read()', 'html = f.read()\n    # Apply I18N to static template\n    html = re.sub(r\'<header class="header">[\s\S]*?<h1>.*?AI工具宝箱.*?<span>.*?</span></h1>[\s\S]*?</header>\', f\'\'\'' + header_new + r'\'\'\', html)')
    
    # Breadcrumbs and Footer in index template
    body = body.replace('html = re.sub(', 'html = html.replace(\'© 2026 AI工具宝箱 · 每日精选优质AI工具\', f\'© 2026 {t("header_title")} · {t("footer_text")}\')\n    html = re.sub(')

    return body

content = re.sub(r'def build_index_page\(tools, articles\):[\s\S]*?return html', update_index, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Success')

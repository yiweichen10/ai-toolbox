
import json
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'

def fix_json_dump(content):
    # 将所有的 json.dumps(..., ensure_ascii=False) 替换为包含 indent=2 的版本，并确保编码正确
    # 特别是针对 breadcrumb, software_data, faq_sd 等
    
    # 修正 build_tool_page 中的 JSON 导出
    content = content.replace(
        'json.dumps(breadcrumb_data)', 
        'json.dumps(breadcrumb_data, ensure_ascii=False, indent=2)'
    )
    content = content.replace(
        'json.dumps(software_data)', 
        'json.dumps(software_data, ensure_ascii=False, indent=2)'
    )
    content = content.replace(
        'json.dumps(faq_sd, ensure_ascii=False)', 
        'json.dumps(faq_sd, ensure_ascii=False, indent=2)'
    )
    
    # 修正 build_article_page 中的 OG Image 和 JSON-LD
    # 先找 build_article_page 函数
    start = content.find('def build_article_page(article, all_articles, all_tools=None):')
    if start != -1:
        end = content.find('return html', start)
        func_body = content[start:end+20] # 包含 return html 部分
        
        # 修复 OG Image 逻辑 (之前可能误用了 slug 而不是 og_image 变量)
        # 查找 f'    <meta property="og:image" content="{...}">'
        new_func_body = func_body
        
        # 确保 og_image 变量被正确定义和使用
        if 'og_image = ensure_og_image' not in func_body:
             # 如果丢失了这一行，补上
             new_func_body = new_func_body.replace(
                 "lang = article.get('lang', 'zh-CN')",
                 "lang = article.get('lang', 'zh-CN')\n    slug = article.get('slug', '')\n    og_image = ensure_og_image(slug, data_obj=article, is_article=True)"
             )
        
        # 确保 JSON-LD 导出格式
        new_func_body = new_func_body.replace(
            'json.dumps(breadcrumb)', 
            'json.dumps(breadcrumb, ensure_ascii=False, indent=2)'
        )
        new_func_body = new_func_body.replace(
            'json.dumps(article_schema)', 
            'json.dumps(article_schema, ensure_ascii=False, indent=2)'
        )
        
        content = content.replace(func_body, new_func_body)

    return content

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = fix_json_dump(content)

# 额外检查 build_article_page 中的 og:image 标签
# 确保它是 <meta property="og:image" content="{og_image}"> 而不是 {slug} 或其他
content = re.sub(
    r'<meta property="og:image" content="\{slug\}">',
    r'<meta property="og:image" content="{og_image}">',
    content
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done fixing JSON-LD and OG Image tag')

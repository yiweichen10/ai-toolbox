import os
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define all functions we want to update
functions = [
    ('build_tool_page', 'tool'),
    ('build_compare_page', 'compare_data'),
    ('build_alternatives_page', 'alt_data'),
    ('build_quiz_page', 'quiz_data'),
    ('build_ranking_page', 'ranking_data'),
    ('build_live_page', 'live_data'),
    ('build_category_page', None), # No direct object, default to zh-CN
    ('build_article_page', 'article'),
    ('build_index_page', None) # No direct object, default to zh-CN
]

for func_name, obj_name in functions:
    # Match the function body
    pattern = rf'def {func_name}\(.*?\):(.*?)(?=def |$)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        body = match.group(1)
        # Add lang definition at the start of the body
        if obj_name:
            lang_def = f"\n    lang = {obj_name}.get('lang', 'zh-CN')\n"
        else:
            lang_def = f"\n    lang = 'zh-CN'\n"
            
        if 'lang =' not in body:
            # Insert after docstring or at the start
            docstring_match = re.search(r'^\s*""".*?"""', body, re.DOTALL)
            if docstring_match:
                new_body = body[:docstring_match.end()] + lang_def + body[docstring_match.end():]
            else:
                new_body = lang_def + body
            
            # Replace <html lang="zh-CN"> with <html lang="{lang}">
            new_body = new_body.replace('<html lang="zh-CN">', '<html lang="{lang}">')
            
            content = content.replace(body, new_body)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated build.py with dynamic lang support.")

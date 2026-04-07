import os

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'rb') as f:
    content = f.read()

# Fix the broken newlines/encoding from previous failed edit
# The broken part looks like: 
# b"    'C': {`n        'label': '\xef\xbf\xbd\xef\xbf\xbd\xef\xbf\xbd\xef\xbf\xbd\xef\xbf\xbd\xef\xbf\xbd',`n        'priority': 3,"
# We want to replace everything between ARTICLE_TYPES = { and the next } with our desired structure.

start_marker = b'ARTICLE_TYPES = {'
end_marker = b'PROMPTS_A = ['

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_block = u'''ARTICLE_TYPES = {
    'A': {
        'label': '国产AI对比评测',
        'priority': 1,
        'description': '国产/中美AI模型或工具的深度对比，真实测试数据',
        'keywords_target': '中文用户搜索的对比决策词',
    },
    'B': {
        'label': '场景化工具推荐',
        'priority': 2,
        'description': '按人群/场景/预算推荐AI工具组合',
        'keywords_target': '场景长尾词 + 职业词',
    },
    'C': {
        'label': '教程指南',
        'priority': 3,
        'description': '具体AI工具从入门到进阶的实操教程',
        'keywords_target': '"怎么用""新手入门"类长尾教程词',
    },
    'E': {
        'label': 'English Global Content',
        'priority': 0,
        'description': 'English articles for global audience (High Priority for Launch)',
        'keywords_target': 'Global AI trends, ROI, high-intent English keywords',
    },
}

# ================================================================
#  A 类：国产AI对比评测（核心差异化内容）
# ================================================================
'''.encode('utf-8')
    # We also need to fix the rest of the file which might have been affected by the encoding mess if it shifted things.
    # But based on the read output, it seems only that block was mangled.
    
    # Let's also fix any remaining `n which might be literal strings now
    # Wait, the read output showed `n which usually means literal backtick then n.
    
    final_content = content[:start_idx] + new_block + content[end_idx:]
    # Sanitize any literal `n that might have leaked
    final_content = final_content.replace(b'`n', b'\n')
    
    with open(path, 'wb') as f:
        f.write(final_content)
    print("Successfully fixed and updated generate_articles.py")
else:
    print(f"Markers not found: start={start_idx}, end={end_idx}")

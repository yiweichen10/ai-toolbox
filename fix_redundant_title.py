import os
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the pattern to find the messy area
# We use \s* to match any indentation
pattern = r'\n\s*raw_content = article\.get\(\'content\', \'\'\)\.strip\(\).*?content_html = markdown_to_html\(raw_content\)'

# The replacement block (formatted correctly with 4 spaces)
new_clean_block = r"""
    raw_content = article.get('content', '').strip()
    # 自动移除正文中重复的标题（如果正文以 # Title 开头）
    # 使用 re.escape 避免特殊字符干扰，并匹配开头
    title_line_pattern = r'^#\s+.*?' + re.escape(article['title'][:10]) + r'.*?\n'
    raw_content = re.sub(title_line_pattern, '', raw_content, count=1, flags=re.IGNORECASE)
    content_html = markdown_to_html(raw_content)"""

# Use a lambda for repl to avoid "bad escape" errors in re.sub
content = re.sub(pattern, lambda m: new_clean_block, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Cleanly fixed title redundancy in build.py (v2)")

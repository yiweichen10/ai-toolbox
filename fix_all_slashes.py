
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all accidental backslashes before quotes
# This is likely from my restore_build.py script interpreting something wrong
new_content = content.replace("\\'", "'").replace('\\"', '"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done')

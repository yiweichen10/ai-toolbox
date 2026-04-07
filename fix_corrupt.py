
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace \{t(\' with {t('
# This pattern matches f-string templates that got double escaped?
new_content = content.replace("{t(\\'", "{t('").replace("\\')}", "')}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done')

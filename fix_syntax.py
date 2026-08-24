
import os
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
content = open(file_path, 'r', encoding='utf-8').read()

# Replace the whole UI_I18N block
new_ui_i18n = open(r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\ui_i18n.py', 'r', encoding='utf-8').read().strip()

# Match the broken block
# It starts with UI_I18N = { and ends with some complex nested braces
pattern = r'UI_I18N = \{[\s\S]*?more_alternatives\': \'🔗 More Alternatives\',\s+\}\s+\}\s+\}'
if re.search(pattern, content):
    content = re.sub(pattern, new_ui_i18n, content)
else:
    # Try a simpler pattern if the above fails
    pattern = r'UI_I18N = \{[\s\S]*?\'en\': \{'
    content = re.sub(r'UI_I18N = \{[\s\S]*?\}\s+\}\s+\}', new_ui_i18n, content, count=1)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Success')

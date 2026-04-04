# -*- coding: utf-8 -*-
"""
Inject Live Dashboard functions into build.py
"""
import re

with open(r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Read the live functions from a separate file
with open(r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\_live_functions.py', 'r', encoding='utf-8') as f:
    live_code = f.read()

insert_marker = "    return html\n\n\ndef build_category_page(category_name, tools_in_category):"
if insert_marker in content:
    new_content = content.replace(insert_marker, live_code.strip() + "\n\n\ndef build_category_page(category_name, tools_in_category):")
    with open(r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('[OK] Injected!')
else:
    print('[FAIL] Marker not found')

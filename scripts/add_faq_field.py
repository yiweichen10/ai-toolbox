#!/usr/bin/env python3
"""为所有工具添加 FAQ 字段"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_PATH = os.path.join(BASE_DIR, 'data', 'tools.json')

# 读取工具数据
with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
    tools = json.load(f)

# 为每个工具添加 FAQ 字段（空列表）
updated_count = 0
for tool in tools:
    if 'faq' not in tool:
        tool['faq'] = []  # 暂时为空，后续填充
        updated_count += 1

# 保存更新后的数据
with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(tools, f, ensure_ascii=False, indent=4)

print(f"✅ 已为 {updated_count} 个工具添加 faq 字段")

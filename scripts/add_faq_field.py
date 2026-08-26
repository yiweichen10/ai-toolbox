#!/usr/bin/env python3
"""为所有工具添加 FAQ 字段"""
import json
import os

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'scripts'))
from data_store import save_tools_batch, save_articles_batch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON_PATH = os.path.join(BASE_DIR, 'data', 'tools.json')

# 读取工具数据
tools = load_all_tools()

# 为每个工具添加 FAQ 字段（空列表）
updated_count = 0
for tool in tools:
    if 'faq' not in tool:
        tool['faq'] = []  # 暂时为空，后续填充
        updated_count += 1

# 保存更新后的数据
save_tools_batch(tools)

print(f"✅ 已为 {updated_count} 个工具添加 faq 字段")

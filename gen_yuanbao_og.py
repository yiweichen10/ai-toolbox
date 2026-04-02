#!/usr/bin/env python3
"""为 tencent-yuanbao 工具生成 OG 图片"""
import sys, json, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gen_seo_images import make_og_image, generate_image

with open(os.path.join(BASE_DIR, 'data', 'tools.json'), 'r', encoding='utf-8') as f:
    tools = json.load(f)

tool = next((t for t in tools if t['slug'] == 'tencent-yuanbao'), None)
if not tool:
    print('未找到 tencent-yuanbao')
    sys.exit(1)

og_path = os.path.join(BASE_DIR, 'images', 'og', 'tencent-yuanbao-og.png')
print(f"为 {tool['name']} 生成 OG 图片...")
og_html = make_og_image(tool, tools)
if generate_image(og_html, og_path):
    print('OG 图片生成成功!')
else:
    print('OG 图片生成失败!')
    sys.exit(1)

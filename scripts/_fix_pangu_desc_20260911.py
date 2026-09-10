# -*- coding: utf-8 -*-
"""修正盘古首句（标题按语义边界收尾），2026-09-11"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from data_store import load_all_tools, save_tool

tools = load_all_tools()
t = next(x for x in tools if x['slug'] == 'pangu')
t['description'] = ("505B 国产开源大模型免费下载。华为盘古 2.0 旗舰 openPangu-2.0-Pro 支持 512K 超长上下文，"
                    "昇腾原生优化，权重可商用，也能经华为云 MaaS 按 Token 调用（约 3.2 元/百万输入），"
                    "企业还可私有化部署行业模型。")
t['verified_description'] = t['description']
save_tool(t)
print("OK 首句已更新")
print("new first sentence:", t['description'].split('。')[0])

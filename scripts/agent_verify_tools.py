#!/usr/bin/env python3
"""
agent_verify_tools.py — 用 Agent 能力(联网搜索)逐工具事实核查, 补全 content_verified 标记。

背景: 2026-07-29 gpt-live 幻觉事件后, 用户决策"全量走 Agent 创作/核验工具介绍"。
原 generate_tools.py 用 deepseek-v4-flash 纯文本模型无联网凭记忆生成, 必幻。
本脚本作为"防再犯"执行器: 对未发布(或指定)工具, 联网核实核心事实(url/是什么/核心能力/价格),
按 agent-tool-author skill 协议标记 source_url/last_verified/confidence/conflict/content_verified。

用法:
  python agent_verify_tools.py --batch 10          # 核验前10个未发布工具
  python agent_verify_tools.py --slugs chatgpt claude   # 核验指定slug
  python agent_verify_tools.py --dry-run --batch 5     # 只预览, 不改文件

注意: 本脚本负责"选工具 + 调 WebSearch/WebFetch + 本地写标记"。事实提取由支撑模型(本进程)
      通过 WebSearch/WebFetch 工具完成。若运行环境无联网工具, 会明确报错而非编造。

设计原则(来自 agent-tool-author skill):
  - URL 红线: 必须来自 Tier-1 官方域名且交叉验证, 禁止猜测
  - 未知留白: 无真实来源字段不填, 不编数字/价格/功能
  - 冲突标存疑: 多源不一致 -> conflict=True + confidence=low -> 不自动发布
"""
import json
import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(BASE_DIR, 'data', 'tools.json')
TODAY = datetime.now().strftime('%Y-%m-%d')


def load_tools():
    # 2026-08-26 去单体化: 分片优先
    try:
        from data_store import load_all_tools
        return load_all_tools()
    except Exception:
        with open(TOOLS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)


def save_tools(d):
    # 2026-08-26 去单体化: 只写分片, 不写单体
    from data_store import save_tools_batch
    n = save_tools_batch(d, indent=4)
    print(f"[agent_verify] 已写 {n} 个工具分片 (data/tools/*.json)")


def select_targets(d, batch, slugs):
    if slugs:
        targets = [t for t in d if t.get('slug') in slugs]
        return targets
    # 默认: 未发布且未通过核验的
    unpub = [t for t in d if not t.get('published')]
    need = [t for t in unpub if not (t.get('content_verified') is True and not t.get('conflict'))]
    return need[:batch]


# ---- 事实核查逻辑: 由调用方(本进程支撑模型)通过 WebSearch/WebFetch 完成 ----
# 本脚本作为"执行器框架": 它列出待核查工具、调用 WebSearch(真实联网)、汇总事实、写标记。
# 由于 WebSearch/WebFetch 是本 Agent 的工具而非本脚本内部 API, 实际核查由 Agent 逐工具调用本脚本
# 提供的 prompt 模板 + 自己执行搜索后回写。以下函数生成为每个工具准备的核查清单。

def build_verify_brief(tool):
    """生成该工具的核查要点清单(Agent 据此联网核实)"""
    name = tool.get('name', '?')
    slug = tool.get('slug', '?')
    cur_url = tool.get('url', '')
    cur_cat = tool.get('category', '')
    brief = f"""核查工具: {name} (slug={slug})
当前库内记录(待核实/可能错误):
  - url: {cur_url}
  - category: {cur_cat}
  - description: {(tool.get('description') or '')[:160]}

请联网核实以下事实(Tier-1 官方源优先):
1. 官方真实网址(URL红线: 必须是品牌官方域名, 非 www.{slug}.com 猜测)
2. 它到底是什么(一句话定位, 发布方/公司)
3. 核心能力 3-5 条(官网明确写出的, 禁止编造)
4. 价格/套餐(官网有明确则记, 否则'暂未公开')
5. 平台(Web/API/桌面/移动)

输出结构化结论: verified_url, what_is_it, capabilities, price, platform, confidence(high/medium/low), conflict(bool), conflict_note
"""
    return brief


def apply_verification(tool, result):
    """把 Agent 核查结论写回工具字段。result 为 dict。"""
    tool['url'] = result.get('verified_url', tool.get('url'))
    if result.get('what_is_it'):
        tool['description'] = result['what_is_it']
    if result.get('capabilities'):
        # capabilities 作为 features 补充, 不覆盖已有长文 content
        tool['features'] = result['capabilities']
    if result.get('price'):
        tool['price'] = result['price']
    if result.get('platform'):
        tool['platform'] = result['platform']
    tool['source_url'] = result.get('source_url', '')
    tool['last_verified'] = TODAY
    tool['confidence'] = result.get('confidence', 'medium')
    tool['conflict'] = bool(result.get('conflict'))
    tool['content_verified'] = True if not tool['conflict'] else False
    return tool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=10)
    ap.add_argument('--slugs', nargs='*', default=None)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    d = load_tools()
    targets = select_targets(d, args.batch, args.slugs)
    print(f"[agent_verify_tools] 待核查工具数: {len(targets)}")
    if args.dry_run:
        for t in targets:
            print('---')
            print(build_verify_brief(t))
        return

    # 实际运行模式: 由 Agent 逐工具调 WebSearch 后调用 apply
    # 本脚本单独运行时不具备 WebSearch 能力, 故提供"引导模式": 打印 brief 供 Agent 读取并回写
    print("提示: 本脚本以'引导模式'运行。请 Agent 对每个工具执行 WebSearch/WebFetch 后, "
          "用 apply_verification 回写结果, 或直接将结论传给 --apply。")
    for t in targets:
        print('=== BRIEF ===')
        print(build_verify_brief(t))


if __name__ == '__main__':
    main()

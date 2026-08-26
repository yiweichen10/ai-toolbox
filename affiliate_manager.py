#!/usr/bin/env python3
"""
AI工具推广链接管理工具
======================
功能：
  1. 读取中英文站所有工具数据
  2. 提供 Web 界面管理推广链接
  3. 保存到 affiliate_links.json
  4. 构建时自动替换官网链接为推广链接

用法：
  python affiliate_manager.py              # 启动 Web 管理界面 (http://localhost:8899)
  python affiliate_manager.py --export     # 导出 affiliate_links.json 模板
  python affiliate_manager.py --stats      # 查看统计信息
"""

import json
import os
import sys
import shutil
import http.server
import urllib.parse
from pathlib import Path

# === 路径配置 ===
BASE_DIR = Path(__file__).parent
ZH_TOOLS = BASE_DIR / "data" / "tools.json"
EN_TOOLS = BASE_DIR.parent / "seo-site-en" / "data" / "tools_en.json"
AFFILIATE_FILE = BASE_DIR / "data" / "affiliate_links.json"

# === 标题定位引擎（用于预览"自动生成"的 positioning，失败则降级）===
sys.path.insert(0, str(BASE_DIR / "scripts"))
try:
    from seo_title_helper import gen_positioning as _gen_positioning
except Exception:
    _gen_positioning = None

# positioning 字段写入上限（与 seo_title_helper.gen_positioning 的 explicit[:30] 对齐）
POSITIONING_MAX = 30

# === 已知有联盟计划的AI工具 ===
KNOWN_AFFILIATE_PROGRAMS = {
    # slug: { program_name, commission, signup_url, notes }
    "jasper-ai": {
        "program": "Jasper Affiliate Program",
        "commission": "25% recurring",
        "signup": "https://www.jasper.ai/affiliate",
        "notes": "高佣金，持续分成"
    },
    "copy-ai": {
        "program": "Copy.ai Affiliate Program",
        "commission": "45% recurring",
        "signup": "https://www.copy.ai/affiliate",
        "notes": "佣金比例高"
    },
    "writesonic": {
        "program": "Writesonic Affiliate Program",
        "commission": "30% recurring",
        "signup": "https://writesonic.com/affiliate",
        "notes": ""
    },
    "rytr": {
        "program": "Rytr Affiliate Program",
        "commission": "30% recurring",
        "signup": "https://rytr.me/affiliate",
        "notes": ""
    },
    "frase": {
        "program": "Frase Affiliate Program",
        "commission": "30% recurring",
        "signup": "https://frase.io/affiliate",
        "notes": "SEO内容工具"
    },
    "anyword": {
        "program": "Anyword Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://anyword.com/affiliate",
        "notes": ""
    },
    "surfer-seo": {
        "program": "Surfer SEO Affiliate Program",
        "commission": "25% recurring",
        "signup": "https://surferseo.com/affiliate",
        "notes": "SEO优化工具"
    },
    "ink-for-all": {
        "program": "INK Affiliate Program",
        "commission": "30% recurring",
        "signup": "https://inkforall.com/affiliate",
        "notes": ""
    },
    "pictory": {
        "program": "Pictory Affiliate Program",
        "commission": "15% recurring",
        "signup": "https://pictory.ai/affiliate",
        "notes": "AI视频生成"
    },
    "synthesia": {
        "program": "Synthesia Affiliate Program",
        "commission": "20% one-time",
        "signup": "https://www.synthesia.io/affiliate",
        "notes": "AI数字人视频"
    },
    "framer": {
        "program": "Framer Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://www.framer.com/affiliate",
        "notes": "网页设计工具"
    },
    "webflow": {
        "program": "Webflow Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://webflow.com/affiliates",
        "notes": ""
    },
    "notion-ai": {
        "program": "Notion Affiliate Program",
        "commission": "50% one-time",
        "signup": "https://www.notion.com/affiliates",
        "notes": "一次性佣金"
    },
    "systeme-io": {
        "program": "Systeme.io Affiliate Program",
        "commission": "50% recurring",
        "signup": "https://systeme.io/affiliate",
        "notes": "超高佣金率"
    },
    "beehiiv": {
        "program": "Beehiiv Affiliate Program",
        "commission": "50% recurring",
        "signup": "https://www.beehiiv.com/affiliate",
        "notes": "Newsletter平台"
    },
    "convertkit": {
        "program": "ConvertKit Affiliate Program",
        "commission": "30% recurring",
        "signup": "https://convertkit.com/affiliates",
        "notes": "邮件营销"
    },
    "semrush": {
        "program": "Semrush Affiliate Program",
        "commission": "$200 CPA / 40% recurring",
        "signup": "https://www.semrush.com/affiliate/",
        "notes": "SEO工具，佣金高"
    },
    "grammarly": {
        "program": "Grammarly Affiliate Program",
        "commission": "$20-25 CPA",
        "signup": "https://www.grammarly.com/affiliates",
        "notes": "写作辅助"
    },
    "wordtune": {
        "program": "Wordtune Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://www.wordtune.com/affiliate",
        "notes": ""
    },
    "elementor": {
        "program": "Elementor Affiliate Program",
        "commission": "50% recurring",
        "signup": "https://elementor.com/affiliates/",
        "notes": "WordPress页面构建器"
    },
    "linkassistant": {
        "program": "SEO PowerSuite Affiliate",
        "commission": "33% recurring",
        "signup": "https://www.link-assistant.com/affiliate.html",
        "notes": ""
    },
    "seedprod": {
        "program": "SeedProd Affiliate",
        "commission": "20% recurring",
        "signup": "https://www.seedprod.com/affiliate/",
        "notes": ""
    },
    "opera-aria-ai": {
        "program": "Opera Affiliate",
        "commission": "varies",
        "signup": "https://www.opera.com/affiliate",
        "notes": ""
    },
    "buffer": {
        "program": "Buffer Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://buffer.com/affiliates",
        "notes": "社交媒体管理"
    },
    "simplified": {
        "program": "Simplified Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://simplified.com/affiliate",
        "notes": ""
    },
    "opencat": {
        "program": "OpenCat Affiliate",
        "commission": "varies",
        "signup": "",
        "notes": "需确认"
    },
    "kaiber-ai": {
        "program": "Kaiber Affiliate",
        "commission": "varies",
        "signup": "",
        "notes": "AI视频生成"
    },
    "tensor-art": {
        "program": "Tensor.art Referral",
        "commission": "varies",
        "signup": "",
        "notes": "AI绘画社区"
    },
    "midjourneyscanner": {
        "program": "Midjourney Scanner Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "openrouter": {
        "program": "OpenRouter Referral",
        "commission": "10% one-time",
        "signup": "https://openrouter.ai/referrals",
        "notes": "API聚合平台"
    },
    "unbounce": {
        "program": "Unbounce Affiliate Program",
        "commission": "20% recurring",
        "signup": "https://unbounce.com/affiliates",
        "notes": "落地页工具"
    },
    "zapier": {
        "program": "Zapier Affiliate Program",
        "commission": "15% recurring",
        "signup": "https://zapier.com/affiliates",
        "notes": "自动化工具"
    },
    "otter-ai": {
        "program": "Otter.ai Referral",
        "commission": "varies",
        "signup": "",
        "notes": "会议记录"
    },
    "fireflies-ai": {
        "program": "Fireflies.ai Referral",
        "commission": "varies",
        "signup": "",
        "notes": "会议AI"
    },
    "jupitrr": {
        "program": "Jupitrr Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "glitter-ai": {
        "program": "Glitter.ai Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "flair-ai": {
        "program": "Flair.ai Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "aider": {
        "program": "Aider Referral",
        "commission": "N/A",
        "signup": "",
        "notes": "开源项目，无联盟"
    },
    "respeecher": {
        "program": "Respeecher Referral",
        "commission": "varies",
        "signup": "",
        "notes": "AI语音转换"
    },
    "agentbrowser": {
        "program": "AgentBrowser Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "trypear-ai": {
        "program": "PearAI Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
    "qoder": {
        "program": "Qoder Referral",
        "commission": "varies",
        "signup": "",
        "notes": ""
    },
}


def load_tools():
    """加载中英文站工具数据 (2026-08-26 中文站去单体化: 分片优先)"""
    tools = []
    # 中文站 (真源为分片 data/tools/*.json)
    if ZH_TOOLS.is_dir() or (str(ZH_TOOLS).endswith('tools.json') and ZH_TOOLS.parent.joinpath('tools').is_dir()):
        try:
            import sys as _sys
            _sys.path.insert(0, str(BASE_DIR / "scripts"))
            from data_store import load_all_tools
            zh_data = load_all_tools()
        except Exception:
            zh_data = json.load(open(ZH_TOOLS, encoding='utf-8')) if ZH_TOOLS.exists() else []
        for t in zh_data:
            tools.append({
                "slug": t.get("slug", ""),
                "name": t.get("name", ""),
                "url": t.get("url", ""),
                "category": t.get("category", ""),
                "description": t.get("description", ""),
                "positioning": t.get("positioning", ""),
                "site": "zh"
            })
    # 英文站
    if EN_TOOLS.exists():
        with open(EN_TOOLS, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        for t in en_data:
            tools.append({
                "slug": t.get("slug", ""),
                "name": t.get("name", ""),
                "url": t.get("url", ""),
                "category": t.get("category", ""),
                "description": t.get("description", ""),
                "positioning": t.get("positioning", ""),
                "site": "en"
            })
    return tools


def load_affiliate_links():
    """加载已有的推广链接"""
    if AFFILIATE_FILE.exists():
        with open(AFFILIATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_affiliate_links(data):
    """保存推广链接"""
    AFFILIATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AFFILIATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_tools_with_affiliate():
    """获取所有工具，附带推广链接和联盟计划信息"""
    tools = load_tools()
    affiliates = load_affiliate_links()
    
    result = []
    for t in tools:
        key = f"{t['site']}:{t['slug']}"
        affiliate_url = affiliates.get(key, {}).get("url", "")
        affiliate_info = KNOWN_AFFILIATE_PROGRAMS.get(t["slug"], None)
        # 自动生成的定位预览（去掉显式覆盖，反映通用引擎真实输出）
        auto_pos = ""
        if _gen_positioning:
            try:
                _t = dict(t)
                _t.pop("positioning", None)
                auto_pos = _gen_positioning(_t)
            except Exception:
                auto_pos = ""

        result.append({
            **t,
            "affiliate_url": affiliate_url,
            "has_affiliate": bool(affiliate_url),
            "known_program": affiliate_info is not None,
            "program_info": affiliate_info,
            "positioning": t.get("positioning", "") or "",
            "auto_positioning": auto_pos
        })
    return result


def compute_auto_positioning(tool):
    """计算通用引擎对某个工具的自动定位（供前端预览）。"""
    if not _gen_positioning:
        return ""
    try:
        _t = dict(tool)
        _t.pop("positioning", None)
        return _gen_positioning(_t)
    except Exception:
        return ""


def save_positioning_for_site(site, updates):
    """将 {slug: positioning_text} 写回对应数据文件。
    positioning_text 为空字符串表示删除该字段（删）。
    写前自动备份原文件。返回成功条数。
    2026-08-26 中文站去单体化: 写分片 data/tools/<slug>.json
    """
    if site == "zh":
        fpath = ZH_TOOLS
        shard_dir = BASE_DIR / "data" / "tools"
        use_shards = shard_dir.is_dir()
    else:
        fpath = EN_TOOLS
        shard_dir = None
        use_shards = False
    if not use_shards and not fpath.exists():
        raise FileNotFoundError(f"数据文件不存在: {fpath}")

    saved = 0
    if use_shards:
        # 写分片: 逐 slug 定位
        import sys as _sys
        _sys.path.insert(0, str(BASE_DIR / "scripts"))
        from data_store import save_tool
        for slug, val in updates.items():
            sp = shard_dir / f"{slug}.json"
            if not sp.exists():
                continue
            tool = json.loads(sp.read_text(encoding="utf-8"))
            if val and val.strip():
                tool["positioning"] = val.strip()[:POSITIONING_MAX]
            else:
                tool.pop("positioning", None)
            save_tool(tool, indent=2)
            saved += 1
        return saved

    # 单体/英文站旧路径
    bak = fpath.with_name(fpath.stem + ".json.positioning.bak")
    shutil.copy2(fpath, bak)

    data = json.loads(fpath.read_text(encoding="utf-8"))
    for slug, val in updates.items():
        tool = next((t for t in data if t.get("slug") == slug), None)
        if tool is None:
            continue
        if val and val.strip():
            tool["positioning"] = val.strip()[:POSITIONING_MAX]
        else:
            # 空值 = 删除字段
            tool.pop("positioning", None)
        saved += 1

    fpath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return saved


# === Web 界面 ===
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI工具推广链接管理</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #0f1117; color: #e0e0e0; }
.header { background: #1a1d27; padding: 20px 30px; border-bottom: 1px solid #2a2d37; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
.header h1 { font-size: 20px; color: #fff; }
.header h1 span { color: #4a9eff; }
.stats { display: flex; gap: 20px; font-size: 13px; }
.stat-item { background: #2a2d37; padding: 6px 14px; border-radius: 6px; }
.stat-item strong { color: #4a9eff; font-size: 16px; }
.stat-item.aff strong { color: #4ade80; }
.stat-item.known strong { color: #fbbf24; }
.controls { padding: 16px 30px; background: #161821; border-bottom: 1px solid #2a2d37; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.controls input[type="text"] { background: #1a1d27; border: 1px solid #2a2d37; color: #e0e0e0; padding: 8px 14px; border-radius: 6px; font-size: 14px; width: 300px; }
.controls input:focus { outline: none; border-color: #4a9eff; }
.controls select { background: #1a1d27; border: 1px solid #2a2d37; color: #e0e0e0; padding: 8px 14px; border-radius: 6px; font-size: 14px; }
.btn { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 14px; transition: all 0.2s; }
.btn-save { background: #4a9eff; color: #fff; }
.btn-save:hover { background: #3a8eef; }
.btn-export { background: #4ade80; color: #0f1117; }
.btn-export:hover { background: #3ace70; }
.btn-secondary { background: #2a2d37; color: #e0e0e0; }
.btn-secondary:hover { background: #3a3d47; }
.table-wrap { padding: 0 30px 30px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #1a1d27; padding: 12px 10px; text-align: left; font-weight: 600; color: #8b8d97; border-bottom: 1px solid #2a2d37; position: sticky; top: 0; }
td { padding: 10px; border-bottom: 1px solid #1e212b; vertical-align: middle; }
tr:hover { background: #161821; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-zh { background: #4a9eff20; color: #4a9eff; }
.badge-en { background: #4ade8020; color: #4ade80; }
.badge-aff { background: #4ade8020; color: #4ade80; }
.badge-known { background: #fbbf2420; color: #fbbf24; }
.badge-none { background: #6b728020; color: #6b7280; }
.affiliate-input { background: #1a1d27; border: 1px solid #2a2d37; color: #e0e0e0; padding: 6px 10px; border-radius: 4px; font-size: 12px; width: 100%; min-width: 300px; }
.affiliate-input:focus { outline: none; border-color: #4a9eff; }
.affiliate-input.has-value { border-color: #4ade80; }
.pos-input { background: #1a1d27; border: 1px solid #2a2d37; color: #e0e0e0; padding: 6px 10px; border-radius: 4px; font-size: 12px; width: 100%; min-width: 220px; }
.pos-input:focus { outline: none; border-color: #fbbf24; }
.pos-input.has-value { border-color: #fbbf24; }
.pos-auto { font-size: 11px; color: #6b7280; margin-top: 3px; }
.pos-auto b { color: #8b8d97; font-weight: 500; }
.tool-name { font-weight: 600; color: #fff; }
.tool-slug { color: #6b7280; font-size: 11px; }
.tool-url { color: #6b7280; font-size: 11px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.program-info { font-size: 11px; color: #fbbf24; }
.program-info a { color: #fbbf24; text-decoration: underline; }
.toast { position: fixed; bottom: 30px; right: 30px; padding: 14px 24px; border-radius: 8px; font-size: 14px; z-index: 999; opacity: 0; transition: opacity 0.3s; }
.toast.show { opacity: 1; }
.toast-success { background: #4ade80; color: #0f1117; }
.toast-error { background: #ef4444; color: #fff; }
.filter-info { font-size: 12px; color: #6b7280; margin-left: auto; }
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; justify-content: center; align-items: center; }
.modal-overlay.show { display: flex; }
.modal { background: #1a1d27; border-radius: 12px; padding: 30px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal h2 { margin-bottom: 16px; color: #fff; }
.modal-close { float: right; cursor: pointer; color: #6b7280; font-size: 24px; }
.modal-close:hover { color: #fff; }
.guide-list { list-style: none; }
.guide-list li { padding: 10px 0; border-bottom: 1px solid #2a2d37; color: #c0c0c0; }
.guide-list li strong { color: #4a9eff; }
.bulk-bar { background: #1a2d1a; padding: 12px 30px; border-bottom: 1px solid #2a5a2a; display: none; align-items: center; gap: 12px; }
.bulk-bar.show { display: flex; }
.tabs { display: flex; gap: 0; background: #161821; border-bottom: 1px solid #2a2d37; padding: 0 30px; }
.tab { background: transparent; border: none; color: #8b8d97; padding: 14px 24px; font-size: 15px; font-weight: 600; cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.2s; display: flex; align-items: center; gap: 8px; }
.tab:hover { color: #e0e0e0; }
.tab.active { color: #fff; border-bottom-color: #4a9eff; }
.tab-count { background: #2a2d37; color: #8b8d97; font-size: 12px; padding: 1px 8px; border-radius: 10px; font-weight: 500; }
.tab.active .tab-count { background: #4a9eff; color: #fff; }
.tab-zh.active { border-bottom-color: #4a9eff; }
.tab-en.active { border-bottom-color: #4ade80; }
.tab-en.active .tab-count { background: #4ade80; color: #0f1117; }
</style>
</head>
<body>

<div class="header">
    <h1>AI工具 <span>推广链接</span> 管理台</h1>
    <div class="stats">
        <div class="stat-item">总工具 <strong id="stat-total">0</strong></div>
        <div class="stat-item aff">已设推广 <strong id="stat-aff">0</strong></div>
        <div class="stat-item known">有联盟计划 <strong id="stat-known">0</strong></div>
        <div class="stat-item" style="color:#fbbf24">已设定位 <strong id="stat-pos">0</strong></div>
    </div>
</div>

<div class="tabs">
    <button class="tab tab-zh active" data-site="zh" onclick="switchTab(this)">🇨🇳 中文站 <span class="tab-count" id="tab-zh">0</span></button>
    <button class="tab tab-en" data-site="en" onclick="switchTab(this)">🌐 英文站 <span class="tab-count" id="tab-en">0</span></button>
</div>

<div class="controls">
    <input type="text" id="search" placeholder="搜索工具名/slug/URL..." oninput="filterTable()">
    <select id="filter-aff" onchange="filterTable()">
        <option value="">全部状态</option>
        <option value="has">已设推广链接</option>
        <option value="none">未设推广链接</option>
        <option value="known">有联盟计划</option>
        <option value="known-none">有联盟但未设</option>
    </select>
    <button class="btn btn-save" onclick="saveAll()">保存推广链接</button>
    <button class="btn" style="background:#fbbf24;color:#0f1117" onclick="savePositioning()">保存定位</button>
    <button class="btn btn-export" onclick="exportJson()">导出 JSON</button>
    <button class="btn btn-secondary" onclick="showGuide()">使用指南</button>
    <span class="filter-info" id="filter-info"></span>
</div>

<div class="table-wrap">
    <table id="main-table">
        <thead>
        <tr>
            <th width="40">站点</th>
            <th>工具名</th>
            <th>官网链接</th>
            <th>推广链接（可编辑）</th>
            <th>SEO定位 positioning（可编辑）</th>
            <th width="120">联盟计划</th>
            <th width="80">状态</th>
        </tr>
        </thead>
        <tbody id="tbody"></tbody>
    </table>
</div>

<div class="modal-overlay" id="guide-modal">
    <div class="modal">
        <span class="modal-close" onclick="closeGuide()">&times;</span>
        <h2>使用指南</h2>
        <ul class="guide-list">
            <li><strong>1. 添加推广链接</strong>：在"推广链接"列输入框中粘贴你的推广链接，然后点"保存推广链接"。</li>
            <li><strong>2. 联盟计划标记</strong>：黄色"有"标记表示该工具有已知的联盟计划，点击可查看注册链接。绿色"有"表示你已设置推广链接。</li>
            <li><strong>3. 数据存储</strong>：推广链接保存在 <code>data/affiliate_links.json</code> 中，不会修改原始 tools.json。</li>
            <li><strong>4. SEO定位(positioning) 增删改</strong>：在"SEO定位"列直接编辑。留空=用通用引擎自动生成（下方"自动:"显示当前自动值）；填入=手动覆盖标题尾；清空已填的值=删除覆盖、回到自动。<b>增</b>（空→填）、<b>改</b>（改值）、<b>删</b>（清空）都覆盖。上限 30 字。</li>
            <li><strong>5. 定位何时用</strong>：当通用标题引擎对某个工具的首句截断失真（如品牌名（副标）——定位 结构、或尾部才是核心价值）时，在此手动写干净的标题尾，重建站点后即生效。</li>
            <li><strong>6. 定位数据落点</strong>：定位直接写入各工具的 <code>data/tools.json</code>（中文站）/ 英文站数据文件，写前自动备份。保存后需<strong>重新构建站点</strong>标题才会更新。</li>
            <li><strong>7. 筛选技巧</strong>：选"有联盟但未设"可快速找到你能赚钱但还没挂链接的工具。</li>
            <li><strong>8. rel 标签</strong>：推广链接会自动加 <code>rel="nofollow noopener sponsored"</code>，符合 SEO 规范。</li>
        </ul>
    </div>
</div>

<div class="toast" id="toast"></div>

<script>
let allTools = [];
let changes = {};
let posChanges = {};     // positioning 待保存覆盖（与 changes 平行）
let currentSite = 'zh';  // 当前选中的站点标签页

async function loadData() {
    const resp = await fetch('/api/tools');
    allTools = await resp.json();
    renderTable(allTools);
    updateStats();
}

function updateStats() {
    const total = allTools.length;
    const aff = allTools.filter(t => t.affiliate_url).length;
    const known = allTools.filter(t => t.known_program).length;
    const posCount = allTools.filter(t => {
        const key = t.site + ':' + t.slug;
        const pending = posChanges[key];
        const cur = pending !== undefined ? pending : t.positioning;
        return cur && cur.trim();
    }).length;
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-aff').textContent = aff;
    document.getElementById('stat-known').textContent = known;
    document.getElementById('stat-pos').textContent = posCount;
    const zhCount = allTools.filter(t => t.site === 'zh').length;
    const enCount = allTools.filter(t => t.site === 'en').length;
    document.getElementById('tab-zh').textContent = zhCount;
    document.getElementById('tab-en').textContent = enCount;
}

function renderTable(tools) {
    const tbody = document.getElementById('tbody');
    tbody.innerHTML = tools.map(t => {
        const key = t.site + ':' + t.slug;
        // 优先显示未保存的编辑内容（切换tab不丢失）
        const pendingVal = changes[key] !== undefined ? changes[key] : t.affiliate_url;
        const hasValue = pendingVal ? 'has-value' : '';
        // positioning 覆盖值（优先未保存编辑）
        const pendingPos = posChanges[key] !== undefined ? posChanges[key] : (t.positioning || '');
        const posHasValue = pendingPos ? 'has-value' : '';
        const knownBadge = t.known_program
            ? `<span class="badge badge-known" title="${t.program_info ? t.program_info.commission : ''}">有</span>`
            : '<span class="badge badge-none">-</span>';
        const programInfo = t.program_info
            ? `<div class="program-info">${t.program_info.commission}${t.program_info.signup ? ' · <a href="' + t.program_info.signup + '" target="_blank">注册</a>' : ''}</div>`
            : '';
        const statusBadge = t.affiliate_url
            ? '<span class="badge badge-aff">已设</span>'
            : '<span class="badge badge-none">未设</span>';
        // 自动生成的定位预览（有覆盖值时显示对比）
        const autoLine = t.auto_positioning
            ? `<div class="pos-auto"><b>自动:</b> ${escHtml(t.auto_positioning)}</div>`
            : '';
        return `<tr data-key="${key}">
            <td><span class="badge badge-${t.site}">${t.site === 'zh' ? '中文' : 'EN'}</span></td>
            <td>
                <div class="tool-name">${escHtml(t.name)}</div>
                <div class="tool-slug">${t.slug}</div>
            </td>
            <td><div class="tool-url" title="${escHtml(t.url)}">${escHtml(t.url)}</div></td>
            <td>
                <input type="text" class="affiliate-input ${hasValue}"
                    value="${escAttr(pendingVal)}"
                    placeholder="粘贴推广链接..."
                    data-key="${key}"
                    data-original="${escAttr(t.affiliate_url)}"
                    oninput="onInputChange(this)">
                ${programInfo}
            </td>
            <td>
                <input type="text" class="pos-input ${posHasValue}"
                    value="${escAttr(pendingPos)}"
                    placeholder="留空=用自动生成"
                    data-key="${key}"
                    data-original="${escAttr(t.positioning || '')}"
                    oninput="onPosInputChange(this)">
                ${autoLine}
            </td>
            <td>${knownBadge}</td>
            <td>${statusBadge}</td>
        </tr>`;
    }).join('');
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escAttr(s) {
    if (!s) return '';
    return s.replace(/"/g, '&quot;');
}

function onInputChange(input) {
    const key = input.dataset.key;
    const val = input.value.trim();
    const original = input.dataset.original;
    if (val !== original) {
        changes[key] = val;
        input.classList.add('has-value');
    } else {
        delete changes[key];
        if (!val) input.classList.remove('has-value');
    }
}

function onPosInputChange(input) {
    const key = input.dataset.key;
    const val = input.value.trim();
    const original = (input.dataset.original || '').trim();
    // 超过 30 字提示（引擎会截断到 30）
    if (val.length > 30) {
        input.style.borderColor = '#ef4444';
    } else {
        input.style.borderColor = '';
    }
    if (val !== original) {
        posChanges[key] = val;
        input.classList.add('has-value');
    } else {
        delete posChanges[key];
        if (!val) input.classList.remove('has-value');
    }
}

function switchTab(el) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    currentSite = el.dataset.site;
    document.getElementById('search').value = '';
    filterTable();
}

function filterTable() {
    const search = document.getElementById('search').value.toLowerCase();
    const site = currentSite;
    const aff = document.getElementById('filter-aff').value;

    let filtered = allTools.filter(t => {
        if (site && t.site !== site) return false;
        if (search) {
            const s = (t.name + ' ' + t.slug + ' ' + t.url).toLowerCase();
            if (!s.includes(search)) return false;
        }
        if (aff === 'has' && !t.affiliate_url) return false;
        if (aff === 'none' && t.affiliate_url) return false;
        if (aff === 'known' && !t.known_program) return false;
        if (aff === 'known-none' && !(t.known_program && !t.affiliate_url)) return false;
        return true;
    });

    renderTable(filtered);
    const siteLabel = site === 'zh' ? '中文站' : '英文站';
    document.getElementById('filter-info').textContent = `${siteLabel} 显示 ${filtered.length} 条`;
}

async function saveAll() {
    // 只保存当前站点的待保存更改
    const siteChanges = {};
    for (const [key, val] of Object.entries(changes)) {
        if (key.startsWith(currentSite + ':')) {
            siteChanges[key] = val;
        }
    }

    if (Object.keys(siteChanges).length === 0) {
        const otherCount = Object.keys(changes).length;
        if (otherCount > 0) {
            showToast(`当前站点无更改（其他站点有 ${otherCount} 条未保存）`, 'error');
        } else {
            showToast('没有需要保存的更改', 'error');
        }
        return;
    }

    const resp = await fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(siteChanges)
    });
    const result = await resp.json();

    if (result.success) {
        // 更新本地数据 + 清除当前站点的待保存项
        for (const [key, val] of Object.entries(siteChanges)) {
            const [site, slug] = key.split(':');
            const tool = allTools.find(t => t.site === site && t.slug === slug);
            if (tool) {
                tool.affiliate_url = val;
            }
            delete changes[key];
        }
        updateStats();
        filterTable();
        const siteLabel = currentSite === 'zh' ? '中文站' : '英文站';
        showToast(`已保存 ${result.saved} 条推广链接（${siteLabel}）`, 'success');
    } else {
        showToast('保存失败: ' + result.error, 'error');
    }
}

function exportJson() {
    window.open('/api/export', '_blank');
}

async function savePositioning() {
    // 收集当前站点待保存的 positioning 更改
    const updates = {};
    for (const [key, val] of Object.entries(posChanges)) {
        if (key.startsWith(currentSite + ':')) {
            const slug = key.split(':').slice(1).join(':');  // slug 可能含冒号
            updates[slug] = val;
        }
    }
    if (Object.keys(updates).length === 0) {
        showToast('没有需要保存的定位更改', 'error');
        return;
    }
    const resp = await fetch('/api/save-positioning', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ site: currentSite, updates: updates })
    });
    const result = await resp.json();
    if (result.success) {
        // 同步到本地数据 + 清除当前站点待保存项
        for (const [key, val] of Object.entries(updates)) {
            const tool = allTools.find(t => t.site === currentSite && t.slug === (key.split(':').slice(1).join(':')));
            if (tool) {
                const fullKey = currentSite + ':' + key;
                tool.positioning = val ? val : '';
                delete posChanges[fullKey];
            }
        }
        updateStats();
        filterTable();
        const siteLabel = currentSite === 'zh' ? '中文站' : '英文站';
        showToast(`已保存 ${result.saved} 条定位覆盖（${siteLabel}）。保存后需重新构建站点才会生效。`, 'success');
    } else {
        showToast('保存失败: ' + (result.error || '未知错误'), 'error');
    }
}

function showGuide() {
    document.getElementById('guide-modal').classList.add('show');
}
function closeGuide() {
    document.getElementById('guide-modal').classList.remove('show');
}

function showToast(msg, type) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast show toast-' + type;
    setTimeout(() => toast.className = 'toast', 3000);
}

// 键盘快捷键
document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveAll();
    }
    if (e.key === 'Escape') {
        closeGuide();
    }
});

loadData();
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        elif self.path == '/api/tools':
            tools = get_all_tools_with_affiliate()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(tools, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/export':
            data = load_affiliate_links()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename=affiliate_links.json')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/save':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            changes = json.loads(body.decode('utf-8'))

            data = load_affiliate_links()
            saved = 0
            for key, val in changes.items():
                if val:
                    if key not in data:
                        data[key] = {}
                    data[key]["url"] = val
                    data[key]["updated"] = "2026-07-27"
                    saved += 1
                else:
                    # 空值 = 删除
                    data.pop(key, None)
                    saved += 1

            save_affiliate_links(data)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "saved": saved}).encode('utf-8'))

        elif self.path == '/api/save-positioning':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))
            # payload: { "site": "zh", "updates": { slug: text } }
            site = payload.get("site", "zh")
            updates = payload.get("updates", {})
            try:
                saved = save_positioning_for_site(site, updates)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "saved": saved,
                    "max": POSITIONING_MAX
                }).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": str(e)
                }).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def show_stats():
    """命令行统计"""
    tools = get_all_tools_with_affiliate()
    zh_tools = [t for t in tools if t['site'] == 'zh']
    en_tools = [t for t in tools if t['site'] == 'en']
    has_aff = [t for t in tools if t['affiliate_url']]
    known = [t for t in tools if t['known_program']]
    known_no_aff = [t for t in tools if t['known_program'] and not t['affiliate_url']]

    print(f"\n{'='*60}")
    print(f"  AI工具推广链接统计")
    print(f"{'='*60}")
    print(f"  中文站工具: {len(zh_tools)}")
    print(f"  英文站工具: {len(en_tools)}")
    print(f"  总计: {len(tools)}")
    print(f"  已设推广链接: {len(has_aff)}")
    print(f"  有联盟计划: {len(known)}")
    print(f"  有联盟但未设: {len(known_no_aff)}")
    print(f"{'='*60}")

    if known_no_aff:
        print(f"\n  ⚡ 可立即挂推广链接的工具 ({len(known_no_aff)}):")
        for t in known_no_aff:
            commission = t['program_info']['commission'] if t['program_info'] else ''
            print(f"    [{t['site'].upper()}] {t['name']} ({t['slug']}) - {commission}")
    print()


def export_template():
    """导出模板"""
    tools = load_tools()
    template = {}
    for t in tools:
        key = f"{t['site']}:{t['slug']}"
        info = KNOWN_AFFILIATE_PROGRAMS.get(t['slug'])
        template[key] = {
            "url": "",
            "official_url": t['url'],
            "name": t['name'],
            "has_program": info is not None,
            "program": info['program'] if info else "",
            "commission": info['commission'] if info else "",
        }
    save_affiliate_links(template)
    print(f"\n已导出模板到: {AFFILIATE_FILE}")
    print(f"共 {len(template)} 条工具记录\n")


def main():
    if '--stats' in sys.argv:
        show_stats()
        return
    if '--export' in sys.argv:
        export_template()
        return

    port = 8899
    server = http.server.HTTPServer(('127.0.0.1', port), Handler)
    print(f"\n  AI工具推广链接管理台")
    print(f"  访问: http://127.0.0.1:{port}")
    print(f"  数据: {AFFILIATE_FILE}")
    print(f"\n  快捷键: Ctrl+S 保存 | ESC 关闭弹窗")
    print(f"  按 Ctrl+C 退出\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
        server.server_close()


if __name__ == '__main__':
    main()

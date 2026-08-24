#!/usr/bin/env python3
"""
audit_orphan_pages.py
=====================
全站入链审计脚本 — 扫描中文站（aitoollab.cn）HTML，统计每页的入链数。

核心逻辑：
1. 遍历 tools/ articles/ compare/ alternatives/ ranking/ dict/ category/ 目录
2. 解析每页 index.html 中的站内 <a href="/.../"> 链接
3. 构建反向链接图（每页被哪些页引用）
4. 输出入链 ≤ 3 的页面清单（markdown + json）
5. CI 对接：0 个「核心页面类型」入链 ≤ 3 即为 pass（exit 0）

用法：
    python3 scripts/audit_orphan_pages.py              # 输出报告
    python3 scripts/audit_orphan_pages.py --ci          # CI 模式（exit 0/1）
    python3 scripts/audit_orphan_pages.py --json        # JSON 输出
    python3 scripts/audit_orphan_pages.py --output report.md  # 写报告文件

参考：scripts/check_internal_links.py
"""

import json
import re
import sys
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SITE_ROOT = Path(__file__).resolve().parent.parent
DOMAIN = "www.aitoollab.cn"

# ── 页面类型定义 ──
PAGE_TYPES = {
    "tools":       {"dir": "tools",       "label": "工具详情页", "core": True},
    "articles":    {"dir": "articles",    "label": "文章页",     "core": True},
    "compare":     {"dir": "compare",     "label": "对比详情页", "core": True},
    "alternatives":{"dir": "alternatives","label": "替代详情页", "core": True},
    "ranking":     {"dir": "ranking",     "label": "排行详情页", "core": True},
    "category":    {"dir": "category",    "label": "分类页",     "core": True},
    "dict":        {"dir": "dict",        "label": "词典页",     "core": False},
}

# 页面类型优先级（用于计算核心 orphan 严重程度）
CORE_TYPES = {k for k, v in PAGE_TYPES.items() if v["core"]}

# ── 工具函数 ──

def _safe_read(filepath: Path) -> str:
    """安全读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _extract_internal_links(html: str) -> list:
    """从 HTML 中提取站内链接目标路径。
    返回: ["/tools/chatgpt/", "/category/ai-chat/", ...]
    """
    links = []
    # 匹配站内 <a href="..."> 链接（排除外部链接、锚点、mailto、js）
    pattern = re.compile(
        r'<a[^>]*href="(/(?:tools|articles|compare|alternatives|ranking|dict|category|quiz|'
        r'author|about|contact|privacy|links|faq|blog)?(?:/[^"]*)?)"',
        re.IGNORECASE
    )
    for m in pattern.finditer(html):
        href = m.group(1)
        if not href:
            continue
        # 排除外部链接（含 ://）、锚点（#）、mailto/javascript
        if href.startswith("http") or href.startswith("//") or "#" in href or href.startswith("javascript"):
            continue
        # 规范化：去掉尾部 index.html，确保以 / 结尾（根路径 / 除外）
        href = re.sub(r'/index\.html$', '/', href)
        if href != "/" and not href.endswith('/'):
            href += '/'
        links.append(href)
    return links


def _get_page_type(url: str) -> str:
    """根据 URL 路径判断页面类型"""
    for ptype, info in PAGE_TYPES.items():
        if url.startswith(f"/{info['dir']}/"):
            return ptype
    if url == "/" or url == "/index.html":
        return "home"
    return "other"


def _page_slug(url: str) -> str:
    """从 URL 提取页面 slug（目录名）"""
    # /tools/chatgpt/ → chatgpt
    parts = [p for p in url.strip("/").split("/") if p]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else ""


# ── 核心逻辑 ──

def collect_all_pages() -> dict:
    """扫描站点所有 HTML 页面。
    返回: {url_path: {"file": Path, "type": str, "slug": str}}
    """
    pages = {}

    for ptype, info in PAGE_TYPES.items():
        dir_path = SITE_ROOT / info["dir"]
        if not dir_path.is_dir():
            continue

        for subdir in dir_path.iterdir():
            if not subdir.is_dir():
                continue
            # 排除 _template 等非内容目录
            if subdir.name.startswith("_") or subdir.name.startswith("."):
                continue
            index_file = subdir / "index.html"
            if not index_file.exists():
                continue

            url = f"/{info['dir']}/{subdir.name}/"
            pages[url] = {
                "file": index_file,
                "type": ptype,
                "slug": subdir.name,
                "label": info["label"],
            }

    # 索引页（文章列表页、根首页等）
    extra_indexes = [
        ("articles", "articles", "文章列表页"),
        ("category", "category", "分类索引页"),
        ("compare", "compare", "对比索引页"),
        ("alternatives", "alternatives", "替代索引页"),
        ("ranking", "ranking", "排行索引页"),
        ("dict", "dict", "词典索引页"),
        ("quiz", "quiz", "答题索引页"),
        ("", "", "首页"),  # /index.html
    ]
    for dir_name, slug, label in extra_indexes:
        if dir_name:
            idx_dir = SITE_ROOT / dir_name
        else:
            idx_dir = SITE_ROOT
        index_file = idx_dir / "index.html"
        if index_file.exists():
            url = f"/{dir_name}/" if dir_name else "/"
            pages[url] = {
                "file": index_file,
                "type": f"{slug}_index" if slug else "home",
                "slug": slug,
                "label": label,
            }

    return pages


def build_link_graph(pages: dict) -> tuple:
    """构建反向链接图。
    返回: (inbound_graph: {url: [source_urls]}, outbound_counts: {url: int})
    """
    inbound = defaultdict(list)     # url → [引用它的页面]
    outbound = defaultdict(int)      # url → 它引用了多少站内页面
    all_page_urls = set(pages.keys())

    for src_url, info in pages.items():
        html = _safe_read(info["file"])
        if not html:
            continue

        links = _extract_internal_links(html)
        outbound[src_url] = len(set(links))

        for target in set(links):
            # 只统计我们已知的页面（排除外部链接和索引页中的动态链接）
            if target in all_page_urls and target != src_url:
                inbound[target].append(src_url)

    return inbound, outbound


def compute_orphan_report(pages: dict, inbound: dict, outbound: dict,
                           threshold: int = 3) -> dict:
    """计算孤儿页报告。
    返回:
    {
        "pass": bool,
        "total_pages": int,
        "orphan_pages": [{"url": str, "type": str, "label": str, "inbound": int, "sources": [...]}],
        "core_orphans": [...],       # 核心页面类型中的孤儿
        "stats": {"by_type": {...}, "total_inbound_links": int, ...}
    }
    """
    orphan_pages = []
    core_orphans = []
    stats_by_type = defaultdict(lambda: {"total": 0, "orphan": 0, "avg_inbound": 0.0})
    total_inbound_sum = 0

    for url, info in pages.items():
        ptype = info["type"]
        in_count = len(inbound.get(url, []))
        sources = inbound.get(url, [])
        total_inbound_sum += in_count

        stats_by_type[ptype]["total"] += 1
        stats_by_type[ptype]["avg_inbound"] += in_count

        if in_count <= threshold:
            entry = {
                "url": url,
                "type": ptype,
                "label": info["label"],
                "slug": info["slug"],
                "inbound": in_count,
                "sources": sources,
            }
            orphan_pages.append(entry)
            stats_by_type[ptype]["orphan"] += 1

            # 判断是否为核心类型
            is_core = False
            for core_type in CORE_TYPES:
                if ptype.startswith(core_type):
                    is_core = True
                    break
            if is_core:
                core_orphans.append(entry)

    # 计算平均入链
    for ptype in stats_by_type:
        t = stats_by_type[ptype]["total"]
        if t > 0:
            stats_by_type[ptype]["avg_inbound"] = round(
                stats_by_type[ptype]["avg_inbound"] / t, 1
            )

    # 按入链数升序排列（最孤儿的排前面）
    orphan_pages.sort(key=lambda x: x["inbound"])
    core_orphans.sort(key=lambda x: x["inbound"])

    total_pages = len(pages)
    avg_inbound_all = round(total_inbound_sum / total_pages, 1) if total_pages > 0 else 0

    return {
        "pass": len(core_orphans) == 0,
        "total_pages": total_pages,
        "threshold": threshold,
        "avg_inbound_all": avg_inbound_all,
        "orphan_pages": orphan_pages,
        "core_orphans": core_orphans,
        "stats_by_type": dict(stats_by_type),
    }


# ── 输出 ──

def format_markdown_report(report: dict) -> str:
    """生成 Markdown 格式报告"""
    lines = []
    lines.append(f"# 站内孤儿页审计报告")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 站点：{DOMAIN}")
    lines.append(f"> 扫描页面总数：{report['total_pages']}")
    lines.append(f"> 平均入链数：{report['avg_inbound_all']}")
    lines.append(f"> 孤儿阈值：≤ {report['threshold']} 条入链")
    lines.append(f"> CI 判定：{'✅ PASS' if report['pass'] else '❌ FAIL — 存在核心类型孤儿页'}")
    lines.append("")

    # 按类型统计
    lines.append("## 按页面类型统计")
    lines.append("| 类型 | 总数 | 孤儿数(≤3) | 孤儿率 | 平均入链 |")
    lines.append("|------|------|-----------|--------|----------|")
    for ptype, info in PAGE_TYPES.items():
        st = report["stats_by_type"].get(ptype, {})
        t = st.get("total", 0)
        o = st.get("orphan", 0)
        rate = f"{o/t*100:.0f}%" if t > 0 else "-"
        avg = st.get("avg_inbound", 0)
        core_mark = " 🔴核心" if info["core"] else ""
        lines.append(f"| {info['label']}{core_mark} | {t} | {o} | {rate} | {avg} |")

    # 索引页
    for ptype_key in report["stats_by_type"]:
        if ptype_key not in PAGE_TYPES:
            st = report["stats_by_type"][ptype_key]
            lines.append(f"| {ptype_key} | {st.get('total',0)} | {st.get('orphan',0)} | - | {st.get('avg_inbound',0)} |")

    lines.append("")

    # 核心孤儿页详情（如果有）
    if report["core_orphans"]:
        lines.append(f"## 🔴 核心类型孤儿页（{len(report['core_orphans'])} 页）")
        lines.append("| # | URL | 类型 | 入链数 | 引用来源 |")
        lines.append("|---|-----|------|--------|----------|")
        for i, entry in enumerate(report["core_orphans"], 1):
            sources_str = ", ".join(entry["sources"][:5])
            if len(entry["sources"]) > 5:
                sources_str += f" ... (+{len(entry['sources'])-5})"
            if not sources_str:
                sources_str = "⚠️ 无入链"
            lines.append(
                f"| {i} | `{entry['url']}` | {entry['label']} | "
                f"**{entry['inbound']}** | {sources_str} |"
            )
        lines.append("")

    # 所有孤儿页清单
    if report["orphan_pages"]:
        lines.append(f"## 📋 全部孤儿页清单（{len(report['orphan_pages'])} 页，入链 ≤ {report['threshold']}）")
        lines.append("| # | URL | 类型 | 入链数 |")
        lines.append("|---|-----|------|--------|")
        for i, entry in enumerate(report["orphan_pages"], 1):
            lines.append(
                f"| {i} | `{entry['url']}` | {entry['label']} | {entry['inbound']} |"
            )
        lines.append("")
    else:
        lines.append("## ✅ 无孤儿页\n")

    lines.append("---")
    lines.append(f"*报告由 `scripts/audit_orphan_pages.py` 自动生成*")
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="全站入链审计 — 孤儿页检测")
    parser.add_argument("--ci", action="store_true", help="CI 模式：0 核心孤儿即 pass（exit 0）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--output", type=str, help="将 Markdown 报告写入文件")
    parser.add_argument("--threshold", type=int, default=3, help="入链阈值（默认 3）")
    args = parser.parse_args()

    # 1. 收集所有页面
    pages = collect_all_pages()
    if not pages:
        print("❌ 未找到任何 HTML 页面，请先构建站点。", file=sys.stderr)
        sys.exit(2)

    # 2. 构建链接图
    inbound, outbound = build_link_graph(pages)

    # 3. 生成报告
    report = compute_orphan_report(pages, inbound, outbound, threshold=args.threshold)

    # 4. 输出
    if args.json:
        # JSON 输出（CI 友好）
        output = {
            "pass": report["pass"],
            "total_pages": report["total_pages"],
            "threshold": report["threshold"],
            "avg_inbound_all": report["avg_inbound_all"],
            "core_orphans_count": len(report["core_orphans"]),
            "orphan_pages_count": len(report["orphan_pages"]),
            "core_orphans": [
                {"url": e["url"], "type": e["type"], "inbound": e["inbound"]}
                for e in report["core_orphans"]
            ],
            "stats_by_type": report["stats_by_type"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        md = format_markdown_report(report)
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"✅ 报告已写入: {out_path}")
        else:
            print(md)

    # 5. CI 判定
    if args.ci:
        if report["pass"]:
            print(f"\n✅ CI PASS: 0 个核心类型孤儿页", file=sys.stderr)
            sys.exit(0)
        else:
            print(
                f"\n❌ CI FAIL: {len(report['core_orphans'])} 个核心类型孤儿页",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()

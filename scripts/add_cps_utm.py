#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_cps_utm.py — 给 ads/cps.json 全部推广链接追加 UTM 归因参数（2026-08-15）

作用：把"站内点击（beacon）"与"阿里云云大使/腾讯云 CPS/百度文心合伙人后台的注册成交"串起来。
    utm_source    = aitoollab（固定站点）
    utm_medium    = cps（固定渠道类型）
    utm_campaign  = 品类英文 slug（每条不同，用于区分哪个品类出单）
    utm_content   = 平台渠道（aliyun / tencent / baidu）

用法：
    python scripts/add_cps_utm.py --dry-run    # 只打印每条 url 的前后变化，不写文件
    python scripts/add_cps_utm.py              # 实际写入（写前自动备份 cps.json.YYYYMMDD.bak）

幂等：url 已含 utm_source 的条目自动跳过。
"""
import argparse
import io
import json
import sys
from datetime import datetime
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CPS_PATH = "ads/cps.json"

# 品类英文 slug（utm_campaign 取值），key 未命中时回退用 raw key
CAMPAIGN_MAP = {
    # by_category（15）
    "AI对话": "ai-chat", "AI写作": "ai-writing", "AI绘画": "ai-image",
    "AI视频": "ai-video", "AI编程": "ai-coding", "AI开发": "ai-dev",
    "AI智能体": "ai-agent", "AI音频": "ai-audio", "AI设计": "ai-design",
    "AI办公": "ai-office", "AI效率": "ai-productivity", "AI自动化": "ai-automation",
    "AI搜索": "ai-search", "AI行业应用": "ai-industry", "AI翻译": "ai-translate",
    # by_news_category（5）
    "模型发布": "model-release", "论文研究": "paper-research",
    "产品发布": "product-release", "行业动态": "industry-news", "观点": "opinion",
    # by_article_category（6）
    "AI资讯": "ai-news", "AI行业动态": "ai-industry-news",
    "AI行业分析": "ai-industry-analysis", "行业趋势": "industry-trend",
    "industry-analysis": "industry-analysis", "数据洞察": "data-insight",
    # default
    "(default)": "default",
}


def channel_content(network):
    n = network or ""
    if "阿里云" in n:
        return "aliyun"
    if "腾讯" in n:
        return "tencent"
    if "百度" in n:
        return "baidu"
    return "other"


def add_utm(url, campaign, content):
    if "utm_source" in url:
        return url, False
    p = urlparse(url)
    qs = parse_qsl(p.query, keep_blank_values=True)
    qs += [
        ("utm_source", "aitoollab"),
        ("utm_medium", "cps"),
        ("utm_campaign", campaign),
        ("utm_content", content),
    ]
    return urlunparse(p._replace(query=urlencode(qs))), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印变化不写文件")
    args = ap.parse_args()

    with open(CPS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    changed, skipped, missing = 0, 0, 0
    report = []

    def handle(key, entry):
        nonlocal changed, skipped, missing
        if not isinstance(entry, dict) or "url" not in entry:
            return
        network = entry.get("network", "")
        campaign = CAMPAIGN_MAP.get(key, key)
        content = channel_content(network)
        new_url, did = add_utm(entry["url"], campaign, content)
        if not did:
            skipped += 1
            return
        report.append((key, entry["url"], new_url, campaign, content))
        entry["url"] = new_url
        changed += 1

    for key, entry in data.get("by_category", {}).items():
        handle(key, entry)
    for key, entry in data.get("by_news_category", {}).items():
        handle(key, entry)
    for key, entry in data.get("by_article_category", {}).items():
        handle(key, entry)
    # default 是顶层单条目（dict 含 url）
    handle("(default)", data.get("default", {}))

    # 打印变化明细
    print(f"== UTM 追加明细 == 改 {changed} / 跳过(已含utm) {skipped}\n")
    for key, old, new, campaign, content in report:
        print(f"[{key}] campaign={campaign} content={content}")
        print(f"  前: {old}")
        print(f"  后: {new}")
        print()

    if args.dry_run:
        print("== DRY-RUN 模式，未写入文件 ==")
        return

    # 写回（中文 JSON 铁律：脚本写 + 读回校验）
    stamp = datetime.now().strftime("%Y%m%d")
    bak = f"{CPS_PATH}.{stamp}.utm.bak"
    with open(CPS_PATH, encoding="utf-8") as f:
        with open(bak, "w", encoding="utf-8") as bf:
            bf.write(f.read())
    with open(CPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 校验：读回 + 统计 utm 条数
    with open(CPS_PATH, encoding="utf-8") as f:
        check = json.load(f)
    utm_count = json.dumps(check, ensure_ascii=False).count("utm_source=aitoollab")
    print(f"== 写入完成 == 备份 {bak}，读回校验通过，utm_source=aitoollab 共 {utm_count} 处")


if __name__ == "__main__":
    main()

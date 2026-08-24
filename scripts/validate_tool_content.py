#!/usr/bin/env python3
"""
内容一致性校验器：扫描 tools.json，标记内容与分类/描述明显不符的工具。

设计目标：低成本、可解释、不误报。用关键词信号而非语义模型，
专门捕捉“牛头不对马嘴”型错误（如 AI绘画 工具被写成聊天/代码助手）。
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_PATH = os.path.join(BASE_DIR, "data", "tools.json")

# 分类 → 期望关键词（至少命中一个） / 禁忌关键词（命中则强烈怀疑错位）
CATEGORY_SIGNALS = {
    "AI绘画": {
        "expected": ["图像", "图片", "绘画", "画图", "文生图", "图生图", "生成", "视觉", "海报", "插画", "图层"],
        "forbidden": ["1M tokens", "100万 tokens", "长上下文", "超长上下文", "代码生成", "自动补全", "编程", "数学推理", "聊天机器人", "问答助手", "只聊天"],
    },
    "AI设计": {
        "expected": ["设计", "视觉", "品牌", "UI", "排版", "海报", "Logo", "素材", "模板"],
        "forbidden": ["1M tokens", "代码生成", "自动补全", "数学推理", "聊天机器人"],
    },
    "AI视频": {
        "expected": ["视频", "动画", "镜头", "分镜", "剪辑", "生成视频", "视频生成", "动效"],
        "forbidden": ["1M tokens", "超长上下文", "代码生成", "数学推理", "图层分离"],
    },
    "AI对话": {
        "expected": ["聊天", "对话", "问答", "助手", "文本", "多轮对话", "大模型"],
        "forbidden": ["图层分离", "文生图", "图生图", "生成视频", "海报设计", "局部重绘"],
    },
    "AI编程": {
        "expected": ["代码", "编程", "补全", "调试", "重构", "IDE", "开发者"],
        "forbidden": ["图层分离", "海报", "1M tokens", "绘画"],
    },
    "AI写作": {
        "expected": ["写作", "文案", "润色", "文章", "内容创作", "营销文案"],
        "forbidden": ["图层分离", "代码生成", "视频生成"],
    },
    "AI音频": {
        "expected": ["音频", "音乐", "声音", "语音", "配音", "编曲", "混音"],
        "forbidden": ["图像生成", "图层分离", "海报", "代码生成"],
    },
    "AI搜索": {
        "expected": ["搜索", "检索", "信息源", "引用", "实时", "联网"],
        "forbidden": ["图层分离", "绘画", "视频生成", "代码生成"],
    },
    "AI智能体": {
        "expected": ["Agent", "智能体", "工作流", "自动化", "任务", "编排"],
        "forbidden": ["图层分离", "绘画", "代码生成"],
    },
}

# 通用：内容里出现明显与公司/产品类型冲突的知名公司名，触发提示
KNOWN_COMPANY_PATTERNS = {
    "阶跃星辰": ["seedream"],  # Seedream 是字节产品，不应出现阶跃星辰
    "StepFun": ["seedream"],
    # 可按需扩展
}


def _normalize(text: str) -> str:
    if not text:
        return ""
    return text.lower().replace(" ", "").replace("，", ",").replace("。", ".")


def _has_any(text: str, keywords: list[str]) -> list[str]:
    """返回命中的关键词列表（保留大小写不敏感），排除显式否定语境。"""
    t = text.lower()
    hits = []
    for kw in keywords:
        kl = kw.lower()
        for m in re.finditer(re.escape(kl), t):
            # 取关键词前后 10 个字符，判断是否被“不是/非/无需/不需要/没有”等否定词修饰
            start = max(0, m.start() - 10)
            end = min(len(t), m.end() + 10)
            ctx = t[start:end]
            if re.search(r"(不是|非|无需|不需要|没有|不含|并非|只是|仅为|只是).{0,8}" + re.escape(kl), ctx):
                continue
            hits.append(kw)
            break  # 同一关键词只计一次
    return hits


def check_tool(tool: dict) -> list[dict]:
    """返回该工具的所有问题（列表），每个问题包含 severity/field/message。"""
    issues = []
    slug = tool.get("slug", "")
    name = tool.get("name", "")
    category = tool.get("category", "")
    content = tool.get("content") or ""
    description = tool.get("description") or ""

    if not content or len(content) < 200:
        issues.append({
            "slug": slug,
            "name": name,
            "category": category,
            "field": "content",
            "severity": "warning",
            "message": "内容过短或为空，可能是生成失败。",
        })
        return issues

    signals = CATEGORY_SIGNALS.get(category)
    if signals:
        expected_hits = _has_any(content, signals["expected"])
        forbidden_hits = _has_any(content, signals["forbidden"])

        if not expected_hits and forbidden_hits:
            issues.append({
                "slug": slug,
                "name": name,
                "category": category,
                "field": "content",
                "severity": "critical",
                "message": f"内容与分类严重不符：未命中任何'{category}'期望关键词，却出现禁忌词 {forbidden_hits}。",
            })
        elif forbidden_hits and len(expected_hits) < 2:
            issues.append({
                "slug": slug,
                "name": name,
                "category": category,
                "field": "content",
                "severity": "high",
                "message": f"内容疑似错位：出现禁忌词 {forbidden_hits}，期望关键词仅命中 {expected_hits}。",
            })
        elif forbidden_hits:
            issues.append({
                "slug": slug,
                "name": name,
                "category": category,
                "field": "content",
                "severity": "medium",
                "message": f"内容出现与分类不太匹配的词：{forbidden_hits}，建议复核。",
            })

    # 公司/品牌名冲突检查
    for company, slug_patterns in KNOWN_COMPANY_PATTERNS.items():
        if any(p in slug.lower() for p in slug_patterns):
            if company.lower() in content.lower():
                issues.append({
                    "slug": slug,
                    "name": name,
                    "category": category,
                    "field": "content",
                    "severity": "critical",
                    "message": f"内容出现错误品牌名：'{company}'，与工具实际品牌冲突。",
                })

    # description 与 content 核心实体一致性（轻量）
    # 如果 description 明确出现某品牌名，而 content 完全未出现，可能是内容写错对象
    # 只匹配句首/主语位置的品牌名，避免把“帮助团队”这类短语误判为品牌
    brand_in_desc = re.search(
        r"^(?:[^，。]{0,35}?)(?:是|由|来自|隶属)\s*([\u4e00-\u9fa5]{2,12}(?:公司|团队|科技|实验室|研究院))",
        description,
    )
    if brand_in_desc:
        brand = brand_in_desc.group(1)
        # 排除把“面向/帮助/提升/专注/一个/一款”等短语误判为品牌的情况
        if (
            brand not in ("团队", "公司", "科技公司")
            and not re.search(r"面向|帮助|提升|专注|成为|旨在|一款|一个|提供|支持|由", brand)
            and brand not in content
        ):
            issues.append({
                "slug": slug,
                "name": name,
                "category": category,
                "field": "content",
                "severity": "medium",
                "message": f"内容未提及 description 中的品牌/团队 '{brand}'，可能写错对象。",
            })

    return issues


def main():
    with open(TOOLS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tools = data if isinstance(data, list) else data.get("tools", [])

    all_issues = []
    for t in tools:
        all_issues.extend(check_tool(t))

    # 汇总
    severity_count = defaultdict(int)
    for issue in all_issues:
        severity_count[issue["severity"]] += 1

    print(f"校验完成：共 {len(tools)} 个工具，发现 {len(all_issues)} 条问题")
    print(f"  critical: {severity_count['critical']}")
    print(f"  high: {severity_count['high']}")
    print(f"  medium: {severity_count['medium']}")
    print(f"  warning: {severity_count['warning']}")
    print("")

    # 按严重级输出
    for severity in ["critical", "high", "medium", "warning"]:
        items = [i for i in all_issues if i["severity"] == severity]
        if not items:
            continue
        print(f"## {severity.upper()} ({len(items)})")
        for i in items:
            print(f"- [{i['category']}] {i['name']} ({i['slug']})")
            print(f"  {i['message']}")
        print("")

    # 写入扫描报告（可选）
    report_path = os.path.join(BASE_DIR, "scripts", "_content_validation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "scanned_at": datetime.now().isoformat(),
            "total_tools": len(tools),
            "issue_count": len(all_issues),
            "severity_count": dict(severity_count),
            "issues": all_issues,
        }, f, ensure_ascii=False, indent=2)
    print(f"详细报告已保存：{report_path}")

    # 以非零退出码表示发现严重/高级问题
    critical_or_high = severity_count["critical"] + severity_count["high"]
    if critical_or_high:
        sys.exit(1)


if __name__ == "__main__":
    main()

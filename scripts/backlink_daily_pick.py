# -*- coding: utf-8 -*-
"""外链建设 · 每日选文推送队列生成器（半自动版）

背景（OPTIMIZATION-ACTION-LIST 3.5）：
    站内文章 176 篇，不可能天天人工挑"哪篇值得外推"。本脚本每天自动选出
    最值得推送到外部平台（公众号/知乎/CSDN 等）的文章，写入 backlink_push_queue/。
    队列内每篇包含：推荐语（钩子）+ 公众号版（正文提纲）+ 知乎版（浓缩回答）
    + CSDN/掘金版（全文转载，可直接粘贴）。

注意：推荐语/摘要是"钩子"，不是可发布正文——
    · CSDN/掘金：直接发全文转载版（含原文链接声明）；
    · 知乎：发浓缩回答（脚本已生成约500-800字骨架，建议再顺一遍语气）；
    · 公众号：按提纲把全文改写/转载，阅读原文放链接，正文不放外链。

用法：
    python scripts/backlink_daily_pick.py            # 今天选 3 篇（默认）
    python scripts/backlink_daily_pick.py --count 5  # 指定篇数
    python scripts/backlink_daily_pick.py --preview  # 只看候选不写文件

调度（Windows 任务计划，每日 09:30）：
    schtasks /Create /TN "aitoollab_backlink_pick" /TR "python C:\\Users\\27040\\WorkBuddy\\20260321092139\\seo-site\\scripts\\backlink_daily_pick.py" /SC DAILY /ST 09:30 /F

说明：
    1) 选文规则：时效性 + 内容质量 + 教程/评测类目加权，7 天内选过的自动跳过；
    2) 状态记录在 backlink_push_queue/.pick_state.json，重复执行同一天不会重复选；
    3) 推送动作仍需人工复制到平台（平台 API 差异与风控，半自动为主）；
    4) 该脚本只生成内容，不联网、不推送，安全幂等。
"""

import argparse
import json
import os
import sys
import datetime
import random

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io_wrapper = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_PATH = os.path.join(BASE_DIR, "data", "articles.json")
QUEUE_DIR = os.path.join(BASE_DIR, "backlink_push_queue")
STATE_PATH = os.path.join(QUEUE_DIR, ".pick_state.json")

# 教程/评测/深度类内容更适合外推（平台审核友好、生命周期长）
PUSH_CATEGORY_BONUS = {
    "AI工具教程": 5,
    "教程指南": 5,
    "AI教程": 5,
    "AI评测": 4,
    "AI工具评测": 4,
    "AI绘画": 3,
    "AI视频": 3,
    "AI编程": 3,
    "行业分析": 2,
    "行业趋势": 2,
    "数据洞察": 2,
}

# 快讯/时效类内容外推价值低（容易过期），降权
STALE_CATEGORIES = {"AI资讯", "AI行业动态", "ai-news", "industry-news", "AI快讯"}


def load_articles():
    with open(ARTICLES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"picked": {}}


def save_state(state):
    os.makedirs(QUEUE_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def score_article(a, today):
    """返回 (分数, 原因列表)。分数越高越值得外推。"""
    reasons = []
    score = 0.0

    date_str = a.get("dateFull") or a.get("date") or ""
    try:
        pub = datetime.date.fromisoformat(date_str)
        age = (today - pub).days
    except ValueError:
        age = 999

    # 时效性：最近 14 天 +8，30 天 +5，60 天 +3；超过 120 天不额外加分
    if 0 <= age <= 14:
        score += 8
        reasons.append(f"14天内新文(+8)")
    elif age <= 30:
        score += 5
        reasons.append("30天内(+5)")
    elif age <= 60:
        score += 3
        reasons.append("60天内(+3)")
    elif age > 120:
        score -= 4
        reasons.append("超120天旧文(-4)")

    # 内容量：字数（中文字符 + 英文单词）
    content = a.get("content") or a.get("body") or ""
    cn = sum(1 for ch in content if "\u4e00" <= ch <= "\u9fff")
    en = sum(1 for ch in content if ch.isalpha())
    words = cn + en
    if words >= 4000:
        score += 5
        reasons.append(f"长文{words}字(+5)")
    elif words >= 2500:
        score += 3
        reasons.append(f"中长文{words}字(+3)")

    # 数据可溯源：有数据来源章节的内容可信度更高，平台更愿意收录
    if "数据来源" in content or "数据声明" in content:
        score += 4
        reasons.append("含数据来源(+4)")

    # 类目加权
    cat = a.get("category", "")
    if cat in PUSH_CATEGORY_BONUS:
        score += PUSH_CATEGORY_BONUS[cat]
        reasons.append(f"{cat}(+{PUSH_CATEGORY_BONUS[cat]})")
    if cat in STALE_CATEGORIES:
        score -= 6
        reasons.append(f"时效类{cat}(-6)")

    # 有 FAQ/HowTo 结构：AI 引用友好
    if "**Q" in content or "## FAQ" in content or "常见问题" in content:
        score += 2
        reasons.append("含FAQ结构(+2)")

    return score, reasons


def build_recommend(a):
    """生成推荐语：优先用 excerpt，再用正文首段兜底。"""
    excerpt = (a.get("excerpt") or "").strip()
    excerpt = strip_markdown(excerpt)
    if len(excerpt) >= 40:
        return cut_sentence(excerpt)
    content = (a.get("content") or a.get("body") or "").strip()
    para = ""
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith(("#", ">", "|", "-")):
            para = line
            break
    return cut_sentence(strip_markdown(para), 120) or excerpt


def clean_tags(tags):
    """tags 里可能有 dict 等非字符串元素，统一过滤成字符串。"""
    out = []
    for t in tags or []:
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, dict):
            out.append(str(t.get("text") or t.get("name") or t.get("tag") or "").strip())
        else:
            out.append(str(t))
    return [t for t in out if t]


def strip_markdown(text):
    """去掉推荐语里的 markdown 链接/加粗，避免平台格式混乱。"""
    import re
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"[`>*#]", "", text)
    return text.strip()


def cut_sentence(text, limit=150):
    """按句号边界截断，避免推荐语断在句子中间。"""
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[:limit]
    for sep in ("。", "！", "？", ".", "!", "?", "；"):
        idx = head.rfind(sep)
        if idx >= limit * 0.5:
            return head[: idx + 1]
    return head + "…"


def build_abstract(a, recommend, limit=220):
    """摘要：推荐语截断 + 标题首句，凑够平台展示长度。"""
    title = a.get("seo_title") or a.get("title", "")
    abstract = recommend
    if len(abstract) < limit:
        sep = "" if abstract.endswith(("。", "！", "？", "！？")) else "。"
        abstract += f"{sep}本文从{title}切入，用可溯源的数据和实操流程把要点讲透。"
    return abstract[:limit]


def extract_h2(md):
    """提取正文的 ## 小标题（去掉编号前缀外的装饰）。"""
    import re
    return re.findall(r"^## (.+)$", md, re.MULTILINE)


def extract_faq(md, limit=3):
    """提取正文 FAQ 的 Q/A（支持 **Q1：…** 格式），返回前 limit 条。"""
    import re
    qas = re.findall(r"\*\*Q\d*[：:]\s*([^*\n]+?)\*\*\s*\n+\s*(.+?)(?=\n\*\*Q\d*[：:]|\n## |\Z)", md, re.DOTALL)
    out = []
    for q, a in qas:
        a = re.sub(r"\*\*", "", a).strip()
        a = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", a)
        a = re.sub(r"\s+", " ", a)
        if len(a) > 160:
            a = a[:160] + "…"
        out.append((q.strip(), a))
        if len(out) >= limit:
            break
    return out


def abs_links(md):
    """站内相对链接转绝对链接，供转载到外站使用。"""
    import re
    md = re.sub(r"\]\(/([^)]+)\)", r"](https://www.aitoollab.cn/\1)", md)
    return md


def build_csdn_full(a):
    """CSDN/掘金转载全文版：去首行 H1 + 相对链接转绝对 + 转载声明。"""
    import re
    content = a.get("content") or a.get("body") or ""
    content = re.sub(r"^# .+\n?", "", content, count=1)
    content = abs_links(content)
    header = (
        f"> 本文由 aitoollab.cn 原创并授权转载。原文：[{a.get('seo_title') or a.get('title')}]"
        f"(https://www.aitoollab.cn/articles/{a['slug']}/)，转载请保留此声明。\n\n"
    )
    return header + content.strip() + "\n"


def build_zhihu_answer(a, recommend):
    """知乎浓缩回答：推荐语开头 + 要点列表 + FAQ 速答 + 文末原文链接。"""
    content = a.get("content") or a.get("body") or ""
    h2s = [h for h in extract_h2(content) if "FAQ" not in h and "常见问题" not in h and "数据来源" not in h]
    faqs = extract_faq(content, limit=2)
    lines = [recommend, ""]
    if h2s:
        lines.append("先把结论给你：")
        for h in h2s[:6]:
            clean = h.strip("一二三四五六七八九十。、 0123456789")
            lines.append(f"- {clean}")
        lines.append("")
    if faqs:
        lines.append("几个高频问题速答：")
        for q, ans in faqs:
            lines.append(f"- {q}：{ans}")
        lines.append("")
    lines.append(f"完整实测数据、对比表和价格时间线见原文：https://www.aitoollab.cn/articles/{a['slug']}/")
    return "\n".join(lines)


def build_wechat_outline(a):
    """公众号正文提纲：给出全文改写需要的章节骨架。"""
    content = a.get("content") or a.get("body") or ""
    h2s = [h for h in extract_h2(content) if "FAQ" not in h and "常见问题" not in h and "数据来源" not in h]
    outline = "正文建议：把原文全文改写成公众号文章（或用转载功能），章节骨架如下——\n"
    for i, h in enumerate(h2s, 1):
        outline += f"{i}. {h}\n"
    outline += "文末：引导关注 + 「阅读原文」指向原文链接，正文内不要放外链（公众号限制）。"
    return outline


def fmt_wechat(a, recommend, abstract, tags):
    return (
        f"### 公众号版（改写成全文后发布）\n"
        f"标题：{a.get('seo_title') or a.get('title')}\n"
        f"摘要：{abstract}\n"
        f"{build_wechat_outline(a)}\n"
        f"标签：{', '.join(tags[:5])}\n"
    )


def fmt_zhihu(a, recommend, abstract, tags):
    title = a.get("seo_title") or a.get("title", "")
    question = title.replace("（2026）", "").strip("：: ")
    return (
        f"### 知乎版（浓缩干货回答，约500-800字）\n"
        f"问题向标题（可选）：{question}，到底怎么选/怎么用？\n"
        f"回答正文：\n"
        f"{build_zhihu_answer(a, recommend)}\n"
        f"话题：{', '.join(tags[:4])}\n"
    )


def fmt_csdn(a, recommend, abstract, tags):
    return (
        f"### CSDN/掘金版（直接转载全文）\n"
        f"标题：{a.get('seo_title') or a.get('title')}\n"
        f"标签：{' '.join(tags[:6])}\n"
        f"正文（完整转载，含原文链接声明）：\n"
        f"{build_csdn_full(a)}\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3, help="每天选几篇（默认3）")
    parser.add_argument("--preview", action="store_true", help="只打印候选不写文件")
    args = parser.parse_args()

    articles = load_articles()
    state = load_state()
    today = datetime.date.today()
    today_key = today.isoformat()

    # 同一天已选过则直接输出当天结果（幂等）
    picked_today = state.get("picked", {}).get(today_key, [])
    if picked_today and not args.preview:
        print(f"[幂等] {today_key} 已选过 {len(picked_today)} 篇，直接输出队列文件。")
        queue_file = os.path.join(QUEUE_DIR, f"{today_key}.md")
        if os.path.exists(queue_file):
            print(f"队列文件：{queue_file}")
        return

    # 最近 7 天选过的不再选
    recent = set()
    for d, slugs in state.get("picked", {}).items():
        try:
            dd = datetime.date.fromisoformat(d)
        except ValueError:
            continue
        if (today - dd).days <= 7:
            recent.update(slugs)

    candidates = []
    for a in articles:
        slug = a.get("slug", "")
        if not slug or not (a.get("content") or a.get("body")):
            continue
        if slug in recent:
            continue
        sc, reasons = score_article(a, today)
        candidates.append((sc, slug, a, reasons))

    candidates.sort(key=lambda x: -x[0])
    random.seed(today_key)  # 同分时用当天日期做稳定随机，保证可复现
    # 前 12 名里做小范围随机，避免每天都推同一批
    pool = candidates[:12]
    random.shuffle(pool)
    chosen = sorted(pool[: args.count], key=lambda x: -x[0])

    if args.preview:
        print(f"今日候选（共{len(candidates)}篇，取前{args.count}）：")
        for sc, slug, a, reasons in chosen:
            print(f"  {sc:>4}  {slug}  {a.get('title','')[:40]}")
        return

    os.makedirs(QUEUE_DIR, exist_ok=True)
    lines = [
        f"# 外链推送队列 {today_key}",
        "",
        f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> 用途：人工复制到公众号/知乎/CSDN 等平台（半自动，发布前请核对内容与链接）。",
        "> 规则：时效+质量+教程评测加权，7天内选过自动跳过；同日重复执行幂等。",
        "",
    ]

    picked = []
    for idx, (sc, slug, a, reasons) in enumerate(chosen, 1):
        recommend = build_recommend(a)
        abstract = build_abstract(a, recommend)
        tags = clean_tags(a.get("tags", []))[:8]
        lines.append(f"---")
        lines.append(f"## {idx}. {a.get('title','')}")
        lines.append("")
        lines.append(f"- 原文：https://www.aitoollab.cn/articles/{slug}/")
        lines.append(f"- 评分：{sc}（{'、'.join(reasons)}）")
        lines.append(f"- 推荐语：{recommend}")
        lines.append("")
        lines.append(fmt_wechat(a, recommend, abstract, tags))
        lines.append("")
        lines.append(fmt_zhihu(a, recommend, abstract, tags))
        lines.append("")
        lines.append(fmt_csdn(a, recommend, abstract, tags))
        lines.append("")
        picked.append(slug)

    queue_file = os.path.join(QUEUE_DIR, f"{today_key}.md")
    with open(queue_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    state.setdefault("picked", {})[today_key] = picked
    save_state(state)

    print(f"[OK] 已选 {len(picked)} 篇，队列文件：{queue_file}")
    for slug in picked:
        print(f"  - {slug}")


if __name__ == "__main__":
    main()

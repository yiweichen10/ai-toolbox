# -*- coding: utf-8 -*-
"""
关键词核实脚本 — 用百度搜索联想词（真实用户检索词）升级 tools.json 的 long_tail 字段。

为什么做：
- long_tail 是工具页 Title 的「自然话术种子」（build_title = {name} {long_tail}（{year}））。
- 原值由 gen_long_tail 按规则推断（分类/价格/竞品），质量尚可但非真实搜索词。
- 百度下拉框返回的是真实用户会搜的词（如「khanmigo国内能用吗」「chatgpt是什么」），
  比规则推断更贴近搜索意图，CTR/排名更优。免费、无需 key、可在无人值守 automation 跑。

做法：
- 对每个重点工具，用多个「种子查询」调百度 suggest，收集真实联想词。
- 去掉品牌名前缀 → 得到自然尾部话术（long_tail 格式）。
- 按意图词+长度评分，选最佳写回，标记 long_tail_verified=true。
- 找不到好词则保留原值、不标记 verified，下次重试。

用法：
    python seo_keyword_research.py --count 15            # 核实 15 个未核实工具并写回
    python seo_keyword_research.py --count 15 --dry-run  # 只报告不写回
    python seo_keyword_research.py --force               # 重新核实已 verified 的（趋势更新）
    python seo_keyword_research.py --slug chatgpt khanmigo  # 指定工具

注意：本脚本只改 data/tools.json（long_tail / long_tail_verified 字段），不动页面；
      写回后需 build.py --target tools + deploy.sh --skip-build 才能上线。
"""

import json
import os
import re
import sys
import time
import argparse
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "tools.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# 知名/高价值工具优先核实（长尾流量价值最高）。slug 不在数据里自动忽略。
KNOWN = [
    "chatgpt", "midjourney", "claude", "gemini", "copilot", "github-copilot",
    "stable-diffusion", "dall-e", "runway", "suno", "kling", "jimeng",
    "wenxin-yiyan", "xunfei-xinghuo", "tongyi-qianwen", "deepseek", "qwen",
    "kimi", "doubao", "yuanbao", "zhipu-qingyan", "baichuan",
    "perplexity", "character-ai", "heygen", "elevenlabs", "otter", "gamma",
    "notion-ai", "cursor", "whisper", "veo", "sora", "pixverse", "hailuo",
    "grok", "mistral", "coze", "dify", "langchain", "khanmigo",
    "stable-diffusion-online", "leonardo-ai", "adobe-firefly", "canva-ai",
    "poe", "quillbot", "gamma", "jasper", "copy-ai", "synthesia",
]

# 种子查询模板（基于工具名生成多个检索角度，覆盖不同搜索意图）
SEED_TPL = [
    "{name}", "{name}评测", "{name}免费", "{name}怎么样",
    "{name}是什么", "{name}怎么用", "{name}平替", "{name} vs",
    "{name}靠谱吗", "{name}好用吗",
]

# 意图词评分（命中高分词优先；基础词次之）
HIGH_INTENT = ["免费", "评测", "怎么样", "是什么", "平替", "好用吗", "值得", "国内", "靠谱", "收费", "哪个好"]
LOW_INTENT = ["怎么用", "怎么读", "和", "比", "对比", "教程", "推荐", "靠谱吗"]

# 硬排除词：出现在尾部即丢弃。这些是「找镜像/下载/客户端」意图（中文版、官网、
# 下载、入口、账号、各手机品牌…），不适合评测站标题，且拼出来语义不通（如
# 「ChatGPT 免费中文版」）。「国内能用吗」含「国内」但表达访问可用性，保留。
HARD_EXCLUDE = [
    "中文版", "官网", "下载", "入口", "账号", "网页", "网址", "app", "安卓",
    "ios", "苹果", "华为", "oppo", "手机版", "电脑版", "在线", "网页版",
    "最新版", "破解", "版下载", "版免费", "客户端",
    # 实体歧义/噪声词（AI 工具名常被百度联想成其他事物）：酒/烟/油/材质/牌子/缩写/
    # 成语/studio/维护/网盘/钢琴 等，拼出来语义错误或无意义
    "酒", "烟", "油", "材质", "红酒", "牌子", "缩写", "成语",
    # 新增歧义实体/技术噪声（AI 工具名常被百度联想成其他事物或技术文档）
    "车", "自行车", "档次", "型号", "品牌", "缓存",
    "studio", "维护", "网盘", "钢琴", "素材",
]


def baidu_suggest(q):
    """返回百度下拉联想词列表（真实用户检索词）。失败返回 []。

    注意：百度 suggest 接口返回 GBK 编码字节（无 charset 声明），必须用 GBK 解码；
    先试 utf-8 兜底，失败回退 gbk，否则中文会变乱码导致提取失败。
    opensearch 接口返回 JSON 数组 [查询词, [联想词列表]]，取第 2 项。
    """
    qe = urllib.parse.quote(q)
    url = f"https://www.baidu.com/su?wd={qe}&action=opensearch"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read()
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            txt = raw.decode("gbk", "ignore")
        data = json.loads(txt)
        if isinstance(data, list) and len(data) > 1:
            return data[1]
        return []
    except Exception:
        return []


def extract_tail(name, cand):
    """从联想词去掉品牌名前缀，得到 long_tail 尾部话术。无关/纯品牌名/脏词返回 None。"""
    c = (cand or "").strip()
    if not c:
        return None
    low_c, low_n = c.lower(), name.lower()
    if low_c == low_n:
        return None  # 纯品牌名
    if not low_c.startswith(low_n):
        return None  # 不含本工具名，跳过（避免无关词污染）
    tail = c[len(name):].strip(" 　-—:：")
    if not tail or len(tail) > 16:
        return None
    # 标点过滤（逗号/顿号/句号说明是百度拼接的脏词，如「怎么样,好用吗」）
    if re.search(r"[,，。、;；]", tail):
        return None
    # 硬排除「找下载/镜像」意图词（大小写不敏感）
    low_tail = tail.lower()
    if any(b in low_tail for b in HARD_EXCLUDE):
        return None
    # 纯数字/年份无意义（如「2023」），排除
    if re.fullmatch(r"\d{1,4}", tail):
        return None
    # 数字:数字 比值（如「4:3」「16:9」），非搜索意图，排除
    if re.fullmatch(r"\d+[:：/]\d+", tail):
        return None
    return tail


def score_tail(tail):
    # 多问句根拼接（如「怎么样好用吗」「是什么还是怎么用」）→ 百度脏词，强杀
    JOINERS = ["怎么样", "好用吗", "怎么用", "是什么", "值得吗", "靠谱吗",
               "收费吗", "免费吗", "平替吗", "国内能用吗"]
    # 冗余后缀：自然但作为标题尾部不如纯问句干净，轻微降权
    REDUNDANT_SUFFIX = ["软件", "模型", "意思", "网站", "品牌", "公司",
                        "人工智能", "指标", "咋读", "怎么读", "截图搜索", "哪个好",
                        "网络语", "东西", "ai", "工具", "版本", "最新"]
    s = 0
    for w in HIGH_INTENT:
        if w in tail:
            s += 3
    for w in LOW_INTENT:
        if w in tail:
            s += 1
    # 拼接脏词：多个问句根共存
    if sum(1 for j in JOINERS if j in tail) > 1:
        s -= 20
    # 同一词重复
    for dup in ["好用吗", "怎么样", "是什么", "怎么用", "免费", "值得", "国内"]:
        if tail.count(dup) > 1:
            s -= 20
    # 冗余后缀降权，让「是什么」这类纯问句胜出
    if any(sx in tail for sx in REDUNDANT_SUFFIX):
        s -= 2
    L = len(tail)
    if 2 <= L <= 8:
        s += 3
    elif 9 <= L <= 12:
        s += 1
    elif L > 14:
        s -= 2
    return s


def research(tool):
    """返回 (best_tail, candidates_count, top_candidates)。best_tail 可能为 None。"""
    name = tool.get("name", "")
    cands = set()
    for tpl in SEED_TPL:
        for w in baidu_suggest(tpl.format(name=name)):
            cands.add(w)
        time.sleep(0.22)  # 礼貌延迟，避免被屏蔽
    tails = []
    for c in cands:
        t = extract_tail(name, c)
        if t:
            tails.append((score_tail(t), t))
    tails = [x for x in tails if x[0] > 0]
    tails.sort(reverse=True)
    best = tails[0][1] if tails else None
    top = [t for _, t in tails[:6]]
    return best, len(cands), top


def select_targets(tools, count, force, specific):
    if specific:
        want = set(specific)
        return [t for t in tools if t.get("slug") in want][:count]
    pool = [t for t in tools if force or not t.get("long_tail_verified")]
    # KNOWN 优先，其余按 slug 稳定排序（每周推进、不重复）
    known_set = set(KNOWN)
    known = [t for t in pool if t.get("slug") in known_set]
    rest = [t for t in pool if t.get("slug") not in known_set]
    rest.sort(key=lambda x: x.get("slug", ""))
    ordered = known + rest
    return ordered[:count]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=15)
    ap.add_argument("--dry-run", action="store_true", help="只报告不写回")
    ap.add_argument("--force", action="store_true", help="重新核实已 verified 的")
    ap.add_argument("--slug", nargs="*", default=[], help="指定 slug")
    args = ap.parse_args()

    with open(DATA, "r", encoding="utf-8") as f:
        tools = json.load(f)

    targets = select_targets(tools, args.count, args.force, args.slug)
    if not targets:
        print("没有需要核实的工具（全部已 verified 且未指定 --force）。")
        return

    print(f"本次核实 {len(targets)} 个工具" + (" [DRY-RUN]" if args.dry_run else ""))
    print("-" * 60)

    tmap = {t["slug"]: t for t in tools}
    updated = 0
    skipped = 0
    for t in targets:
        name = t.get("name", "")
        slug = t.get("slug", "")
        old = t.get("long_tail", "")
        best, n_cand, top = research(t)
        if best and best != old:
            print(f"[更新] {name} ({slug})")
            print(f"       旧: {old}")
            print(f"       新: {best}   (联想候选 {n_cand} 个, 候选: {top})")
            if not args.dry_run:
                t["long_tail"] = best
                t["long_tail_verified"] = True
                t["long_tail_source"] = "baidu_suggest"
            updated += 1
        elif best == old:
            print(f"[维持] {name} ({slug}) 规则词已是最优: {old}")
            if not args.dry_run:
                t["long_tail_verified"] = True
                t["long_tail_source"] = "baidu_suggest"
            updated += 1
        else:
            print(f"[跳过] {name} ({slug}) 无可靠联想词 (候选 {n_cand} 个), 保留: {old}")
            skipped += 1

    print("-" * 60)
    print(f"完成: 更新/维持 {updated}, 跳过 {skipped}")

    if not args.dry_run and updated:
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(tools, f, ensure_ascii=False, indent=2)
        print(f"已写回 data/tools.json（{updated} 个工具）")


if __name__ == "__main__":
    main()

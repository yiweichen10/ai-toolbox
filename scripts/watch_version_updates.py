# -*- coding: utf-8 -*-
"""
watch_version_updates.py — AI 工具版本更新监控
================================================
扫描多个数据源（官方博客 RSS + Product Hunt + aihot 直连 + GitHub Releases）最近 N 天内容，
用「工具名 + 版本模式」匹配 tools.json 中已知工具，命中即生成「版本更新候选清单」，
供主流程/Agent 联网核实后更新 tools.json。

数据源:
  news       本地 AI 快讯 data/news_*.json（可选源，不作为默认；监控改用 aihot 直连最新）
  rss        官方博客 RSS（OpenAI/Google/NVIDIA/Microsoft 等，沙箱可达源；容错跳过失败源）
  producthunt Product Hunt feed（可选，失败跳过）
  aihot      直连 aihot 全量新闻（最近窗口 API 上限100条，覆盖全网 AI 动态，不依赖本地8条精选）
  github     对 tools.json 中带 github repo 的开源工具拉取 Releases（权威版本信号，沙箱可达）

用法:
  python scripts/watch_version_updates.py                      # 默认四源(不含news)，近 7 天
  python scripts/watch_version_updates.py --days 14            # 近 14 天
  python scripts/watch_version_updates.py --sources news       # 仅快讯源
  python scripts/watch_version_updates.py --sources news,rss   # 快讯+官方RSS
  python scripts/watch_version_updates.py --out data/version_update_candidates.json
  python scripts/watch_version_updates.py --slugs kimi deepseek

输出: data/version_update_candidates.json
  {"updated": "...", "sources": [...], "candidates": [{"slug","name","version","title","date","category","source"}]}
"""
import json, os, re, sys, glob
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(BASE_DIR, "data", "tools.json")
DEFAULT_OUT = os.path.join(BASE_DIR, "data", "version_update_candidates.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
CST = timezone(timedelta(hours=8))

# 官方博客 RSS 源（已逐一验证可用；注意 mistral.ai/feed.xml 会触发沙箱杀进程，禁止加入）
RSS_FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google Blog", "https://blog.google/rss/"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("NVIDIA", "https://blogs.nvidia.com/feed/"),
    ("Microsoft AI", "https://www.microsoft.com/en-us/ai/blog/feed/"),
]

# 版本 token 模式：K3 / V4 / GPT-5.6 / FLUX 3 / X.0 / 2.8T 等
VERSION_RE = re.compile(
    r"\b(?:[A-Za-z]{1,6}[- ]?\d+(?:\.\d+)*[A-Za-z]*(?: Pro| Max| Ultra| Mini| Turbo| Flash| Lite)?)\b"
)
# 发布/更新动作关键词
ACTION_WORDS = ["发布", "开源", "上线", "推出", "升级", "更新", "发布日", "支持", "宣布", "开源发布", "available", "release", "launch"]

def load_tools():
    """分片优先(真源 data/tools/*.json), 单体回退(2026-08-26 去单体化)。"""
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
        from data_store import load_all_tools
        return load_all_tools()
    except Exception:
        with open(TOOLS_JSON, encoding="utf-8") as f:
            return json.load(f)

def load_news(days):
    """加载最近 days 天所有 news_*.json 的条目（带日期）。"""
    items = []
    today = datetime.now()
    for f in sorted(glob.glob(os.path.join(BASE_DIR, "data", "news_*.json"))):
        m = re.search(r"news_(\d{4}-\d{2}-\d{2})\.json$", f)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d")
        if (today - d).days > days:
            continue
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        arr = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(arr, list):
            continue
        for it in arr:
            items.append({"title": it.get("title", ""), "category": it.get("category", ""),
                          "date": m.group(1), "source": "news"})
    return items

def _parse_rss_items(raw, name, days, now):
    """解析 RSS/Atom XML（兼容 <item> 与 <entry>），返回近 days 天的 [{title,date,category,source}]。"""
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    cutoff = now - timedelta(days=days)
    entries = list(root.iter("item")) or list(root.iter("entry"))
    for item in entries:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        pub = item.findtext("pubDate") or item.findtext("published") or item.findtext("updated") or ""
        date_s = now.strftime("%Y-%m-%d")
        try:
            pd = parsedate_to_datetime(pub).replace(tzinfo=None)
            if pd < cutoff:
                continue
            date_s = pd.strftime("%Y-%m-%d")
        except Exception:
            pass
        out.append({"title": title, "category": f"rss:{name}", "date": date_s, "source": name})
    return out

def fetch_rss(days):
    """抓取官方博客 RSS。单个源失败不影响整体。"""
    items, now = [], datetime.now()
    for name, url in RSS_FEEDS:
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=20) as r:
                raw = r.read(300000).decode("utf-8", errors="ignore")
            got = _parse_rss_items(raw, name, days, now)
            items.extend(got)
            if got:
                print(f"[rss] {name}: {len(got)} 条")
        except Exception as e:
            print(f"[rss] 跳过 {name}: {type(e).__name__}")
    return items

def fetch_producthunt(days):
    """Product Hunt feed（可选源，失败跳过）。"""
    items, now = [], datetime.now()
    for url in ("https://www.producthunt.com/feed", "https://www.producthunt.com/topics/artificial-intelligence/feed"):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=20) as r:
                raw = r.read(300000).decode("utf-8", errors="ignore")
            got = _parse_rss_items(raw, "Product Hunt", days, now)
            items.extend(got)
            if got:
                print(f"[ph] {url}: {len(got)} 条")
        except Exception as e:
            print(f"[ph] 跳过: {type(e).__name__}")
    return items

def fetch_aihot(days):
    """直连 aihot 全量新闻（mode=all，API 上限100条/窗口），不依赖本地 news 精选文件。
    返回 [{title, category, date, source}]，参与通用 match() 匹配。"""
    from urllib.parse import urlencode
    items = []
    since = (datetime.now(CST) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S+08:00')
    url = "https://aihot.virxact.com/api/public/items?" + urlencode({'mode': 'all', 'since': since, 'take': 100})
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        arr = data.get("items", []) if isinstance(data, dict) else data
        for it in arr:
            pa = it.get("publishedAt", "")
            date_s = datetime.now().strftime("%Y-%m-%d")
            try:
                t = datetime.fromisoformat(pa)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                date_s = t.astimezone(CST).strftime("%Y-%m-%d")
            except Exception:
                pass
            items.append({"title": it.get("title", ""), "category": "aihot", "date": date_s, "source": "aihot"})
        if items:
            print(f"[aihot] 近 {days} 天全量: {len(items)} 条")
    except Exception as e:
        print(f"[aihot] 跳过: {type(e).__name__}")
    return items


def fetch_github_releases(tools, days=7):
    """对 tools.json 中带 github repo 链接的工具，拉取最新 Releases 作为权威版本信号。
    直接生成 candidates（title 为 'repo tag'，不含中文名，不走通用文本匹配）。
    只保留最近 days 天内的 release，过滤历史旧版本噪音。"""
    repos = {}
    for t in tools:
        u = t.get("official_url", "") or t.get("url", "") or ""
        m = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", u)
        if not m:
            continue
        repo = m.group(1).rstrip("/")
        if repo.lower() in ("features/copilot",):
            continue
        repos[t["slug"]] = (t.get("name", t["slug"]), repo)
    cutoff = datetime.now(CST) - timedelta(days=days)
    cands = []
    for slug, (display, repo) in repos.items():
        try:
            url = f"https://api.github.com/repos/{repo}/releases?per_page=15"
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
            with urlopen(req, timeout=15) as r:
                rels = json.loads(r.read().decode("utf-8"))
            for d in rels[:15]:
                tag = d.get("tag_name") or d.get("name") or ""
                if not tag:
                    continue
                pub = d.get("published_at") or d.get("created_at") or ""
                try:
                    tt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    if tt < cutoff:
                        continue  # 跳过历史旧版本
                    date_s = tt.strftime("%Y-%m-%d")
                except Exception:
                    continue  # 日期解析失败跳过，保持候选干净
                cands.append({
                    "slug": slug, "name": display, "version": tag,
                    "title": f"{repo} {tag}", "date": date_s,
                    "category": f"github:{repo}", "source": "github",
                    "matched_keyword": repo,
                })
        except Exception as e:
            print(f"[gh] 跳过 {repo}: {type(e).__name__}")
    if cands:
        print(f"[gh] {len(repos)} 个 repo 扫描，近 {days} 天命中 {len(cands)} 条 release 候选")
    return cands


def match(items, tools, only_slugs=None):
    """匹配候选：标题含工具名 且 含版本 token 且 含动作词。"""
    candidates = []
    # 工具名表（小写），过滤过短/泛化名
    name_map = []
    GENERIC_TOK = re.compile(r"^(ai|chat|gpt|app|bot|glm|kimi|claude|deepseek|gemini|grok|llm|api|ai助手|大模型|模型)$")
    for t in tools:
        nm = (t.get("name") or "").strip()
        if len(nm) < 2:
            continue
        # 排除过于泛化的名称（如 "AI"、"Chat"）
        if re.fullmatch(r"AI|ai|Chat|GPT|App|Bot", nm):
            continue
        name_map.append((t["slug"], nm, t.get("name")))
        # 扩展别名：seo_keywords 也参与匹配（如 "GLM-5.3" 命中 → glm-5-2，
        # 解决"竞品新闻句中匹配"漏检本体的问题，2026-08-19 GLM-5.3 事件；
        # 仅用 seo_keywords 而非 tags——tags 的"开源/Coding"等泛化词会大面积误报）
        for raw in (t.get("seo_keywords") or []):
            toks = raw if isinstance(raw, list) else re.split(r"[,，/\s]+", str(raw))
            for tok in toks:
                tok = str(tok).strip().lower()
                if len(tok) < 3 or len(tok) > 24:
                    continue
                if GENERIC_TOK.match(tok):
                    continue  # 单 token 泛化词跳过，避免全站误报
                name_map.append((t["slug"], tok, t.get("name")))
    name_map.sort(key=lambda x: -len(x[1]))  # 长名优先匹配

    for it in items:
        title = it["title"]
        title_l = title.lower()
        for slug, nm, display in name_map:
            if only_slugs and slug not in only_slugs:
                continue
            nl = nm.lower()
            # 词边界匹配，避免 "udio" 命中 "Qwen-Audio" 这类子串误报
            if not re.search(r"(?<![a-z0-9])" + re.escape(nl) + r"(?![a-z0-9])", title_l):
                continue
            versions = VERSION_RE.findall(title)
            # 去掉与工具名本身重合的 token（如工具名就是 "FLUX" 且标题 "FLUX 3" 仍算版本）
            vers = [v for v in versions if v.lower() != nl]
            has_action = any(w in title for w in ACTION_WORDS)
            if vers and has_action:
                candidates.append({
                    "slug": slug, "name": display,
                    "version": vers[0],
                    "title": title, "date": it["date"],
                    "category": it["category"],
                    "source": it.get("source", "news"),
                    "matched_keyword": display,
                })
    # 去重（同 slug 同 version 同 title）
    seen = set()
    out = []
    for c in candidates:
        k = (c["slug"], c["version"], c["title"])
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--slugs", nargs="*", default=None)
    ap.add_argument("--sources", default="rss,producthunt,aihot,github",
                    help="数据源组合: news,rss,producthunt,aihot,github（默认不含news，监控独立用aihot直连最新100条）")
    args = ap.parse_args()

    tools = load_tools()
    srcs = [s.strip() for s in args.sources.split(",") if s.strip()]

    items = []
    if "news" in srcs:
        items += load_news(args.days)
    if "rss" in srcs:
        items += fetch_rss(args.days)
    if "producthunt" in srcs:
        items += fetch_producthunt(args.days)
    if "aihot" in srcs:
        items += fetch_aihot(args.days)

    cands = match(items, tools, args.slugs)
    # GitHub 源直接产出 candidates（title 为 'repo tag'，不走文本匹配）
    if "github" in srcs:
        cands += fetch_github_releases(tools, args.days)
    # only_slugs 约束（github 候选同样受过滤）
    if args.slugs:
        cands = [c for c in cands if c["slug"] in args.slugs]
    cands.sort(key=lambda c: (c["date"], c["slug"]))

    result = {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "sources": srcs, "candidates": cands}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"扫描 {args.days} 天（源: {','.join(srcs)}），共 {len(items)} 条内容，命中 {len(cands)} 条版本更新候选 -> {args.out}")
    for c in cands:
        print(f"  [{c['date']}|{c['source']}] {c['slug']} -> 版本 {c['version']} | {c['title'][:60]}")

if __name__ == "__main__":
    main()

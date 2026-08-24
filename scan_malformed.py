import os, re, glob

ROOT = "C:/Users/27040/WorkBuddy/20260321092139/seo-site"
dirs = ["tools", "articles", "category", "compare", "alternatives", "ranking", "quiz", "live"]

# 真畸形：<hN 之后没有 > 且不是属性(name=)，直接接内容文字（CJK 或拉丁词但无 '='）
# 排除合法带属性标签：<h2 id="x"> <h1 style="..."> —— 用负向预查 (?![a-zA-Z]+=)
pat = re.compile(r'<h([1-6])\s+(?![a-zA-Z]+=)[^>]*?[一-鿿A-Za-z]', re.M)

found = []
total = 0
for d in dirs:
    base = os.path.join(ROOT, d)
    if not os.path.isdir(base):
        continue
    for fp in glob.glob(os.path.join(base, "**", "*.html"), recursive=True):
        if "_template" in fp:  # JS 模板占位，非真实页面
            continue
        total += 1
        try:
            txt = open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in pat.finditer(txt):
            s = max(0, m.start()-12)
            e = min(len(txt), m.start()+45)
            found.append((fp.replace(ROOT+os.sep, ""), txt[s:e].replace("\n", " ")))

print("扫描目录:", dirs, "(已排除 _template)")
print("文件总数:", total)
print("真·畸形标题标签命中:", len(found))
print("=" * 70)
for f, snip in found[:120]:
    print(f"[{f}]\n  {snip!r}\n")

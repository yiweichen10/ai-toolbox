#!/usr/bin/env python3
"""Quick verification of tools_en.json and articles_en.json"""
import json
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("TOOLS_EN.JSON VERIFICATION (59 tools)")
print("=" * 60)

tools = json.load(open("data/tools_en.json", "r", encoding="utf-8"))
issues = []

for t in tools:
    name = t["name"]
    desc = t.get("description", "")
    pros = t.get("pros", [])
    cons = t.get("cons", [])
    faq = t.get("faq", [])
    content = t.get("content", "")

    if len(desc) < 50:
        issues.append(f"{name}: description too short ({len(desc)} chars)")
    if len(pros) < 3:
        issues.append(f"{name}: pros < 3 ({len(pros)})")
    if len(cons) < 2:
        issues.append(f"{name}: cons < 2 ({len(cons)})")
    if len(faq) < 2:
        issues.append(f"{name}: faq < 2 ({len(faq)})")
    wc = len(content.split())
    if wc < 500:
        issues.append(f"{name}: content < 500 words ({wc})")
    if "[AUTO-GENERATE]" in json.dumps(t):
        issues.append(f"{name}: still has [AUTO-GENERATE]")
    if "## " not in content:
        issues.append(f"{name}: no H2 headings")

print(f"\nField issues: {len(issues)}")
for i in issues:
    print(f"  ! {i}")

words = [len(t.get("content", "").split()) for t in tools]
print(f"\nContent word counts:")
print(f"  Min: {min(words)}, Max: {max(words)}, Avg: {sum(words) // len(words)}")
print(f"  500-700: {sum(1 for w in words if 500 <= w < 700)}")
print(f"  700-1000: {sum(1 for w in words if 700 <= w < 1000)}")
print(f"  1000-1500: {sum(1 for w in words if 1000 <= w < 1500)}")
print(f"  >1500: {sum(1 for w in words if w >= 1500)}")

seo_checks = {"has_pricing": 0, "has_pros_cons": 0, "has_verdict": 0, "has_features": 0, "has_alternatives": 0}
for t in tools:
    c = t.get("content", "").lower()
    if "pricing" in c or "price" in c or "plan" in c:
        seo_checks["has_pricing"] += 1
    if "pros" in c or "advantage" in c:
        seo_checks["has_pros_cons"] += 1
    if "verdict" in c or "conclusion" in c or "final" in c:
        seo_checks["has_verdict"] += 1
    if "feature" in c:
        seo_checks["has_features"] += 1
    if "alternative" in c or " vs " in c:
        seo_checks["has_alternatives"] += 1

print(f"\nSEO elements in content:")
for k, v in seo_checks.items():
    pct = v * 100 // len(tools)
    status = "OK" if pct >= 90 else ("WARN" if pct >= 70 else "FAIL")
    print(f"  {k}: {v}/59 ({pct}%) [{status}]")

descs = [len(t.get("description", "")) for t in tools]
print(f"\nDescriptions:")
print(f"  Min: {min(descs)}, Max: {max(descs)}, Avg: {sum(descs) // len(descs)} chars")
short_descs = [t["name"] for t in tools if len(t.get("description", "")) < 80]
if short_descs:
    print(f"  Too short (<80 chars): {short_descs}")

faq_counts = [len(t.get("faq", [])) for t in tools]
print(f"\nFAQ per tool:")
print(f"  0: {sum(1 for f in faq_counts if f == 0)}")
print(f"  1: {sum(1 for f in faq_counts if f == 1)}")
print(f"  2+: {sum(1 for f in faq_counts if f >= 2)}")

print("\n" + "=" * 60)
print("ARTICLES_EN.JSON VERIFICATION")
print("=" * 60)

arts = json.load(open("data/articles_en.json", "r", encoding="utf-8"))
print(f"Total: {len(arts)} articles")

art_issues = []
for a in arts:
    slug = a.get("slug", "no-slug")
    title = a.get("title", "")
    if not title:
        art_issues.append(f"{slug}: missing title")
    if not a.get("date"):
        art_issues.append(f"{slug}: missing date")
    if not a.get("category"):
        art_issues.append(f"{slug}: missing category")
    desc = a.get("description", "")
    if len(desc) < 80:
        art_issues.append(f"{slug}: description < 80 chars ({len(desc)})")
    content = a.get("content", "")
    wc = len(content.split())
    if wc < 300:
        art_issues.append(f"{slug}: content < 300 words ({wc})")

print(f"\nField issues: {len(art_issues)}")
for i in art_issues:
    print(f"  ! {i}")

words = [len(a.get("content", "").split()) for a in arts]
print(f"\nWord counts:")
print(f"  Min: {min(words)}, Max: {max(words)}, Avg: {sum(words) // len(words)}")
print(f"  <500: {sum(1 for w in words if w < 500)}")
print(f"  500-1000: {sum(1 for w in words if 500 <= w < 1000)}")
print(f"  1000-1500: {sum(1 for w in words if 1000 <= w < 1500)}")
print(f"  1500-2000: {sum(1 for w in words if 1500 <= w < 2000)}")
print(f"  >2000: {sum(1 for w in words if w >= 2000)}")

seo_art = {"has_h2": 0, "has_conclusion": 0, "has_faq": 0, "has_list": 0, "has_comparison": 0}
for a in arts:
    c = a.get("content", "").lower()
    if "## " in c:
        seo_art["has_h2"] += 1
    if "conclusion" in c or "verdict" in c:
        seo_art["has_conclusion"] += 1
    if "faq" in c or "frequently" in c or "?" in c:
        seo_art["has_faq"] += 1
    if "- " in c or "1." in c:
        seo_art["has_list"] += 1
    if "compar" in c or " vs " in c:
        seo_art["has_comparison"] += 1

print(f"\nSEO structure:")
for k, v in seo_art.items():
    pct = v * 100 // len(arts) if arts else 0
    status = "OK" if pct >= 90 else ("WARN" if pct >= 70 else "FAIL")
    print(f"  {k}: {v}/{len(arts)} ({pct}%) [{status}]")

print(f"\nAll articles:")
for a in arts:
    wc = len(a.get("content", "").split())
    kw = a.get("keywords", "N/A")[:50]
    print(f"  [{wc:4d}w] {a.get('title', '')[:65]}")
    print(f"         keywords: {kw}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total_issues = len(issues) + len(art_issues)
if total_issues == 0:
    print("ALL CHECKS PASSED!")
else:
    print(f"Total issues: {total_issues} ({len(issues)} tools + {len(art_issues)} articles)")

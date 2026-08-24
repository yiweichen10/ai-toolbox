#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bing 关键词报告自动分析器
- 自动寻找 E:\\下载 下最新的 www.aitoollab.cn_KeywordReport_*.csv
- 生成四类词分析报告（漏网/赢家/机会/潜力）到 reports/keyword-reports/
- 定时提醒模式（--remind）：
    退出码 0 = 有最新数据且已生成报告
    退出码 2 = 超过 14 天没导出，提醒用户去导出
    退出码 1 = 出错
"""
import argparse
import csv
import glob
import os
import sys
from collections import Counter
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = r"E:\下载"
REPORT_DIR = os.path.join(BASE_DIR, "reports", "keyword-reports")
CSV_PATTERN = "www.aitoollab.cn_KeywordReport_*.csv"


def find_latest_csv():
    files = glob.glob(os.path.join(DOWNLOAD_DIR, CSV_PATTERN))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for idx, r in enumerate(csv.reader(f)):
            if idx == 0 or not r or not r[0].strip():
                continue
            try:
                rows.append({
                    "kw": r[0].strip(),
                    "imp": int(float(r[1])),
                    "clk": int(float(r[2])),
                    "ctr": float(r[3].rstrip("%")),
                    "pos": float(r[4]),
                })
            except (ValueError, IndexError):
                continue
    return rows


def bucket_label(r):
    imp = r["imp"]
    if imp >= 100000:
        return "大词(10万+)"
    if imp >= 10000:
        return "中词(1-10万)"
    if imp >= 1000:
        return "小词(1千-1万)"
    return "长尾(<1千)"


def pick(rows, cond, limit=15):
    out = [r for r in rows if cond(r)]
    out.sort(key=lambda r: -r["imp"])
    return out[:limit]


def fmt_row(r):
    return f"**{r['kw']}**：展示 {r['imp']:,}，点击率 {r['ctr']:.2f}%，平均排名 {r['pos']:.1f}"


def build_report(rows, src_name, generated_at):
    total_imp = sum(r["imp"] for r in rows)
    total_clk = sum(r["clk"] for r in rows)
    overall_ctr = total_clk / total_imp * 100 if total_imp else 0.0
    buckets = Counter(bucket_label(r) for r in rows)
    order = ["大词(10万+)", "中词(1-10万)", "小词(1千-1万)", "长尾(<1千)"]

    leak = pick(rows, lambda r: r["imp"] >= 10000 and r["ctr"] < 1.0)
    win = pick(rows, lambda r: r["imp"] >= 10000 and r["ctr"] >= 4.0)
    opp = pick(rows, lambda r: r["imp"] >= 5000 and r["pos"] <= 5 and r["ctr"] < 2.0)
    pot = pick(rows, lambda r: r["ctr"] >= 10.0 and r["imp"] < 10000)

    rank_lines = []
    for bound, label in [(3, "前3"), (5, "前5"), (10, "前10"), (20, "前20")]:
        n = sum(1 for r in rows if r["pos"] <= bound)
        rank_lines.append(f"{label}：{n} 词（{n / len(rows) * 100:.0f}%）")

    L = []
    A = L.append
    A(f"# Bing 关键词周报（{generated_at}）")
    A("")
    A(f"数据源：{src_name}")
    A(f"总词数 **{len(rows)}**｜总展示 **{total_imp:,}**｜总点击 **{total_clk:,}**｜整体点击率 **{overall_ctr:.2f}%**")
    A("")
    A("## 一、大盘分档")
    A("")
    A("| 档位 | 词数 | 展示 | 点击 | 点击率 |")
    A("|---|---|---|---|---|")
    for k in order:
        v = buckets.get(k, 0)
        imp = sum(r["imp"] for r in rows if bucket_label(r) == k)
        clk = sum(r["clk"] for r in rows if bucket_label(r) == k)
        ctr = clk / imp * 100 if imp else 0.0
        A(f"| {k} | {v} | {imp:,} | {clk:,} | {ctr:.2f}% |")
    A("")
    A("## 二、漏网词（展示大、点击差）——多半是品牌词，先判断值不值得救")
    A("")
    if leak:
        for r in leak:
            A(f"- {fmt_row(r)}")
    else:
        A("（无）")
    A("")
    A("## 三、赢家词（展示大、点击好）——代表内容，值得巩固和延伸")
    A("")
    if win:
        for r in win:
            A(f"- {fmt_row(r)}")
    else:
        A("（无）")
    A("")
    A("## 四、机会词（排名已进前5、点击没跟上）——优化标题/描述就能救")
    A("")
    if opp:
        for r in opp:
            A(f"- {fmt_row(r)}")
    else:
        A("（无）")
    A("")
    A("## 五、潜力词（点击率>=10%、展示还少）——金矿，新文章选题方向")
    A("")
    if pot:
        for r in pot:
            A(f"- {fmt_row(r)}")
    else:
        A("（无）")
    A("")
    A("## 六、收录健康度（平均排名分布）")
    A("")
    for line in rank_lines:
        A(f"- {line}")
    A("")
    A("## 七、本周行动建议")
    A("")
    A("1. **潜力词**：围绕上面第五部分的词延伸写 1-2 篇，标题直接带这些词。")
    A("2. **机会词**：给对应页面优化标题和首段，让描述更吸引人。")
    A("3. **漏网词**：如果全是品牌词（cursor/coze/zcode 这类），不用投入，Meta 已优化则观察即可。")
    A("4. 对比上次周报：上次的潜力词展示涨了吗？涨了说明方向对。")
    A("")
    A("---")
    A("*本报告由站点自动化生成，仅供内部决策参考。*")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Bing 关键词报告分析")
    ap.add_argument("--csv", help="指定CSV路径（默认自动找E:\\下载下最新的）")
    ap.add_argument("--remind", action="store_true", help="定时提醒模式：0=有报告 2=提醒导出 1=出错")
    args = ap.parse_args()

    csv_path = args.csv if args.csv else find_latest_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("没有找到关键词报告CSV（E:\\下载\\www.aitoollab.cn_KeywordReport_*.csv）")
        return 1

    mtime = os.path.getmtime(csv_path)
    age_days = (datetime.now() - datetime.fromtimestamp(mtime)).days
    rows = load_rows(csv_path)
    if not rows:
        print("CSV 解析失败，请检查格式")
        return 1

    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    content = build_report(rows, os.path.basename(csv_path), datetime.now().strftime("%Y-%m-%d"))
    out_path = os.path.join(REPORT_DIR, f"{stamp}.md")
    latest_path = os.path.join(REPORT_DIR, "latest.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"报告已生成：{out_path}")
    print(f"数据年龄：{age_days} 天")

    if args.remind:
        if age_days > 14:
            print("提醒：超过14天未导出关键词，请到 Bing 站长后台导出")
            return 2
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

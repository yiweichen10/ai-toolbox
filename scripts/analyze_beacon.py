#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_beacon.py — CPS beacon 曝光/点击数据分析（2026-08-15 新增）

数据源：nginx access log 中 /ads/beacon.gif 请求（由 ads/loader.js 的 cpsBeacon 发出）。
百度统计免费版无事件分析权限，本脚本为 CPS 转化漏斗的主数据源。

用法：
    python scripts/analyze_beacon.py                 # ssh 拉服务器 access.log 分析（默认最近 5 万条 beacon）
    python scripts/analyze_beacon.py --file a.log    # 分析本地日志文件
    python scripts/analyze_beacon.py --raw           # 附加输出最近 20 条原始 beacon 记录（调试用）

输出：总量 + 按渠道 / 页面类型聚合的曝光、点击、点击率 + 点击 TOP15 页面。
"""
import argparse
import io
import os
import re
import subprocess
import sys
from collections import Counter
from urllib.parse import urlparse, parse_qs

# Windows GBK 控制台编码兜底（AGENTS.md 铁律）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SERVER = "root@121.43.144.99"
SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519_aitoollab")  # 与 deploy.sh 一致

# 已知测试流量（8/15 端到端验证：curl 发模拟 impression+click），统计时剔除，避免污染 CTR
TEST_CHANNELS = {"test-channel"}
TEST_SLUGS = {"e2e-test2"}
# 站点独立日志（www server block）。注意：/var/log/nginx/access.log 只记非 www 的 301，
# 真实流量在这里；且 .gif 默认 access_log off，beacon 由 nginx 精确匹配 location 单独开日志。
LOG_PATH = "/var/www/aitoollab/logs/access.log"
LOG_DIR = "/var/www/aitoollab/logs"  # 日志每日 03:12 切割，历史进 access.log-YYYYMMDD.gz
HISTORY_DAYS = 14  # 拉取最近 N 天的 .gz 历史（周报看 7 天，留余量）
# 2026-09-01 起 beacon 路径改为 /reco/r.gif（规避 uBlock/AdGuard 拦截），
# 旧路径 /ads/beacon.gif 仍需兼容历史日志。两处必须同步：
#   ① ads/loader.js 的 CPS_BEACON_URL  ② /etc/nginx/conf.d/aitoollab.conf 的 /reco/ 块
BEACON_PATHS = r"/reco/r\.gif|/ads/beacon\.gif"
BEACON_RE = re.compile(r'"(?:GET|POST)\s+((?:' + BEACON_PATHS + r')\?[^"\s]*)\s+HTTP')
# 逐日漏斗口径：验证"广告拦截吃掉多少样本"，同时规避滚动窗口环比失真（周报必须用逐日数据比）
PAGE_RE = r'"GET /(tools|articles|news)/'
CFG_RE = r"/reco/data\.json|/ads/cps\.json"
CRAWLER_RE = r"bot|spider|crawler|headless|python|curl|wget|scrapy|axios|okhttp"


def parse_line(line):
    m = BEACON_RE.search(line)
    if not m:
        return None
    qs = parse_qs(urlparse(m.group(1)).query)
    return {k: v[0] for k, v in qs.items()}


def pct(c, i):
    return f"{c / i * 100:.2f}%" if i else "-"


def pad(s, width):
    """中英文混排简单对齐：中文按 2 宽度计。"""
    w = sum(2 if ord(c) > 127 else 1 for c in s)
    return s + " " * max(0, width - w)


def ssh_run(remote_cmd, timeout=120):
    """执行远程命令，返回 stdout；失败返回 None。"""
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
           SERVER, remote_cmd]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0 and not r.stdout:
        print(f"[ERROR] ssh 执行失败：{r.stderr[:300]}")
        return None
    return r.stdout


def run_funnel(days):
    """逐日漏斗：真人PV → 配置加载 → 曝光 → 点击。

    存在的意义有两个：
      1) 量化广告拦截损失：配置加载数 / 真人PV 明显低于 100% 即说明被拦（或脚本未执行）。
      2) 替代滚动窗口做环比：总量对比不可靠（窗口滑动会让总量不增反减），逐日对比才有效。

    2026-09-02 修正两个数据完整性 bug：
      a) logrotate 配了 delaycompress，最近一天的轮转文件是**未压缩的** access.log-YYYYMMDD
        （无 .gz），旧 glob `access.log-*.gz` 会漏掉它 → 每次分析都丢最近完整天。
      b) 旧版按"文件名日期"当天标日期，但文件实际覆盖 前日03:12→当日03:12，标签错位约 3 小时。
        现改为按日志行内 `[DD/Mon/YYYY]` 真实日期聚合（单遍 awk，服务器端完成）。
    """
    remote = (
        f"cd {LOG_DIR} && {{ "
        f"for f in $(ls -tr access.log-* 2>/dev/null | tail -n {days + 2}); do "
        f"  case \"$f\" in *.gz) zcat \"$f\" 2>/dev/null;; *) cat \"$f\" 2>/dev/null;; esac; done; "
        f"cat access.log 2>/dev/null; "
        f"}} | gawk -v days={days} '"
        "BEGIN {"
        "  m[\"Jan\"]=\"01\";m[\"Feb\"]=\"02\";m[\"Mar\"]=\"03\";m[\"Apr\"]=\"04\";"
        "  m[\"May\"]=\"05\";m[\"Jun\"]=\"06\";m[\"Jul\"]=\"07\";m[\"Aug\"]=\"08\";"
        "  m[\"Sep\"]=\"09\";m[\"Oct\"]=\"10\";m[\"Nov\"]=\"11\";m[\"Dec\"]=\"12\";"
        "  page=\"GET /(tools|articles|news)/\";"
        "  crawl=\"bot|spider|crawler|headless|python|curl|wget|scrapy|axios|okhttp\";"
        "  cfg=\"/reco/data[.]json|/ads/cps[.]json\";"
        "  beacon=\"/reco/r[.]gif|/ads/beacon[.]gif\";"
        "}"
        "{"
        "  dd=substr($4,2,2); mo=substr($4,5,3); yy=substr($4,9,4);"
        "  if (dd ~ /^[0-9][0-9]$/ && (mo in m)) {"
        "    d = yy m[mo] dd;"
        "    if ($0 ~ page && $0 !~ crawl) pv[d]++;"
        "    if ($0 ~ cfg) cfgc[d]++;"
        "    if ($0 ~ beacon && $0 ~ /act=impression/) imp[d]++;"
        "    if ($0 ~ beacon && $0 ~ /act=click/) clk[d]++;"
        "  }"
        "}"
        "END {"
        "  n=0; for (k in pv) if (k>0) ord[++n]=k;"
        "  for(i=1;i<=n;i++) for(j=i+1;j<=n;j++) if(ord[j]<ord[i]){t=ord[i];ord[i]=ord[j];ord[j]=t}"
        "  start = n > days ? n-days+1 : 1;"
        "  for(i=start;i<=n;i++){ d=ord[i];"
        "    print d, pv[d]+0, cfgc[d]+0, imp[d]+0, clk[d]+0;"
        "  }"
        "}'"
    )
    out = ssh_run(remote, timeout=300)
    if not out:
        return
    # 剔除今天（未完整日，口径见 MEMORY 铁律）；如需包含改传参
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    print("== 逐日漏斗（按日志行内真实日期聚合，不含当天未完整数据）==")
    print(f"{pad('日期', 14)}{'真人PV':>9}{'配置加载':>10}{'加载率':>9}{'曝光':>8}{'点击':>7}{'点击率':>9}")
    print("-" * 66)
    tp = tc = ti = tk = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        d, pv, cfg, imp, clk = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        if d == today:
            print(f"{pad(d + ' (今天,未完整,已剔除)', 30)}{pv:>7}{cfg:>10}{'-':>9}{imp:>8}{clk:>7}{'-':>9}")
            continue
        tp += pv; tc += cfg; ti += imp; tk += clk
        rate = f"{cfg / pv * 100:.0f}%" if pv else "-"
        print(f"{pad(d, 14)}{pv:>9}{cfg:>10}{rate:>9}{imp:>8}{clk:>7}{pct(clk, imp):>9}")
    if tp:
        print("-" * 66)
        print(f"{pad('合计', 14)}{tp:>9}{tc:>10}{f'{tc / tp * 100:.0f}%':>9}{ti:>8}{tk:>7}{pct(tk, ti):>9}")
        print(f"\n加载率 = 配置加载 / 真人PV。上限受 无JS/预取访问 稀释；"
              f"明显低于同类日说明被拦（或脚本未执行）。")


def main():
    ap = argparse.ArgumentParser(description="CPS beacon 曝光/点击分析")
    ap.add_argument("--file", help="本地 nginx 日志文件路径（不指定则 ssh 拉服务器）")
    ap.add_argument("--tail", type=int, default=50000, help="ssh 拉取时 grep 后保留的条数（默认 50000）")
    ap.add_argument("--raw", action="store_true", help="附加输出最近 20 条原始记录")
    ap.add_argument("--funnel", action="store_true",
                    help="输出逐日漏斗（真人PV / 配置加载 / 曝光 / 点击），"
                         "用于验证广告拦截比例与替代滚动窗口做周环比")
    ap.add_argument("--funnel-days", type=int, default=8, help="--funnel 回溯天数（默认 8）")
    args = ap.parse_args()

    if args.funnel:
        run_funnel(args.funnel_days)
        return

    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        source = args.file
    else:
        # 拉取：当前 access.log + 最近 N 天 .gz 历史（日志每日切割，只读当前会漏历史数据）
        # grep 必须同时匹配新旧 beacon 路径，否则改路径后统计直接归零
        remote_cmd = (
            f"{{ cat {LOG_PATH}; "
            f"find {LOG_DIR} -maxdepth 1 -name 'access.log-*.gz' -mtime -{HISTORY_DAYS} 2>/dev/null "
            f"| sort | xargs -r zcat 2>/dev/null; }} | grep -E '{BEACON_PATHS}' | tail -{args.tail}"
        )
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
               SERVER, remote_cmd]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 and not r.stdout:
            print(f"[ERROR] ssh 拉取日志失败：{r.stderr[:300]}")
            sys.exit(1)
        lines = r.stdout.splitlines()
        source = f"{SERVER}:{LOG_DIR}/access.log(+{HISTORY_DAYS}天.gz)"

    imp_ch, clk_ch = Counter(), Counter()
    imp_pt, clk_pt = Counter(), Counter()
    imp_slug, clk_slug = Counter(), Counter()
    total_imp = total_clk = 0
    parsed = 0
    skipped = 0  # 剔除的测试流量条数
    raw_records = []

    for ln in lines:
        d = parse_line(ln)
        if not d:
            continue
        parsed += 1
        act = d.get("act", "")
        ch = d.get("ch", "?")
        pt = d.get("pt", "?")
        slug = d.get("slug", "")
        # 测试流量剔除（ch=test-channel / slug=e2e-test2，curl 端到端验证产生）
        if ch in TEST_CHANNELS or slug in TEST_SLUGS:
            skipped += 1
            continue
        # 空 slug：仅 /news/ 汇总页会出现（URL 无 /news/{slug} 可提取），归类为 news-index
        if not slug:
            slug = "news-index（/news/汇总页）" if pt == "news" else "-"
        if args.raw:
            raw_records.append(d)
        if act == "impression":
            total_imp += 1
            imp_ch[ch] += 1
            imp_pt[pt] += 1
            imp_slug[slug] += 1
        elif act == "click":
            total_clk += 1
            clk_ch[ch] += 1
            clk_pt[pt] += 1
            clk_slug[slug] += 1

    print(f"== CPS Beacon 统计 ==")
    print(f"数据源：{source}（日志行 {len(lines)}，解析出 beacon {parsed} 条，剔除测试流量 {skipped} 条）")
    print(f"总曝光 {total_imp} / 总点击 {total_clk} / 总点击率 {pct(total_clk, total_imp)}\n")

    if parsed == 0:
        print("暂无 beacon 数据。可能原因：刚上线还没流量，或 loader.js 未生效。")
        print("验证：curl -sI 'https://www.aitoollab.cn/ads/beacon.gif?act=test&ch=manual&pt=test&ts=1'")
        return
    if total_imp == 0 and total_clk == 0:
        print("剔除测试流量后无有效 beacon 数据（全部为测试记录）。")
        return

    print(f"{pad('渠道', 16)}{'曝光':>8}{'点击':>8}{'点击率':>10}")
    print("-" * 44)
    for ch in sorted(set(list(imp_ch) + list(clk_ch))):
        print(f"{pad(ch, 16)}{imp_ch[ch]:>8}{clk_ch[ch]:>8}{pct(clk_ch[ch], imp_ch[ch]):>10}")

    print(f"\n{pad('页面类型', 16)}{'曝光':>8}{'点击':>8}{'点击率':>10}")
    print("-" * 44)
    for pt in sorted(set(list(imp_pt) + list(clk_pt))):
        print(f"{pad(pt, 16)}{imp_pt[pt]:>8}{clk_pt[pt]:>8}{pct(clk_pt[pt], imp_pt[pt]):>10}")

    top = sorted(clk_slug, key=lambda s: clk_slug[s], reverse=True)[:15]
    if top:
        print(f"\n== 点击 TOP{len(top)} 页面 ==")
        print(f"{pad('slug', 40)}{'曝光':>8}{'点击':>8}{'点击率':>10}")
        print("-" * 68)
        for s in top:
            print(f"{pad(s, 40)}{imp_slug[s]:>8}{clk_slug[s]:>8}{pct(clk_slug[s], imp_slug[s]):>10}")

    if args.raw and raw_records:
        print(f"\n== 最近 {min(20, len(raw_records))} 条原始记录 ==")
        for d in raw_records[-20:]:
            print(d)


if __name__ == "__main__":
    main()

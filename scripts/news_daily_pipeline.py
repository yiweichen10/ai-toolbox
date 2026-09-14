#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""news_daily_pipeline.py — AI 快讯日更「单一入口」串联器（2026-09-14 立规）

## 为什么要有它
快讯日更是「多个独立步骤 + 多处软门禁」拼起来的，每一步失败都能"静默降级"：
fetch 产出 category=null 没人拦、提炼后不校验 commentary、部署完不验线上。
事故只能靠人肉在下一期发现。本脚本把所有**确定性环节**串成一条命令，
任一步失败立即非零退出并给出可执行的原因，杜绝"带病上线"。

## 边界（关键，别误会）
Link 里有一段是**判断**，不是确定性代码，脚本串不了，必须 Agent 做：
  - 同日/跨天去重的最终裁定
  - 标题主体核对（上游 LLM 会把新闻主体张冠李戴）、事实浓缩与 commentary 撰写
所以流程是：脚本跑到「采集完 + 契约校验」→ 停 → Agent 做提炼 → 再跑本脚本续跑
（脚本按注释里的 `--from=build` 续跑，不重复采集）。'--check-only' 供 Agent 自检。

## 用法
  # 全链路（默认：fetch → 契约门禁 → 提炼检查 → build → deploy → 记录 → 线上验证）
  python scripts/news_daily_pipeline.py

  # Agent 提炼完只想跑后半段
  python scripts/news_daily_pipeline.py --from build

  # 只跑到契约校验为止（本地演练，不构建不部署）
  python scripts/news_daily_pipeline.py --until gate

  # 演练：只打印将执行什么
  python scripts/news_daily_pipeline.py --dry-run
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone, time as dtime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CST = timezone(timedelta(hours=8))
SITE = "https://www.aitoollab.cn"

STEPS = ["fetch", "gate", "build", "deploy", "log", "verify"]


def _run(cmd, step, cwd=BASE_DIR, env_extra=None):
    """跑子命令：失败即抛 RuntimeError（含 rc + 尾部输出），不静默吞错。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    print(f"\n=== [{step}] $ {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out.rstrip())
    if p.returncode != 0:
        raise RuntimeError(f"步骤 [{step}] 失败 rc={p.returncode}\n--- 输出尾部 ---\n{out[-1500:]}")
    return out


def _py():
    return sys.executable


def _latest_news_file():
    fs = sorted(glob.glob(os.path.join(BASE_DIR, "data", "news_*.json")))
    fs = [f for f in fs if not f.endswith(".bak")]
    return fs[-1] if fs else None


def _bash():
    import shutil
    for c in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe",
              os.path.expanduser("~/.workbuddy/binaries/PortableGit/versions/1.2.0/bin/bash.exe")):
        if c and os.path.exists(c):
            return c
    raise RuntimeError("找不到 bash，无法执行 deploy.sh")


# ── 步骤实现 ────────────────────────────────────────────────────────────────

def step_fetch(args):
    """1. 采集（幂等：文件已存在且有内容则跳过）

    采集端已内建**字段契约拦截**：上游条目缺 title/summary/category/source/source_url 时
    直接拒收（不猜值填补），名额由其他合格新闻补上。这里只负责把拦截情况显式报出来，
    并把"上游质量异常"与"正常防御"区分开。
    """
    out = _run([_py(), "scripts/fetch_aihot_news.py"], "fetch")
    fp = _latest_news_file()
    if not fp:
        raise RuntimeError("采集后仍无 data/news_*.json")
    items = json.load(open(fp, encoding="utf-8"))
    if not items:
        raise RuntimeError(f"采集结果为空：{os.path.basename(fp)}（上游无数据，本期不可发布）")
    n = len(items)
    print(f"  → 本期 {n} 条：{os.path.basename(fp)}")

    if "⛔ 字段契约拦截" in out:
        print("  ⚠️ 本期有上游条目被字段契约拒收（明细见上）。这是**防御生效**，不是缺陷被掩盖；"
              "但若连续多期发生或占比很高，属上游数据/采集策略问题 → 先分析根因，勿加兜底。")
    if n < 5:
        print(f"  ⚠️ 本期仅 {n} 条（历史常见 5-8 条）。若明显偏低，先分析：上游接口异常？"
              f"跨天去重口径过宽？字段拦截过多？**不要靠补条目凑数**。")
    return fp


def step_gate(args):
    """2. 契约门禁（硬伤即中止）+ 3. 提炼产物（commentary）完整性"""
    fp = _latest_news_file()
    if not fp:
        raise RuntimeError("找不到 data/news_*.json")
    # --fail：有任何硬伤直接 rc!=0，把问题挡在构建之前
    _run([_py(), "scripts/check_news_quality.py", "--today", "--fail"], "gate")

    items = json.load(open(fp, encoding="utf-8"))
    missing = [i.get("id") for i in items if not (i.get("commentary") or "").strip()]
    if missing and not args.skip_commentary_check:
        raise RuntimeError(
            f"共 {len(missing)} 条缺 commentary 原创评注：{missing}\n"
            "  → 这是 Agent 步骤1.5 的产物（脚本串不了）。请先完成要点提炼与评注撰写，"
            "或加 --skip-commentary-check 显式跳过（不推荐）。"
        )
    print(f"  → 契约通过：{len(items)} 条，字段齐全，评注在位")
    return fp


def step_build(args):
    """4. 数据感知增量构建（只渲染受影响页面，含首页与全量 sitemap）"""
    _run([_py(), "scripts/build.py", "--changed"], "build")


def step_deploy(args):
    """5. 增量部署，并以 .deploy_last_result.json 为唯一判定依据（不看 stdout 尾部）"""
    _run([_bash(), "deploy.sh", "--skip-build"], "deploy")
    rf = os.path.join(BASE_DIR, ".deploy_last_result.json")
    if not os.path.exists(rf):
        raise RuntimeError("部署后找不到 .deploy_last_result.json，结果不可判定")
    res = json.load(open(rf, encoding="utf-8"))
    if res.get("status") != "SUCCESS":
        raise RuntimeError(f"部署未成功：{res}")
    print(f"  → 部署 SUCCESS（commit={res.get('detail','')}）")
    return res


def step_log(args):
    """6. 记录流水线 + 刷新仪表盘"""
    today = datetime.now(CST)
    title = f"AI快讯 {today.strftime('%m-%d')}"
    _run([_py(), "scripts/pipeline_log.py", "ai_news", "ok", title,
          "快讯日更全链路（单一入口）"], "log")
    _run([_py(), "scripts/gen_cms.py"], "log")


def step_verify(args):
    """7. 线上验证：真实用户路径，不看本地产物"""
    import urllib.request
    day = datetime.now(CST).strftime("%Y-%m-%d")
    fp = _latest_news_file()
    n = len(json.load(open(fp, encoding="utf-8")))
    today = datetime.now(CST)
    body = None
    errors = []

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 news-pipeline-verify"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")

    # 允许期次页不是"今天"（脚本可能按数据文件日期校验）
    day = os.path.basename(fp).replace("news_", "").replace(".json", "")
    try:
        code, idx = get(f"{SITE}/news/")
        if code != 200:
            errors.append(f"/news/ HTTP {code}")
        if day not in idx:
            errors.append(f"/news/ 不含本期日期 {day}")
        code, page = get(f"{SITE}/news/{day}/")
        if code != 200:
            errors.append(f"/news/{day}/ HTTP {code}")
        if f"{n}条精选" not in page:
            errors.append(f"期次页不含「{n}条精选」")
        if "x.com/" in page:
            errors.append("期次页仍有 x.com 源链接（国内不可访问）")
        if page.count("news-item-title") < n:
            errors.append(f"期次页条目标题只渲染 {page.count('news-item-title')} 个，少于 {n}")
    except Exception as e:
        errors.append(f"线上请求异常：{e}")

    if errors:
        raise RuntimeError("线上验收未通过：\n  - " + "\n  - ".join(errors))
    print(f"  → 线上验收通过：{SITE}/news/{day}/ 「{n}条精选」，无 x.com 残留")


STEP_FN = {
    "fetch": step_fetch,
    "gate": step_gate,
    "build": step_build,
    "deploy": step_deploy,
    "log": step_log,
    "verify": step_verify,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default=STEPS[0], choices=STEPS,
                    help="从哪一步开始（Agent 提炼完可用 --from build）")
    ap.add_argument("--until", dest="until", default=STEPS[-1], choices=STEPS,
                    help="跑到哪一步为止（本地演练用 --until gate）")
    ap.add_argument("--skip-commentary-check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    i0, i1 = STEPS.index(args.frm), STEPS.index(args.until)
    if i0 > i1:
        print(f"❌ --from({args.frm}) 在 --until({args.until}) 之后")
        return 2
    plan = STEPS[i0:i1 + 1]
    print(f"[news_daily_pipeline] 计划执行：{' → '.join(plan)}")
    if args.dry_run:
        print("(--dry-run 仅打印，不执行)")
        return 0

    t0 = datetime.now()
    try:
        for s in plan:
            STEP_FN[s](args)
    except Exception as e:
        print(f"\n❌ 快讯日更链路中止于 [{s}]：{e}")
        print("\n── 先分析，别硬跑（2026-09-14 用户拍板）─────────────────────────")
        print("  本项目禁止用「默认值 / 猜测 / 静默跳过」把缺陷填上继续跑——那只会把显性问题")
        print("  变成下游的隐性错误，而且没人知道。正确姿势：")
        print("   1) 取证：把上面的原始输出读完，确认真实取值（用 repr() 区分 None / '' / 键不存在），"
              "别用真值判断猜")
        print("   2) 分侧定位：谁写坏的（生产侧）+ 谁放行的（门禁侧），两侧都要找到，只修一侧还会复发")
        print("   3) 判断根因类型：上游数据缺陷？选条策略错？契约没覆盖？边界没写？")
        print("   4) 只修根因；存量坏数据由人读过内容后判定写回（逐文件 .bak + 写后读回校验），"
              "不要用脚本猜值")
        print("   5) 复现验证通过后再重跑本链路的对应段（--from <step>），不要从头盲跑")
        print(f"\n  取证命令：{_py()} scripts/fetch_aihot_news.py --audit-fields   # 字段缺陷全库清单")
        print(f"           {_py()} scripts/check_news_quality.py --today       # 本期质量明细")
        return 1
    print(f"\n🎉 快讯日更全链路完成（{int((datetime.now()-t0).total_seconds())}s）："
          f"{SITE}/news/{os.path.basename(_latest_news_file()).replace('news_','').replace('.json','')}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

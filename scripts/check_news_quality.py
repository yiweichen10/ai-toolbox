#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_news_quality.py — AI 快讯质量门禁

检测快讯的"硬伤"，防止「标题截断 / 空摘要 / 英文标题 / 复述式无价值摘要」复发。

用法:
  python scripts/check_news_quality.py              # 检查全部快讯，输出报告
  python scripts/check_news_quality.py --today       # 只查最新一期
  python scripts/check_news_quality.py --fix         # 自动修复标题尾部标点（写回）
  python scripts/check_news_quality.py --fail        # 有硬伤则 exit 1（供 build 门禁）

判定:
  硬伤(FAIL)  = 空摘要 / 空标题 / 英文标题（中文占比 < 30%）
  警告(WARN)  = 标题尾部标点 / 摘要过长(>120字,疑似复述式) / 摘要无价值钩子

原则: 只拦截"明显不可读"的硬伤；"价值提炼"靠生成 prompt 治本，脚本只兜底不替代。
"""
import json
import glob
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CJK_RE = re.compile(r'[\u4e00-\u9fff]')
# 连续 >=3 个英文单词（空格分隔）视为"英文句子"，区别于夹在中文里的英文专名（GPT-5.6/Cursor/SpaceX）
EN_RUN_RE = re.compile(r'[A-Za-z][A-Za-z0-9.\-]*(?:\s+[A-Za-z][A-Za-z0-9.\-]*){2,}')
TRAIL_PUNCT = '。！？，、；：…!?.,;: '
# 中英文粘连：中文与 ASCII 字母直接相邻无空格（如 "Cursor并入SpaceX" / "iPhone备忘录" / "DAW靠拢"）。
# 数字与中文单位紧贴（38.3倍）是标准中文写法，不算粘连，故只查字母。
CJK_ASCII_GLUE_RE = re.compile(r'[\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u4e00-\u9fff]')
# 摘要空话词：AI 无信息量套话（"建议关注后续API降价"），出现即视为"价值提炼"失败
CLICHE_WORDS = (
    '建议关注', '建议你', '建议用户', '建议开发者', '建议音乐人', '建议立即', '建议尽快',
    '可关注', '推荐关注', '感兴趣可', '值得一试', '值得关注', '欢迎体验', '敬请期待', '密切关注',
)
# 价值钩子：摘要至少命中一类，否则大概率是"纯复述"
VALUE_HINTS = (
    '免费', '降价', '开源', '上线', '发布', '开放', '支持', '可用', '达到', '超越',
    '突破', '宣布', '收购', '融资', '涨价', '取消', '推出', '升级', '实测', '首次',
    '价格', '成本', '性能', '用户', '亿', '万', '%', '$', '元', '参数量', '上下文',
    '周', '倍', '条', '天', '小时', '美元', '篇', '次', '个', 'GB', 'GPU', '月', '秒',
)


def cjk_ratio(s):
    if not s:
        return 0
    return len(CJK_RE.findall(s)) / len(s)


def strip_tail(t):
    t = (t or '').strip()
    while t and t[-1] in TRAIL_PUNCT:
        t = t[:-1].rstrip()
    return t


def check_one(it):
    """返回 (fail_list, warn_list)"""
    fails, warns = [], []
    title = (it.get('title') or '').strip()
    summary = (it.get('summary') or '').strip()

    if not title:
        fails.append('空标题')
    if not summary:
        fails.append('空摘要')

    if title:
        # 英文标题 = 完全无中文（快讯标题中英混排、英文专名多是常态，只要含中文即可读）
        if EN_RUN_RE.search(title) and not CJK_RE.search(title):
            fails.append('英文标题(无任何中文)')
        if title[-1] in TRAIL_PUNCT:
            warns.append(f'标题尾部标点「{title[-1]}」')
        if CJK_ASCII_GLUE_RE.search(title):
            fails.append('标题中英文粘连(缺空格，如"Cursor并入")')

    if summary:
        if len(summary) > 90:
            warns.append(f'摘要过长({len(summary)}字,疑似复述式,目标≤60)')
        if len(summary) < 20:
            warns.append(f'摘要过短({len(summary)}字,疑似无信息)')
        if not any(h in summary for h in VALUE_HINTS):
            warns.append('摘要无价值钩子(无数字/结果/价格词)')
        hit_cliche = [w for w in CLICHE_WORDS if w in summary]
        if hit_cliche:
            warns.append(f'摘要空话词({"/".join(hit_cliche)})')
        if CJK_ASCII_GLUE_RE.search(summary):
            warns.append('摘要中英文粘连(缺空格)')

    # 2026-08-25 评注门禁（编辑整理+评注）：存量无 commentary 字段不警告，只查新增字段
    commentary = (it.get('commentary') or '').strip()
    if commentary:
        if len(commentary) < 30:
            warns.append(f'评注过短({len(commentary)}字,疑似敷衍)')
        hit_comm = [w for w in CLICHE_WORDS if w in commentary]
        if hit_comm:
            warns.append(f'评注空话词({"/".join(hit_comm)})')
        if summary and (summary[:20] in commentary or commentary[:20] in summary):
            warns.append('评注复述摘要(无信息增量)')

    return fails, warns


def load_files(today_only=False):
    files = sorted(glob.glob(os.path.join(BASE_DIR, 'data', 'news_*.json')))
    if today_only and files:
        files = files[-1:]
    return files


def _norm_title(t):
    """标题归一化：去空格/标点/大小写，用于同日重复检测"""
    return re.sub(r'[\s\-_—–·,，。.．:：;；!！?？()（）""''<>《》]', '', (t or '').lower())


def _dup_flags(items):
    """同文件内重复/近似标题检测。返回 {index: [flag,...]}"""
    flags = {}
    normed = [_norm_title(it.get('title', '')) for it in items]
    for i in range(len(normed)):
        n1 = normed[i]
        for j in range(i + 1, len(normed)):
            n2 = normed[j]
            if not n1 or not n2:
                continue
            if n1 == n2:
                flags.setdefault(i, []).append(f'与第{j+1}条标题完全相同(重复新闻)')
            elif (len(n1) > 6 and n1 in n2) or (len(n2) > 6 and n2 in n1):
                flags.setdefault(i, []).append(f'与第{j+1}条标题近似(疑似同一事件)')
    return flags


def _cross_day_dup_flags(fp, items):
    """跨天重复检测（2026-08-16 新增）：与前 3 天已发条目比对，
    同一事件连续多天报道（如 Qwen3.8 开源 08-13/14/15 连上 3 天）记 WARN。
    采集脚本 fetch_aihot_news.py 已做源头去重，此处为兜底报告。"""
    flags = {}
    try:
        from fetch_aihot_news import load_recent_signatures, is_seen
    except Exception:
        return flags
    fname = os.path.basename(fp)
    m = re.search(r'news_(\d{4}-\d{2}-\d{2})', fname)
    if not m:
        return flags
    sigs, urls = load_recent_signatures(m.group(1), days=3)
    if not sigs:
        return flags
    for idx, it in enumerate(items):
        if is_seen(it.get('title', ''), (it.get('source_url') or '').strip(), sigs, urls):
            flags.setdefault(idx, []).append('与前 3 天已发快讯疑似同一事件(跨天重复)')
    return flags


def main():
    args = sys.argv[1:]
    today_only = '--today' in args
    do_fix = '--fix' in args
    do_fail = '--fail' in args

    files = load_files(today_only)
    total = 0
    total_fail = 0
    total_warn = 0
    fix_count = 0

    for fp in files:
        fname = os.path.basename(fp).replace('news_', '').replace('.json', '')
        try:
            items = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            print(f'  ✗ {fname}: JSON 解析失败 {e}')
            continue

        changed = False
        dup_flags = _dup_flags(items)
        for k, v in _cross_day_dup_flags(fp, items).items():
            dup_flags.setdefault(k, []).extend(v)
        for idx, it in enumerate(items):
            total += 1
            fails, warns = check_one(it)
            for df in dup_flags.get(idx, []):
                warns.append(df)
            if fails:
                total_fail += 1
                print(f'  ✗ FAIL [{fname} {it.get("id","")}] {", ".join(fails)}')
                print(f'      标题: {(it.get("title") or "")[:50]}')
            if warns:
                total_warn += 1
                print(f'  △ WARN [{fname} {it.get("id","")}] {", ".join(warns)}')
                print(f'      标题: {(it.get("title") or "")[:50]}')
            # 自动修复：标题尾部标点
            if do_fix and it.get('title') and it['title'][-1] in TRAIL_PUNCT:
                new_t = strip_tail(it['title'])
                if new_t != it['title']:
                    it['title'] = new_t
                    changed = True
                    fix_count += 1

        if changed:
            json.dump(items, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f'  ↻ 已修复 {fname} 标题尾部标点')

    print(f'\n[news质量门禁] 共 {total} 条 / 硬伤 {total_fail} / 警告 {total_warn}' +
          (f' / 已修复标点 {fix_count}' if do_fix else ''))

    if do_fail and total_fail > 0:
        print('✗ 存在硬伤，构建门禁未通过（先修 data/news_*.json 或补 AI 改写）')
        sys.exit(1)
    if do_fail:
        print('✓ 门禁通过：无硬伤')


if __name__ == '__main__':
    main()

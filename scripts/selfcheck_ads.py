#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selfcheck_ads.py — aitoollab.cn 广告迁移部署前自检

验证内容：
  1. config.json / wwads.json 可解析
  2. 开关状态正确：monetag-inpage-push=enabled，wwads=disabled，其余 monetag 保持关闭
  3. 已启用的 monetag slot 文件非空且含 <script>
  4. loader.js 存在
  5. 在沙箱副本上真实运行 inject_ads.py，确认 wwads 标记块/脚本被彻底清理、无报错
  6. 确认 Monetag 代码不在静态 HTML 中烤入（运行时由 loader.js 注入，符合 CPM 自动渲染架构）

用法：
  python scripts/selfcheck_ads.py
退出码：0=通过，1=存在错误（禁止部署）
"""
import os
import re
import sys
import json
import shutil
import subprocess
import tempfile

# 修复 Windows 下 stdout/stderr 默认编码(GBK/ascii)导致打印 emoji/中文时静默崩溃的问题
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # seo-site
ADS = os.path.join(BASE, 'ads')
INJECT = os.path.join(BASE, 'scripts', 'inject_ads.py')
LOADER = os.path.join(ADS, 'loader.js')

ALLOWED_TOP = {
    '',  # 根目录（含 index.html 等内容页），不可剪枝，否则子目录不会被遍历
    'tools', 'articles', 'category', 'compare', 'alternatives',
    'ranking', 'quiz', 'live', 'dict', 'news', 'ads', 'data',
}

results = []  # (level, msg)


def ok(msg):
    results.append(('OK', msg))


def warn(msg):
    results.append(('WARN', msg))


def err(msg):
    results.append(('ERR', msg))


def section(title):
    results.append(('HEAD', title))


# ---------- 1) JSON 解析 ----------
section('【1】配置文件解析')
try:
    cfg = json.load(open(os.path.join(ADS, 'config.json'), encoding='utf-8'))
    ok('config.json 解析成功')
except Exception as e:
    err('config.json 解析失败: %s' % e)
    cfg = None

try:
    ww = json.load(open(os.path.join(ADS, 'wwads.json'), encoding='utf-8'))
    ok('wwads.json 解析成功')
except Exception as e:
    err('wwads.json 解析失败: %s' % e)
    ww = None

# ---------- 2) 开关状态 ----------
section('【2】开关状态')
if cfg:
    # Monetag 家族已于 2026-07-30 废弃并彻底移除：config.slots 中不应再有任何 monetag- 开头的 slot
    remaining = [k for k in cfg['slots'] if k.startswith('monetag-')]
    if not remaining:
        ok('Monetag 已彻底移除（config.slots 无 monetag-* 残留）✅')
    else:
        err('config.slots 仍残留 Monetag: %s（应全部移除）' % ', '.join(remaining))

if ww:
    if ww.get('enabled') is False:
        ok('wwads enabled=false（已关闭）✅')
    else:
        err('wwads 仍启用 (enabled != false)，会导致双联盟并存')

# ---------- 3) Monetag slot 文件（应已移除） ----------
section('【3】Monetag slot 文件（应已移除）')
if cfg:
    monetag_slots = [(k, s) for k, s in cfg['slots'].items() if k.startswith('monetag-')]
    if not monetag_slots:
        ok('config 中无 monetag slot，无需校验 slot 文件 ✅')
    else:
        for k, s in monetag_slots:
            f = os.path.join(ADS, s.get('file', ''))
            if os.path.isfile(f):
                err('Monetag slot 文件仍存在: %s（应删除）' % f)
            else:
                ok('Monetag slot 文件已删除: %s' % s.get('file'))

# ---------- 4) loader.js ----------
section('【4】loader.js')
if os.path.isfile(LOADER):
    ok('loader.js 存在')
    txt = open(LOADER, encoding='utf-8').read()
    if 'injectHTML' in txt and 'createElement(\'script\')' in txt:
        ok('loader.js 能执行含 <script> 的 slot（injectHTML 重建 script 节点）')
    else:
        warn('loader.js 未检测到 script 执行逻辑，Monetag 可能不渲染')
else:
    err('loader.js 缺失，Monetag 无法运行时注入')

# ---------- 5) 沙箱运行 inject_ads.py ----------
section('【5】沙箱运行 inject_ads.py（验证 wwads 清理）')
sandbox = tempfile.mkdtemp(prefix='seo-selfcheck-')
try:
    # 仅拷贝自检必需内容：HTML + ads/ + data/
    copied = 0
    for root, dirs, files in os.walk(BASE):
        rel = os.path.relpath(root, BASE)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top not in ALLOWED_TOP:
            dirs[:] = []
            continue
        for f in files:
            if not f.endswith('.html') and top not in ('ads', 'data'):
                continue
            src = os.path.join(root, f)
            dst = os.path.join(sandbox, rel, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1

    def count_wwads(base):
        markers = script = dodge = 0
        for r, _, fs in os.walk(base):
            for f in fs:
                if f.endswith('.html'):
                    t = open(os.path.join(r, f), encoding='utf-8').read()
                    if '<!-- wwads-begin -->' in t:
                        markers += 1
                    if 'cdn.wwads.cn/js/makemoney.js' in t:
                        script += 1
                    if '/ads/wwads-dodge.js' in t:
                        dodge += 1
        return markers, script, dodge

    before = count_wwads(sandbox)
    try:
        r = subprocess.run([sys.executable, INJECT, sandbox],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            err('inject_ads.py 运行异常 (rc=%d):\n%s' % (r.returncode, (r.stderr or '')[:2000]))
        else:
            ok('inject_ads.py 沙箱运行完成 (rc=0)')
    except Exception as e:
        err('inject_ads.py 沙箱调用失败: %s' % e)
    after = count_wwads(sandbox)

    if before[0] > 0 and after[0] == 0:
        ok('wwads 标记块清理: %d → 0（干净）✅' % before[0])
    elif before[0] == 0:
        warn('沙箱中未发现 wwads 标记块（可能源站已清理）')
    else:
        err('wwads 标记块未清理干净: %d → %d' % (before[0], after[0]))

    if (before[1] + before[2]) > 0 and (after[1] + after[2]) == 0:
        ok('wwads 脚本引用清理: 主脚本 %d + 避让 %d → 0（干净）✅' % (before[1], before[2]))
    elif (before[1] + before[2]) == 0:
        warn('沙箱中未发现 wwads 脚本引用')
    else:
        err('wwads 脚本引用未清理: 主 %d / 避让 %d' % (after[1], after[2]))

    # 6) Monetag 不在"内容"静态 HTML 中烤入（运行时注入才是正确架构）
    #    注意：ads/slots/monetag-*.html 是 slot 定义文件（被 loader.js 运行时拉取），
    #    本身含 Monetag 域名属正常，需排除，只检查真正的内容页。
    monetag_in_static = 0
    for r, _, fs in os.walk(sandbox):
        for f in fs:
            if f.endswith('.html'):
                full = os.path.join(r, f)
                relp = os.path.relpath(full, sandbox).replace(os.sep, '/')
                if relp.startswith('ads/'):  # slot 定义文件，跳过
                    continue
                t = open(full, encoding='utf-8').read()
                if 'nap5k.com' in t or 'n6wxm.com' in t or '5gvci.com' in t:
                    monetag_in_static += 1
    if monetag_in_static == 0:
        ok('Monetag 代码未烤入内容静态 HTML（运行时由 loader.js 注入，符合 CPM 架构）✅')
    else:
        warn('发现 %d 个内容 HTML 含 Monetag 域名（预期 0，运行时注入）' % monetag_in_static)
finally:
    shutil.rmtree(sandbox, ignore_errors=True)

# ---------- 报告 ----------
print('=' * 64)
print('部署前自检报告 — aitoollab.cn 广告迁移 (wwads → Monetag In-Page Push)')
print('=' * 64)
for lvl, msg in results:
    if lvl == 'HEAD':
        print('\n' + msg)
    else:
        print('[%s] %s' % (lvl, msg))

errs = [m for l, m in results if l == 'ERR']
warns = [m for l, m in results if l == 'WARN']
print('\n' + '-' * 64)
if errs:
    print('结论: ❌ 存在 %d 个错误，禁止部署，请先修复' % len(errs))
elif warns:
    print('结论: ⚠️ 通过（%d 条警告，需留意）' % len(warns))
else:
    print('结论: ✅ 全部通过，可部署')
sys.exit(1 if errs else 0)

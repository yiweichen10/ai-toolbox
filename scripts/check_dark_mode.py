#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_dark_mode.py — 部署前守卫：暗色模式"浅底+浅字"防复发检查

背景（2026-08-13）：暗色修复是白名单式枚举，Quiz/排行页卡片、CPS 推广卡、
文章正文内联浅底（pre/tr/p/div）等漏网，出现"浅底+浅字"看不清。
本脚本做静态守卫，防止模板/CSS/广告脚本改回去：
  1. Quiz 页页面级 <style> 的容器规则必须走 CSS 变量，不得写死浅色 background；
  2. 排行页 top3 卡片 / 深度解读区同理；
  3. ads/loader.js 必须带 [data-theme="dark"] .cps-card 暗色分支；
  4. css/style.min.css 必须包含正文内联浅底与 Quiz/排行/移动占位条兜底规则；
  5. （仅告警）扫描正文内联浅底元素数量，供内容管线参考，不阻断部署。
用法：python scripts/check_dark_mode.py
退出码：0=通过；1=存在硬编码浅底（禁止部署，deploy.sh set -e 会中断）
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 正文内联浅底（仅告警）
_INLINE_LIGHT = re.compile(
    r'<(pre|tr|p|div|td|li|blockquote)[^>]*style="[^"]*background(-color)?\s*:\s*'
    r'(#fff(fff)?|white|#ffffff|#f[0-9a-f]{5}|rgba?\(255\s*,\s*255\s*,\s*255)',
    re.I,
)
_LIGHT_HEX = re.compile(r'background(-color)?\s*:\s*#', re.I)


def _read(rel):
    with open(os.path.join(BASE, rel), encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _style_block(html, marker):
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.S):
        if marker in m.group(1):
            return m.group(1)
    return ''


def main():
    errors = []

    # 1) Quiz 页
    for page in sorted(
        f for f in __import__('glob').glob(os.path.join(BASE, 'quiz', '**', 'index.html'), recursive=True)
    ):
        rel = os.path.relpath(page, BASE).replace(os.sep, '/')
        html = _read(rel)
        block = _style_block(html, '.quiz-container')
        for cls in ('quiz-progress', 'quiz-question', 'quiz-intro', 'quiz-conclusion', 'tool-rec-detail'):
            rule = re.search(r'\.' + re.escape(cls) + r'\s*\{([^}]*)\}', block)
            if rule and _LIGHT_HEX.search(rule.group(1)):
                errors.append(f'{rel}: .{cls} 仍写死浅色背景：{rule.group(1).strip()[:80]}')

    # 2) 排行页
    for page in sorted(
        f for f in __import__('glob').glob(os.path.join(BASE, 'ranking', '**', 'index.html'), recursive=True)
    ):
        rel = os.path.relpath(page, BASE).replace(os.sep, '/')
        html = _read(rel)
        block = _style_block(html, '.rank-top3-card')
        for cls in ('rank-top3-card', 'ranking-table-wrap', 'ranking-table th'):
            rule = re.search(r'\.' + re.escape(cls) + r'\s*\{([^}]*)\}', block)
            if rule and _LIGHT_HEX.search(rule.group(1)):
                errors.append(f'{rel}: .{cls} 仍写死浅色背景：{rule.group(1).strip()[:80]}')
        sec = re.search(r'<section class="ranking-analysis"[^>]*>', html)
        if sec and 'var(--surface-2' not in sec.group(0):
            errors.append(f'{rel}: .ranking-analysis 区仍写死浅色背景：{sec.group(0)[:100]}')

    # 3) loader.js 暗黑分支
    loader = _read('ads/loader.js')
    if '[data-theme="dark"] .cps-card' not in loader:
        errors.append('ads/loader.js: 缺少 [data-theme="dark"] .cps-card 暗黑分支')

    # 4) style.min.css 兜底规则
    css = _read('css/style.min.css')
    required = (
        '[data-theme="dark"] .article-body pre[style*="background"]',
        ':root:not([data-theme="dark"]) .article-body pre[style*="background"]',
        '[data-theme="dark"] .quiz-question',
        '[data-theme="dark"] .rank-top3-card',
        '[data-theme="dark"] .mobile-ad-inline',
    )
    for needle in required:
        if needle not in css:
            errors.append(f'css/style.min.css: 缺少兜底规则 {needle}')

    # 5) 告警：正文内联浅底元素数量（CSS 已兜底，不阻断）
    inline_total = 0
    for top in ('articles', 'tools', 'compare'):
        for page in __import__('glob').glob(os.path.join(BASE, top, '**', 'index.html'), recursive=True):
            try:
                html = _read(os.path.relpath(page, BASE).replace(os.sep, '/'))
            except Exception:
                continue
            m = re.search(r'<article[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</article>', html, re.S)
            if m:
                inline_total += len(_INLINE_LIGHT.findall(m.group(1)))
    if inline_total:
        print(f'[warn] 正文内联浅底元素 {inline_total} 处（已由 style.min.css 暗黑/浅色兜底规则覆盖，仅提示内容管线）')

    if errors:
        print('暗色模式守卫未通过：')
        for e in errors:
            print(f'  ✗ {e}')
        sys.exit(1)
    print('✅ 暗色模式守卫通过：Quiz/排行页模板、loader.js、style.min.css 均无硬编码浅底')


if __name__ == '__main__':
    main()

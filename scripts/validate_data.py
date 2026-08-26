#!/usr/bin/env python3
"""validate_data.py — 构建前数据校验闸（G3，2026-08-23）

定位：fail-fast。在 build.py 入口与 deploy.sh 步骤 0 各跑一次，
脏数据（缺必填/重复 slug/格式错误）在进渲染前被拦下。

规则分级：
  ERROR → 退出码 1，中止构建（源头拦截）
  WARN  → 仅打印，不阻断（质量问题留给人/后续门禁）

用法：
  python scripts/validate_data.py             # tools + articles
  python scripts/validate_data.py --tools     # 仅 tools
  python scripts/validate_data.py --articles  # 仅 articles
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
# 2026-08-26 去单体化(任务#7): 真源为分片目录 data/tools/ data/articles/, 单体已退役。
TOOLS_FILE = os.path.join(DATA_DIR, 'tools')
ARTICLES_FILE = os.path.join(DATA_DIR, 'articles')

# Windows 控制台编码兜底（与 build.py 一致）
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ERRORS = []
WARNS = []


def err(msg):
    ERRORS.append(msg)
    print(f'[ERROR] {msg}')


def warn(msg):
    WARNS.append(msg)
    print(f'[WARN]  {msg}')


def load_json(path, label):
    # 2026-08-26 去单体化: path 为分片目录 data/tools|articles, 聚合所有 *.json
    import glob
    if os.path.isdir(path):
        out = []
        for fp in sorted(glob.glob(os.path.join(path, '*.json'))):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if isinstance(d, list):
                    out.extend(d)
                elif isinstance(d, dict):
                    out.append(d)
            except Exception as e:
                err(f'{label}: 分片 {os.path.basename(fp)} 解析失败: {e}')
        if out:
            return out
        err(f'{label}: 分片目录为空 {path}')
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and 'tools' in d:
            return d['tools']
        if isinstance(d, dict) and 'articles' in d:
            return d['articles']
        if isinstance(d, list):
            return d
        err(f'{label}: 顶层结构异常（期望 list 或 {{"tools":[...]}}）')
        return []
    except json.JSONDecodeError as e:
        err(f'{label}: JSON 解析失败: {e}')
        return []
    except FileNotFoundError:
        err(f'{label}: 文件不存在 {path}')
        return []
    except Exception as e:
        err(f'{label}: 读取失败: {e}')
        return []


SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


def validate_tools():
    tools = load_json(TOOLS_FILE, 'tools.json')
    if not tools:
        return
    print(f'[validate] tools.json: {len(tools)} 条')

    # 1. 必填字段
    for i, t in enumerate(tools):
        tag = f'tools[{i}]'
        slug = t.get('slug') if isinstance(t, dict) else None
        label = f'{tag}(slug={slug})' if slug else tag
        if not isinstance(t, dict):
            err(f'{label}: 不是对象（{type(t).__name__}）')
            continue
        for field in ('slug', 'name', 'category'):
            if not t.get(field):
                err(f'{label}: 必填字段缺失 "{field}"')
        # published=True 的内容完整性（内容为空 = 会渲染出空页）
        if t.get('published'):
            for field in ('description', 'content', 'url'):
                if not (t.get(field) or '').strip():
                    err(f'{label}: published 工具缺 "{field}"')

    # 2. slug 唯一 + 格式
    seen = {}
    for t in tools:
        if not isinstance(t, dict):
            continue
        slug = t.get('slug')
        if not slug:
            continue
        if slug in seen:
            err(f'重复 slug: "{slug}"（tools[{seen[slug]}] 与当前条目）')
        else:
            seen[slug] = len(seen)
        if not SLUG_RE.match(slug):
            warn(f'slug 格式可疑（建议小写字母/数字/连字符）: "{slug}"')

    # 3. 交叉引用完整性（related 指向的 slug 必须存在）
    for t in tools:
        if not isinstance(t, dict):
            continue
        related = t.get('related') or []
        if isinstance(related, str):
            related = [related]
        if not isinstance(related, list):
            continue
        for r in related:
            rslug = r.get('slug') if isinstance(r, dict) else r
            if isinstance(rslug, str) and rslug and rslug not in seen:
                warn(f'tools/{t.get("slug")} related 指向不存在: "{rslug}"')


DATE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2})$')


def validate_articles():
    arts = load_json(ARTICLES_FILE, 'articles.json')
    if not arts:
        return
    print(f'[validate] articles.json: {len(arts)} 条')

    # 1. 必填字段
    for i, a in enumerate(arts):
        tag = f'articles[{i}]'
        slug = a.get('slug') if isinstance(a, dict) else None
        label = f'{tag}(slug={slug})' if slug else tag
        if not isinstance(a, dict):
            err(f'{label}: 不是对象（{type(a).__name__}）')
            continue
        for field in ('slug', 'title'):
            if not (a.get(field) or '').strip():
                err(f'{label}: 必填字段缺失 "{field}"')
        # 正文：content 与 body 二选一（build.py 渲染回退逻辑一致）
        if not ((a.get('content') or '').strip() or (a.get('body') or '').strip()):
            err(f'{label}: 正文缺失（content 与 body 均为空）')
        # 日期格式（硬伤：搜索引擎/排序依赖）
        d = a.get('date', '')
        if d and not DATE_RE.match(str(d)):
            warn(f'{label}: 日期格式异常 "{d}"（期望 YYYY-MM-DD 或 MM/DD）')

    # 2. slug 唯一
    seen = set()
    for a in arts:
        if not isinstance(a, dict):
            continue
        slug = a.get('slug')
        if slug:
            if slug in seen:
                err(f'重复 slug: "{slug}"')
            seen.add(slug)


def main():
    only = None
    if '--tools' in sys.argv:
        only = 'tools'
    elif '--articles' in sys.argv:
        only = 'articles'

    if only in (None, 'tools'):
        validate_tools()
    if only in (None, 'articles'):
        validate_articles()

    print('-' * 50)
    if ERRORS:
        print(f'[validate] 校验失败: {len(ERRORS)} ERROR / {len(WARNS)} WARN → 中止')
        for e in ERRORS[:20]:
            print(f'  - {e}')
        if len(ERRORS) > 20:
            print(f'  ... 等 {len(ERRORS)} 条')
        return 1
    if WARNS:
        print(f'[validate] 校验通过（{len(WARNS)} WARN，不阻断）')
    else:
        print('[validate] 校验通过，数据干净')
    return 0


if __name__ == '__main__':
    sys.exit(main())

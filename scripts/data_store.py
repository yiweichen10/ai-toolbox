#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一数据存取层（数据化整为零核心）。

设计（解决单体全量重写 + 并发竞态 + 截断三害）：
- 写入：每实体一个文件 data/<type>/<slug>.json（各自独立，无竞态、最小爆炸半径）
- 单体同步：原子更新 data/<type>.json（temp+rename，防截断），供服务器后端 / 孤儿清理兼容
- 读取：目录优先聚合，回退单体

供发布脚本（publish_*）与维护脚本调用，替换直接 json.dump 整个单体。
"""
import os
import json
import tempfile

try:
    from filelock import FileLock
except ImportError:
    FileLock = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def _atomic_write_json(path, data, indent=2):
    """原子写：写临时文件后 os.replace 替换，避免写到一半被杀导致文件截断。"""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def _load_all(mono_name, dir_name):
    import glob
    d = os.path.join(DATA_DIR, dir_name)
    if os.path.isdir(d):
        files = sorted(glob.glob(os.path.join(d, '*.json')))
        if files:
            out = []
            for fp in files:
                try:
                    rec = json.load(open(fp, 'r', encoding='utf-8'))
                except Exception:
                    continue
                if isinstance(rec, list):
                    out.extend(rec)
                elif isinstance(rec, dict):
                    out.append(rec)
            return out
    mono = os.path.join(DATA_DIR, mono_name)
    if os.path.isfile(mono):
        with open(mono, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def _save_one(rec, mono_name, dir_name, indent=2):
    slug = rec.get('slug')
    if not slug:
        raise ValueError('记录缺少 slug，无法保存')
    d = os.path.join(DATA_DIR, dir_name)
    os.makedirs(d, exist_ok=True)
    # 1. 写小文件（每实体独立，无竞态）
    with open(os.path.join(d, f'{slug}.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=indent)
    # 2. 原子更新单体（服务器同步 / 孤儿清理兼容）
    # 2026-08-24 G6 并发锁：单体读-改-写加跨进程文件锁，防多自动化同刻写导致互相覆盖（丢字段）。
    # 小文件 <slug>.json 各自独立无需锁；锁只保护单体的全局读改写段。
    mono = os.path.join(DATA_DIR, mono_name)
    if os.path.isfile(mono):
        if FileLock is not None:
            lock = FileLock(mono + '.lock', timeout=30)
            with lock:
                _sync_mono(mono, rec, indent)
        else:
            _sync_mono(mono, rec, indent)
    return True


def _sync_mono(mono, rec, indent):
    """单体读-改-写（必须在文件锁内调用）。"""
    slug = rec.get('slug')
    try:
        all_rec = json.load(open(mono, 'r', encoding='utf-8'))
    except Exception:
        all_rec = []
    if not isinstance(all_rec, list):
        all_rec = []
    found = False
    for i, r in enumerate(all_rec):
        if isinstance(r, dict) and r.get('slug') == slug:
            all_rec[i] = rec
            found = True
            break
    if not found:
        all_rec.append(rec)
    _atomic_write_json(mono, all_rec, indent=indent)


def load_all_tools():
    return _load_all('tools.json', 'tools')


def load_all_articles():
    return _load_all('articles.json', 'articles')


def save_tool(tool, indent=4):
    """保存单个工具：写 data/tools/<slug>.json + 原子同步 tools.json。"""
    return _save_one(tool, 'tools.json', 'tools', indent=indent)


def save_article(article, indent=2):
    """保存单篇文章：写 data/articles/<slug>.json + 原子同步 articles.json。"""
    return _save_one(article, 'articles.json', 'articles', indent=indent)


def delete_tool(slug):
    p = os.path.join(DATA_DIR, 'tools', f'{slug}.json')
    if os.path.exists(p):
        os.remove(p)
    mono = os.path.join(DATA_DIR, 'tools.json')
    if os.path.isfile(mono):
        if FileLock is not None:
            with FileLock(mono + '.lock', timeout=30):
                _delete_from_mono(mono, slug, 4)
        else:
            _delete_from_mono(mono, slug, 4)


def delete_article(slug):
    p = os.path.join(DATA_DIR, 'articles', f'{slug}.json')
    if os.path.exists(p):
        os.remove(p)
    mono = os.path.join(DATA_DIR, 'articles.json')
    if os.path.isfile(mono):
        if FileLock is not None:
            with FileLock(mono + '.lock', timeout=30):
                _delete_from_mono(mono, slug, 2)
        else:
            _delete_from_mono(mono, slug, 2)


def _delete_from_mono(mono, slug, indent):
    """单体删记录（必须在文件锁内调用）。"""
    try:
        all_t = json.load(open(mono, 'r', encoding='utf-8'))
        if isinstance(all_t, list):
            all_t = [t for t in all_t if not (isinstance(t, dict) and t.get('slug') == slug)]
            _atomic_write_json(mono, all_t, indent=indent)
    except Exception:
        pass

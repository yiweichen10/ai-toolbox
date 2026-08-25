# -*- coding: utf-8 -*-
"""数据加载层（模块3，2026-08-24 从 build.py 抽离）。

包含：
  - get_category_slug
  - load_tools / load_articles（目录优先 + 单体回退）
  - get_tool_link_map / get_published_tool_slugs
  - load_compare_data / load_quiz_data / load_ranking_data / load_live_data
  - load_news_archive / _load_dict_terms

依赖：build_lib.html_utils._record_build_error、build.DATA_DIR、build.CATEGORY_SLUG_MAP。
CATEGORY_SLUG_MAP 用延迟 import 避免循环依赖。
"""
import os
import json
import glob

from build_lib.html_utils import _record_build_error


def _build_cfg():
    from build import DATA_DIR, CATEGORY_SLUG_MAP
    return DATA_DIR, CATEGORY_SLUG_MAP


def get_category_slug(category_name):
    """根据中文分类名生成SEO友好的英文slug。优先使用预设映射，否则使用拼音。"""
    DATA_DIR, CATEGORY_SLUG_MAP = _build_cfg()
    if category_name in CATEGORY_SLUG_MAP:
        return CATEGORY_SLUG_MAP[category_name]
    from pypinyin import pinyin, Style
    pinyin_list = pinyin(category_name, style=Style.NORMAL)
    slug = '-'.join([item[0] for item in pinyin_list if item and item[0].strip()]).lower()
    return slug


def load_tools():
    """目录优先加载工具数据。有 data/tools/*.json 则聚合，否则回退单体 tools.json。"""
    DATA_DIR, _ = _build_cfg()
    d = os.path.join(DATA_DIR, 'tools')
    if os.path.isdir(d):
        files = sorted(glob.glob(os.path.join(d, '*.json')))
        if files:
            out = []
            for fp in files:
                try:
                    rec = json.load(open(fp, 'r', encoding='utf-8'))
                except Exception as e:
                    _record_build_error('load_tools', fp, str(e))
                    continue
                if isinstance(rec, list):
                    out.extend(rec)
                elif isinstance(rec, dict):
                    out.append(rec)
                else:
                    _record_build_error('load_tools', fp, f'未知类型 {type(rec).__name__}')
            return out
    with open(os.path.join(DATA_DIR, 'tools.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def load_articles():
    """目录优先加载文章数据。有 data/articles/*.json 则聚合，否则回退单体 articles.json。"""
    DATA_DIR, _ = _build_cfg()
    d = os.path.join(DATA_DIR, 'articles')
    if os.path.isdir(d):
        files = sorted(glob.glob(os.path.join(d, '*.json')))
        if files:
            out = []
            for fp in files:
                try:
                    rec = json.load(open(fp, 'r', encoding='utf-8'))
                except Exception as e:
                    _record_build_error('load_articles', fp, str(e))
                    continue
                if isinstance(rec, list):
                    out.extend(rec)
                elif isinstance(rec, dict):
                    out.append(rec)
                else:
                    _record_build_error('load_articles', fp, f'未知类型 {type(rec).__name__}')
            return out
    with open(os.path.join(DATA_DIR, 'articles.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def sync_mono_from_shards(mono_name, dir_name, indent=2):
    """散文件目录 → 单体文件 幂等合并（build 前自动聚合兜底，2026-08-25）。

    背景：load_*() 目录优先后，自动化/旁路写散文件（data/<dir_name>/*.json）不再同步单体，
    导致依赖单体的下游（gen_cms / server.py / 检查脚本）读到陈旧数据。
    本函数在 build_target() 入口调用：把散文件目录合并回单体 data/<mono_name>，
    只增改不删除（保护单体中的历史记录）；无差异时零写入。
    返回：新增/变更条数（0 = 无需写盘）。
    """
    DATA_DIR, _ = _build_cfg()
    d = os.path.join(DATA_DIR, dir_name)
    if not os.path.isdir(d):
        return 0
    files = sorted(glob.glob(os.path.join(d, '*.json')))
    if not files:
        return 0
    # 1. 聚合散文件
    shards = []
    for fp in files:
        try:
            rec = json.load(open(fp, 'r', encoding='utf-8'))
        except Exception as e:
            _record_build_error(f'sync_{dir_name}', fp, str(e))
            continue
        if isinstance(rec, list):
            shards.extend(rec)
        elif isinstance(rec, dict):
            shards.append(rec)
    # 2. 读单体（异常回退空表，不阻断）
    mono_path = os.path.join(DATA_DIR, mono_name)
    try:
        with open(mono_path, 'r', encoding='utf-8') as f:
            mono = json.load(f)
    except Exception:
        mono = []
    if not isinstance(mono, list):
        mono = []
    # 3. 按 slug 合并：单体保序，散文件覆盖同名 + 追加新 slug
    by_slug = {}
    for r in mono:
        if isinstance(r, dict) and r.get('slug'):
            by_slug[r['slug']] = r
    changed = 0
    for r in shards:
        if not isinstance(r, dict) or not r.get('slug'):
            continue
        if by_slug.get(r['slug']) != r:
            by_slug[r['slug']] = r
            changed += 1
    # 4. 有差异才原子写回（temp + rename，防截断）
    if changed:
        tmp = mono_path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(list(by_slug.values()), f, ensure_ascii=False, indent=indent)
            os.replace(tmp, mono_path)
        except Exception as e:
            _record_build_error(f'sync_{dir_name}', mono_path, str(e))
    return changed


_TOOL_LINK_MAP = None
_LINK_STOPWORDS = {'AI', 'API', 'GPT', 'Chat', 'ChatGPT', '工具', '助手',
                   '人工智能', '大模型', '机器人', 'AI工具', 'APP', 'App', '软件'}


def get_tool_link_map():
    """返回 [(name, slug), ...] 用于正文行内内链，按名称长度降序以便最长优先匹配。"""
    global _TOOL_LINK_MAP
    if _TOOL_LINK_MAP is None:
        try:
            ts = load_tools()
        except Exception:
            ts = []
        m = []
        for t in ts:
            if not t.get('published', True):
                continue
            nm = (t.get('name') or '').strip()
            sl = t.get('slug')
            if nm and sl:
                m.append((nm, sl))
        m.sort(key=lambda x: len(x[0]), reverse=True)
        _TOOL_LINK_MAP = m
    return _TOOL_LINK_MAP


_PUBLISHED_TOOL_SLUGS = None


def get_published_tool_slugs():
    """返回已发布工具的 slug 集合。"""
    global _PUBLISHED_TOOL_SLUGS
    if _PUBLISHED_TOOL_SLUGS is None:
        try:
            _ts = load_tools()
            _PUBLISHED_TOOL_SLUGS = {t.get('slug') for t in _ts if t.get('published', True)}
        except Exception:
            _PUBLISHED_TOOL_SLUGS = set()
    return _PUBLISHED_TOOL_SLUGS


def load_compare_data():
    """加载对比数据文件"""
    DATA_DIR, _ = _build_cfg()
    compare_file = os.path.join(DATA_DIR, 'compare_data.json')
    if os.path.exists(compare_file):
        with open(compare_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"compares": [], "alternatives": [], "metadata": {}}


def load_quiz_data():
    """加载Quiz数据文件 (Phase 4)"""
    DATA_DIR, _ = _build_cfg()
    quiz_file = os.path.join(DATA_DIR, 'quiz_data.json')
    if os.path.exists(quiz_file):
        with open(quiz_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"quizzes": [], "metadata": {}}


def load_ranking_data():
    """加载排名数据文件 (Phase 5)"""
    DATA_DIR, _ = _build_cfg()
    ranking_file = os.path.join(DATA_DIR, 'ranking_data.json')
    if os.path.exists(ranking_file):
        with open(ranking_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"rankings": [], "metadata": {}}


def load_live_data():
    """加载 live dashboard 数据"""
    DATA_DIR, _ = _build_cfg()
    path = os.path.join(DATA_DIR, 'live_data.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    print(f'  [WARN] live_data.json not found at {path}')
    return {}


def load_news_archive():
    """加载 data/news_*.json 快讯归档，返回 (daily_dict, dates_list)。"""
    DATA_DIR, _ = _build_cfg()
    BASE_DIR = os.path.dirname(DATA_DIR)  # data_dir 的父目录即 BASE_DIR
    files = sorted(glob.glob(os.path.join(BASE_DIR, 'data', 'news_*.json')), reverse=True)
    daily = {}
    dates = []
    for fp in files:
        try:
            data = json.load(open(fp, 'r', encoding='utf-8'))
            date_str = os.path.basename(fp).replace('news_', '').replace('.json', '')
            daily[date_str] = data
            dates.append(date_str)
        except Exception:
            continue
    return daily, dates


def _load_dict_terms():
    """加载AI词典数据"""
    DATA_DIR, _ = _build_cfg()
    dict_data_path = os.path.join(DATA_DIR, 'dict_terms.json')
    if os.path.exists(dict_data_path):
        with open(dict_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 工具助手后端服务（零依赖，Python 3.6+）
=============================================
功能：
  1. 从 data/tools.json 构建内存检索索引（mtime 变化自动重载）
  2. POST /api/chat   关键词检索候选工具 + 调 LLM（千问 Qwen / 智谱 GLM）流式回答
  3. GET  /api/health 健康检查（工具数 / 模式 / 模型）
  4. 同 IP 限流 + 全局并发 1（免费档限制）排队，避免把上游打爆
  5. 每次问答写 JSONL 日志（供后续关键词调研）

配置（环境变量，或 /etc/aitoollab/ai-assistant.env）：
  DASHSCOPE_API_KEY    阿里云百炼（DashScope）API Key；配置后优先走千问
  QWEN_MODEL           千问主模型，默认 qwen3.8-max
  QWEN_MODEL_FALLBACKS 429/5xx 时降级模型（逗号分隔），默认 qwen-plus,qwen-turbo
  QWEN_API_BASE        默认 https://dashscope.aliyuncs.com/compatible-mode/v1
  QWEN_ENABLE_THINKING 千问深度思考开关，默认 0（更快更稳更省）
  DEEPSEEK_API_KEY     DeepSeek 官方 API Key（未走千问平台时启用）
  DEEPSEEK_USE_DASHSCOPE 置 1 时走千问/百炼平台调 deepseek 模型（复用 DASHSCOPE_API_KEY）
  DEEPSEEK_MODEL       默认 deepseek-v4-flash
  DEEPSEEK_MODEL_FALLBACKS 429/5xx 时降级模型（逗号分隔），默认空
  DEEPSEEK_ENABLE_THINKING 深度思考开关，默认 0
  ZHIPU_API_KEY        智谱 API Key（千问未配置时启用；两者都配置则互为降级）
  GLM_MODEL            智谱主模型，默认 glm-4.7-flash
  GLM_MODEL_FALLBACKS  429/5xx 时降级模型（逗号分隔），默认 glm-4-flash,glm-4-flash-250414
  GLM_API_BASE         默认 https://open.bigmodel.cn/api/paas/v4
  MODEL_COOLDOWN       某模型 429 后冷却秒数，默认 30
  ASSISTANT_HOST       默认 127.0.0.1
  ASSISTANT_PORT       默认 8123
  MAX_TOKENS           默认 1600
  TEMPERATURE          默认 0.6
  RATE_PER_MIN         每 IP 每分钟请求上限，默认 12
  QUEUE_TIMEOUT        全局排队超时秒数，默认 30
  TOOLS_JSON           工具数据路径
  LOG_FILE             问答日志路径

部署：scripts/deploy_assistant.sh
"""

from __future__ import print_function

import io
import hashlib
import json
import math
import os
import re
import sys
import time
import threading
import traceback
import urllib.request
import urllib.error
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
try:
    from http.server import ThreadingMixIn          # Python 3.7-3.12
except ImportError:
    from socketserver import ThreadingMixIn         # Python 3.13+（已移出 http.server）


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _load_env_file(path):
    """读取 KEY=VALUE 格式的 env 文件（忽略注释与空行）"""
    if not os.path.isfile(path):
        return {}
    out = {}
    with io.open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, _, v = line.partition('=')
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


_ENV_CANDIDATES = [
    '/etc/aitoollab/ai-assistant.env',          # 服务器正式配置
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),   # 本地开发
]
_FILE_CFG = {}
for _p in _ENV_CANDIDATES:
    _FILE_CFG.update(_load_env_file(_p))


def cfg(name, default=None):
    return os.environ.get(name) or _FILE_CFG.get(name) or default


HOST = cfg('ASSISTANT_HOST', '127.0.0.1')
PORT = int(cfg('ASSISTANT_PORT', '8123'))
# ---------------------------------------------------------------------------
# 上游 LLM 提供商：DeepSeek（可走千问平台）-> 千问 -> 智谱 GLM；均可通过 env 配置
# ---------------------------------------------------------------------------

def _split_models(raw, primary):
    out = []
    for _m in (raw or '').split(','):
        _m = _m.strip()
        if _m and _m != primary and _m not in out:
            out.append(_m)
    return out


GLM_KEY = (cfg('ZHIPU_API_KEY') or '').strip()
GLM_MODEL = cfg('GLM_MODEL', 'glm-4.7-flash')
GLM_MODEL_FALLBACKS = _split_models(
    cfg('GLM_MODEL_FALLBACKS', 'glm-4-flash,glm-4-flash-250414'), GLM_MODEL)
GLM_API_BASE = cfg('GLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4')

QWEN_KEY = (cfg('DASHSCOPE_API_KEY') or '').strip()
QWEN_MODEL = cfg('QWEN_MODEL', 'qwen3.8-max')
QWEN_MODEL_FALLBACKS = _split_models(
    cfg('QWEN_MODEL_FALLBACKS', 'qwen-plus,qwen-turbo'), QWEN_MODEL)
QWEN_API_BASE = cfg('QWEN_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
QWEN_ENABLE_THINKING = (cfg('QWEN_ENABLE_THINKING', '0') or '').strip().lower() in (
    '1', 'true', 'yes', 'on')

DEEPSEEK_KEY = (cfg('DEEPSEEK_API_KEY') or '').strip()
DEEPSEEK_MODEL = cfg('DEEPSEEK_MODEL', 'deepseek-v4-flash')
DEEPSEEK_MODEL_FALLBACKS = _split_models(
    cfg('DEEPSEEK_MODEL_FALLBACKS', ''), DEEPSEEK_MODEL)
DEEPSEEK_BASE_URL = cfg('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_USE_DASHSCOPE = (cfg('DEEPSEEK_USE_DASHSCOPE', '0') or '').strip().lower() in (
    '1', 'true', 'yes', 'on')
DEEPSEEK_ENABLE_THINKING = (cfg('DEEPSEEK_ENABLE_THINKING', '0') or '').strip().lower() in (
    '1', 'true', 'yes', 'on')

_PROVIDERS = []
if DEEPSEEK_USE_DASHSCOPE:
    # 千问/百炼平台也托管 deepseek 模型：复用 DASHSCOPE_API_KEY 与 DashScope 接口
    if QWEN_KEY:
        _PROVIDERS.append({
            'name': 'deepseek',
            'label': 'DeepSeek（千问平台）',
            'key': QWEN_KEY,
            'base': QWEN_API_BASE,
            'model': DEEPSEEK_MODEL,
            'fallbacks': DEEPSEEK_MODEL_FALLBACKS,
            'extra': {'enable_thinking': DEEPSEEK_ENABLE_THINKING},
        })
elif DEEPSEEK_KEY:
    _PROVIDERS.append({
        'name': 'deepseek',
        'label': 'DeepSeek',
        'key': DEEPSEEK_KEY,
        'base': DEEPSEEK_BASE_URL,
        'model': DEEPSEEK_MODEL,
        'fallbacks': DEEPSEEK_MODEL_FALLBACKS,
        'extra': {},
    })
if QWEN_KEY:
    _PROVIDERS.append({
        'name': 'qwen',
        'label': '千问',
        'key': QWEN_KEY,
        'base': QWEN_API_BASE,
        'model': QWEN_MODEL,
        'fallbacks': QWEN_MODEL_FALLBACKS,
        'extra': {'enable_thinking': QWEN_ENABLE_THINKING},
    })
if GLM_KEY:
    _PROVIDERS.append({
        'name': 'glm',
        'label': '智谱 GLM',
        'key': GLM_KEY,
        'base': GLM_API_BASE,
        'model': GLM_MODEL,
        'fallbacks': GLM_MODEL_FALLBACKS,
        'extra': {},
    })

API_KEY = QWEN_KEY or GLM_KEY
MODEL = _PROVIDERS[0]['model'] if _PROVIDERS else (QWEN_MODEL if QWEN_KEY else GLM_MODEL)
MODEL_FALLBACKS = _PROVIDERS[0]['fallbacks'] if _PROVIDERS else []

MODEL_COOLDOWN = float(cfg('MODEL_COOLDOWN', '30'))
RETRY_BACKOFFS = (1.0, 2.0, 4.0)          # 每次换模型前的短退避（秒）
MAX_TOKENS = int(cfg('MAX_TOKENS', '1600'))
TEMPERATURE = float(cfg('TEMPERATURE', '0.6'))
RATE_PER_MIN = int(cfg('RATE_PER_MIN', '12'))
QUEUE_TIMEOUT = float(cfg('QUEUE_TIMEOUT', '30'))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = cfg(
    'TOOLS_JSON',
    '/var/www/aitoollab/html/data/tools.json'
)
if not os.path.isfile(TOOLS_JSON):
    _local = os.path.join(BASE_DIR, 'data', 'tools.json')
    if os.path.isfile(_local):
        TOOLS_JSON = _local

LOG_FILE = cfg('LOG_FILE', '/var/www/aitoollab/logs/ai_assistant.log')
if not os.path.isdir(os.path.dirname(LOG_FILE)):
    _local_log = os.path.join(BASE_DIR, 'logs', 'ai_assistant.log')
    try:
        os.makedirs(os.path.dirname(_local_log), exist_ok=True)
    except OSError:
        pass
    LOG_FILE = _local_log

# 用户点赞数据（独立于部署目录，重建/覆盖不会丢）
LIKES_JSON = cfg('LIKES_JSON', '/var/www/aitoollab/data/tool_likes.json')
if not os.path.isdir(os.path.dirname(LIKES_JSON)):
    _local_likes = os.path.join(BASE_DIR, 'data', 'tool_likes.json')
    if os.path.isdir(os.path.dirname(_local_likes)):
        LIKES_JSON = _local_likes

LIKE_SALT = cfg('LIKE_SALT', 'aitoollab-like-salt-2026')
LIKE_DAILY_CAP = int(cfg('LIKE_DAILY_CAP', '25'))
LIKE_BURST_ALERT = int(cfg('LIKE_BURST_ALERT', '30'))

# 常见问题缓存（P0-1）：高频问题首轮命中直接返回，不再调上游
CACHE_TTL = int(cfg('CACHE_TTL', '21600'))   # 默认 6 小时
CACHE_MAX = int(cfg('CACHE_MAX', '200'))     # 最多缓存 200 条，超出淘汰最旧一半

# 回答反馈（P1-4）：用户对 AI 回答点"有用/没用"
FEEDBACK_JSON = cfg('FEEDBACK_JSON', '/var/www/aitoollab/data/ai_feedback.json')
if not os.path.isdir(os.path.dirname(FEEDBACK_JSON)):
    _local_fb = os.path.join(BASE_DIR, 'data', 'ai_feedback.json')
    if os.path.isdir(os.path.dirname(_local_fb)):
        FEEDBACK_JSON = _local_fb
FEEDBACK_RATE_PER_MIN = int(cfg('FEEDBACK_RATE_PER_MIN', '20'))
FEEDBACK_LOG_MAX = int(cfg('FEEDBACK_LOG_MAX', '5000'))

MOCK = cfg('MOCK_MODE', 'auto').lower()
if MOCK == 'auto':
    MOCK = (not API_KEY)
else:
    MOCK = (MOCK == '1' or MOCK == 'true')


# ---------------------------------------------------------------------------
# 工具库加载与检索
# ---------------------------------------------------------------------------

_INDEX_LOCK = threading.Lock()
_INDEX = {'tools': [], 'mtime': 0, 'loaded_at': 0}


def _is_free(tool):
    price = tool.get('price') or ''
    for tg in tool.get('tags') or []:
        if isinstance(tg, dict):
            txt = tg.get('text', '')
        elif isinstance(tg, str):
            txt = tg
        else:
            txt = ''
        low = txt.lower()
        if '免费' in txt or 'free' in low or '开源' in txt:
            return True
    low = price.lower()
    return '免费' in price or 'free' in low or '开源' in price


def _parse_visits(v):
    if not v:
        return 0.0
    s = str(v).strip()
    try:
        if '亿' in s:
            return float(s.replace('亿', '').strip()) * 1e8
        if '万' in s:
            return float(s.replace('万', '').strip()) * 1e4
        m = re.search(r'[\d.]+', s)
        return float(m.group()) if m else 0.0
    except (TypeError, ValueError):
        return 0.0


def _norm(s):
    return re.sub(r'[\s\u3000,，。、!！?？;；:：()（）[\]【】"\'"‘’“”\-–—]+', '', str(s or '')).lower()


def _load_tools(force=False):
    global _INDEX
    try:
        mtime = os.path.getmtime(TOOLS_JSON)
    except OSError:
        mtime = 0
    if not force and _INDEX['mtime'] == mtime and _INDEX['tools']:
        return _INDEX['tools']
    try:
        with io.open(TOOLS_JSON, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        if _INDEX['tools']:
            return _INDEX['tools']
        return []
    raw = data.get('tools', data) if isinstance(data, dict) else data
    likes_map = _load_likes()['counts']
    tools = []
    for t in raw:
        if not t.get('published', True):
            continue
        name = t.get('name') or ''
        slug = t.get('slug') or ''
        if not slug:
            continue
        tags = []
        for tg in t.get('tags') or []:
            if isinstance(tg, dict):
                tags.append(tg.get('text', ''))
            elif isinstance(tg, str):
                tags.append(tg)
        tags = [x for x in tags if x][:8]
        desc = (t.get('description') or '')[:260]
        positioning = (t.get('positioning') or '')[:180]
        price = (t.get('price') or '')[:180]
        platform = (t.get('platform') or '')[:120]
        tools.append({
            'name': name,
            'slug': slug,
            'category': t.get('category') or '',
            'tags': tags,
            'description': desc,
            'positioning': positioning,
            'price': price,
            'platform': platform,
            'free': _is_free(t),
            'likes': int(likes_map.get(slug, 0) or 0),
            'visits': _parse_visits(t.get('visits')),
            'rating': (t.get('rating') or ''),
            '_norm': _norm(' '.join([name] + tags)),
            '_name_norm': _norm(name),
            '_cat_norm': _norm(t.get('category') or ''),
            '_pos_norm': _norm(positioning),
            '_desc_norm': _norm(desc),
            '_plat_norm': _norm(platform),
        })
    _INDEX = {'tools': tools, 'mtime': mtime, 'loaded_at': time.time()}
    return tools


CATEGORY_ALIASES = {
    'AI对话': ['对话', '聊天', '问答', 'chat', '聊天机器人', '智能对话', '陪聊', '客服'],
    'AI写作': ['写作', '文案', '文章', '作文', '论文', '报告', '博客', '小红书', '公众号', '小说', '脚本', '润色'],
    'AI绘画': ['绘画', '画图', '绘图', '插画', '图生图', '文生图', '漫画', '动漫', 'logo', '图标'],
    'AI视频': ['视频', '数字人', '剪辑', '短视频', '文生视频', '图生视频', '影视', '口播', '数字分身'],
    'AI音频': ['音频', '音乐', '配音', '语音', '文字转语音', 'tts', '唱歌', '音效', '播客', '电台'],
    'AI编程': ['编程', '代码', '写代码', '开发', '程序员', 'coding', 'ide', '调试', 'bug', '前端'],
    'AI开发': ['开发', 'api', 'sdk', '模型', '部署', '训练', '微调', '集成'],
    'AI办公': ['办公', 'ppt', '文档', '表格', 'excel', 'word', '会议', '简历', '报告'],
    'AI效率': ['效率', '笔记', '纪要', 'todo', '任务', '时间管理', '整理'],
    'AI智能体': ['智能体', 'agent', '工作流', 'mcp', '机器人助手'],
    'AI自动化': ['自动化', 'rpa', '流程', '批量', '自动'],
    'AI检测': ['检测', '查重', 'ai检测', '降重', '识别', '去ai'],
    'AI学习': ['学习', '教育', '英语', '数学', '辅导', '考试', '课程', '口语', '学'],
    'AI提示词': ['提示词', 'prompt', '咒语'],
    'AI搜索': ['搜索', 'deep research', '研究', '调研', '资讯', '新闻', '查找'],
    'AI翻译': ['翻译', '英文', '多语言', '字幕', '译'],
    'AI行业应用': ['行业', '电商', '营销', '客服', '法律', '医疗', '金融', '教师', '销售'],
}

# 匹配时剔除的虚词（“免费”保留，它是重要意图词）
_FILLER = set('推荐哪个哪些什么有没有帮我求一个几款好用工具的吗呢啊吧咋怎么如何选适合想找找款能下些写做生成做视频图片文字声音语音代码')

# 二元词过滤：含这些虚词/功能字的 2 字词基本是噪音（“么好”“用的”“的工”），直接丢弃
_BIGRAM_STOP_CHARS = set(
    '的了么呢啊吧吗是和与或在就都很太真不没能会要想帮找给个款点下些种'
    '什么怎么如何推荐好用工具适合哪个哪些最好免费有这那之其然而却又被把让'
)


def _cjk_run_tokens(s):
    """把无空格的混合中英文按“连续汉字 / 连续非汉字”切段，
    汉字段再拆出 2 字子串，例如 “免费的ai写作工具” ->
    [免费, 费的, 的ai, ai, ai写, 写作, 作工, 工具]（后续会去虚词）。
    注意 2 字子串取全量会导致“的ai”这种跨段噪声，这里仅对汉字段内部取子串。
    """
    tokens = []
    runs = []
    cur = ''
    cur_cjk = None
    for ch in s:
        is_cjk = '\u4e00' <= ch <= '\u9fff'
        if cur and is_cjk != cur_cjk:
            runs.append((cur, cur_cjk))
            cur = ''
        cur += ch
        cur_cjk = is_cjk
    if cur:
        runs.append((cur, cur_cjk))
    for run, is_cjk in runs:
        if len(run) < 2:
            continue
        if is_cjk:
            tokens.append(run)                      # 整段（如“写作工具”）
            for i in range(len(run) - 1):
                bigram = run[i:i + 2]
                if bigram[0] in _BIGRAM_STOP_CHARS or bigram[1] in _BIGRAM_STOP_CHARS:
                    continue
                tokens.append(bigram)               # 二字词（如“写作”“降重”）
        else:
            tokens.append(run.lower())              # 英文/数字串（如 deepseek）
    return tokens


def _split_terms(query):
    q = query.lower()
    terms = [x for x in re.split(r'[\s,，。、!！?？;；:：()（）[\]【】]+', q) if x]
    # 中文短语整体也是一个强信号（如“免费写作”）
    compact = _norm(q)
    if len(compact) >= 2:
        terms.append(compact)
    terms.extend(_cjk_run_tokens(compact))
    cleaned = []
    for t in terms:
        if len(t) < 2:
            continue
        if t in _FILLER:
            continue
        if t not in cleaned:
            cleaned.append(t)
    return cleaned


def _detect_categories(query):
    q = query.lower()
    hits = []
    for cat, aliases in CATEGORY_ALIASES.items():
        for a in aliases:
            if a and a in q:
                hits.append(cat)
                break
    return hits


def _rating_num(t):
    m = re.search(r'[\d.]+', str(t.get('rating') or ''))
    try:
        return min(max(float(m.group()), 0.0), 5.0)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def _reputation(t):
    """口碑分：编辑评分 + 访问热度 + 用户点赞（各自封顶，避免单维失控）"""
    r = min(_rating_num(t) * 1.2, 6.0)
    v = min(math.log10(t['visits'] + 1.0) * 0.7, 3.5)
    l = min(math.sqrt(t['likes']) * 0.5, 2.5)
    return r + v + l


def _quality(t):
    """综合质量分：模糊查询（“有什么好用的”）时的口碑排序依据"""
    r = min(_rating_num(t) * 1.5, 7.5)
    v = min(math.log10(t['visits'] + 1.0) * 1.0, 5.0)
    l = min(math.sqrt(t['likes']) * 0.8, 4.0)
    return r + v + l


# ---------------------------------------------------------------------------
# 属性排序意图路由（B 类）：用户要“按某个属性挑/排”工具时，
# 不走相关性截断（top14），而是对全量工具按属性排序返回，保证 LLM 视野正确。
# 这是修复“筛选名字最长的工具却答不对”的根因：之前 LLM 只看到 top14 相关候选。
# ---------------------------------------------------------------------------
# 属性维度：key -> (匹配词元组, 排序 lambda, 是否降序, 人类可读标签)

def _price_num(price):
    """从价格字符串提取金额数值（'￥99/月'->99.0；免费->0.0；无法解析（停服/未公开/只有日期）->None）。
    返回 None 便于排序时把“无法定价”的工具沉底，避免“最贵/最便宜”被无效数据污染。
    关键点：只认带货币符号或货币/时间单位的数字，排除年份/日期数字（如“2026-04-26 停服”里的 2026）。"""
    if not price:
        return 0.0
    text = str(price)
    # 优先匹配带货币符号的金额
    money = re.findall(r'[￥¥$\u20ac\u00a5]\s*([\d]+(?:\.[\d]+)?)', text)
    if money:
        return max(float(n) for n in money)
    # 其次匹配“数字+货币/时间单位”的金额（如 99/月、9.9美元、39元）
    unit = re.findall(r'([\d]+(?:\.[\d]+)?)\s*(?:元|块|刀|美元|美金|欧元| RMB|rmb|usd|eur|/月|/年|/次|/天|每月|每年|月付|年付|month|year|mo|yr)', text)
    if unit:
        return max(float(n) for n in unit)
    return None   # 无货币上下文（如“已停服”“官网未公开”）-> 沉底


def _price_sort_key(t):
    """价格排序键：可解析价格返回数值；无法定价（停服/未公开）返回 None，
    由 retrieve_attr 里的 sentinel 统一沉底（升序沉末尾、降序沉末尾）。"""
    return _price_num(t['price'])


_ATTR_DIMS = [
    ('name_len', ('名字最长', '名称最长', '最长的名字', '名字长度', '名称长度', '名字字数', '字数最多', '名字最长', '哪个名字最长'),
     lambda t: len(t['name']), True, '名字长度（长→短）'),
    ('name_len_asc', ('名字最短', '名称最短', '最短的名字', '名字最短', '哪个名字最短'),
     lambda t: len(t['name']), False, '名字长度（短→长）'),
    ('price_desc', ('最贵', '价格最高', '收费最高', '最贵的', '价格最贵', '最贵的工具'),
     _price_sort_key, True, '价格（高→低）'),
    ('price_asc', ('最便宜', '价格最低', '最实惠', '最便宜的', '收费最低'),
     _price_sort_key, False, '价格（低→高）'),
    ('tags_most', ('标签最多', '标签最多的', '标签数最多', '分类最多', '最多的标签'),
     lambda t: len(t['tags']), True, '标签数量（多→少）'),
    ('tags_least', ('标签最少', '标签最少的', '标签数最少'),
     lambda t: len(t['tags']), False, '标签数量（少→多）'),
    ('visits_desc', ('访问最多', '最热门', '访问量最高', '热度最高', '最多的访问', '最火的', '访问量最多'),
     lambda t: t['visits'], True, '访问热度（高→低）'),
    ('likes_desc', ('点赞最多', '点赞最高的', '喜欢最多', '被赞最多', '点赞数最多'),
     lambda t: t['likes'], True, '用户点赞数（多→少）'),
    ('rating_desc', ('评分最高', '评分最高的', '评价最好', '分最高的', '评分最高'),
     lambda t: _rating_num(t), True, '编辑评分（高→低）'),
]


def _classify_attr_intent(query):
    """识别是否为“按属性排序/筛选”意图；返回维度元组或 None。"""
    q = query.lower()
    for key, words, fn, desc, label in _ATTR_DIMS:
        for w in words:
            if w in q:
                return key, words, fn, desc, label
    return None


def retrieve_attr(intent, top_n=14):
    """属性排序分支：对全量工具按指定维度排序，返回 top_n（不截断到相关性）。
    无效定价（None）无论升/降序都沉底，避免“最便宜”把停服/未公开工具顶到第一。"""
    tools = _load_tools()
    if not tools:
        return [], []
    _, _, fn, desc, label = intent
    if label.startswith('价格'):
        # 价格维度：None（无法定价）统一沉底。
        # 降序（最贵）时 None 应为最小（-inf）沉底；升序（最便宜）时 None 应为最大（+inf）沉底。
        sentinel = float('-inf') if desc else float('inf')
        ranked = sorted(tools, key=lambda t: (fn(t) if fn(t) is not None else sentinel),
                        reverse=desc)
    else:
        ranked = sorted(tools, key=fn, reverse=desc)
    return ranked[:top_n], [label]   # 第二个元素复用 cats 槽位，前端无副作用


def retrieve(query, top_n=14):
    """检索候选工具。
    1) 先看是否“按属性排序/筛选”意图（B 类：名字最长/最贵/标签最多…），
       命中则对全量工具按属性排序返回，LLM 视野不受 top14 截断限制；
    2) 否则走 A 类：相关性打分 + 口碑分加权 + 意图加成。付费不减分；
       用户明确要免费时才做免费方向加分。
    返回 (候选列表, 命中分类/排序说明)。"""
    # —— B 类路由：属性排序意图优先（避免被相关性截断坑掉）——
    attr_intent = _classify_attr_intent(query)
    if attr_intent:
        return retrieve_attr(attr_intent, top_n)
    tools = _load_tools()
    if not tools:
        return [], []
    ql = query.lower()
    terms = _split_terms(query)
    cats = _detect_categories(query)
    free_intent = ('免费' in query) or ('free' in ql) or ('0元' in query)
    cn_intent = ('国内' in query) or ('直连' in query) or ('翻墙' in query) or ('不用翻墙' in query) or ('中文' in query)

    scored = []
    for t in tools:
        s = 0.0
        if t['_name_norm'] == _norm(query) and t['_name_norm']:
            s += 30
        if t['_name_norm'] and t['_name_norm'] in ql:
            s += 10
        for term in terms:
            if term in t['_name_norm']:
                s += 8
            if term in t['_cat_norm']:
                s += 6
            for tag in t['tags']:
                tn = _norm(tag)
                if tn and term in tn:
                    s += 5
                    break
            if term in t['_pos_norm']:
                s += 3
            if term in t['_desc_norm']:
                s += 2
            if term in t['_plat_norm']:
                s += 1
        for c in cats:
            if t['category'] == c:
                s += 7
        if free_intent and t['free']:
            s += 4
        if cn_intent and ('国内' in t['platform'] or '中文' in t['platform']):
            s += 3
        if s > 0:
            # 口碑分加权 0.4：相关性仍主导，但口碑能帮“弱相关但很好用”的工具浮上来
            scored.append((s + _reputation(t) * 0.4, t))

    if not scored:
        # 无任何命中（如“有什么好用的”）：按综合质量分（口碑）排序
        hot = sorted(tools, key=_quality, reverse=True)[:top_n]
        return hot, cats

    scored.sort(key=lambda x: (-x[0], -x[1]['visits']))
    picked = [t for _, t in scored[:top_n]]
    # 双轨保底：确保候选里免费/付费都有，避免某一档被口碑分挤掉
    if len(picked) >= 2:
        has_free = any(t['free'] for t in picked)
        has_paid = any(not t['free'] for t in picked)
        if not has_free or not has_paid:
            need = 'free' if not has_free else 'paid'
            rest = [t for _, t in scored if t not in picked]
            best = next((t for t in rest if (t['free'] if need == 'free' else not t['free'])), None)
            if best is None:
                best = next((t for t in sorted(tools, key=_quality, reverse=True)
                             if (t['free'] if need == 'free' else not t['free']) and t not in picked), None)
            if best is not None:
                picked[-1] = best
    return picked, cats


# ---------------------------------------------------------------------------
# 提示词与 LLM 调用（千问 / GLM）
# ---------------------------------------------------------------------------

def _candidate_json(t):
    base = _name_aliases(t['name'])[1] if len(_name_aliases(t['name'])) > 1 else t['name']
    return {
        'name': t['name'],
        'short_name': base,
        'slug': t['slug'],
        'category': t['category'],
        'free': t['free'],
        'price': t['price'],
        'tags': t['tags'][:5],
        'description': t['description'],
        'positioning': t['positioning'],
    }


def build_system_prompt(candidates, all_count):
    payload = json.dumps([_candidate_json(t) for t in candidates], ensure_ascii=False)
    return (
        '你是「AI工具宝箱」(aitoollab.cn) 的 AI 选工具助手。用户会提出工具需求，'
        '你只能从下方候选工具清单中挑选 2-5 款推荐，绝不允许编造清单之外的任何工具。\n\n'
        '硬性规则：\n'
        '1. 只能推荐候选清单里的工具，链接格式必须是 [工具名](/tools/slug/)，slug 用清单里的值；'
        '工具名请用清单里的短名（short_name，若提供），不要加括号注释或版本后缀。\n'
        '2. 每款工具输出格式：\n'
        '   **[工具名](/tools/slug/)**\n'
        '   - 一句话推荐理由（贴合用户具体需求，不要泛泛而谈）\n'
        '   - 分类：xx ｜ 价格：xx\n'
        '3. 若候选清单里没有符合需求的工具，如实说“目前收录的 %d 款工具里没有完全匹配的”，'
        '再给出最接近的 1-2 款或下一步建议，不要硬推。\n'
        '4. 用简体中文回答，简洁、口语化、站在用户角度，不要客套话和开场白。\n'
        '5. 用户问“哪个最好/推荐几个/怎么选”时，优先推口碑好的：评分高、访问热度高、'
        '用户点赞（likes）多的工具优先；不要因为工具付费就贬低它，收费通常意味着功能更强，'
        '口碑好的付费工具同样值得推荐。\n'
        '6. 只有用户明确提到“免费/不要钱”时，才优先选 free=true 的工具并如实标注价格；'
        '其他情况付费与免费一视同仁，按口碑和相关性推荐。\n'
        '7. 当用户没有明确要求免费时，推荐默认分两档输出：\n'
        '   「免费/高性价比」1-2 款 + 「功能最强/预算充足」1-2 款，'
        '每款标注价格，并简单说明两档差异（例如：预算有限选 X，追求最强体验选 Y）；'
        '若候选清单里某一档确实没有合适的，如实说明，不要硬凑。\n'
        '8. 不要输出候选清单以外的工具信息，不要虚构价格、功能或评分。\n'
        '9. 若用户问与选工具无关的话题（闲聊、写代码请求等），用一两句简短回应，'
        '然后引导回“帮你选工具”。\n'
        '10. 若用户问“名字最长/最贵/标签最多/访问最多/点赞最多/评分最高”等'
        '“按属性挑/排”的问题，下方候选清单已是按该属性排序后的全量 Top 结果'
        '（不是相关性检索）。请直接基于清单如实列出排在最前的几款并说明其属性值'
        '（如名字长度、价格），不要自行换标准或硬凑相关性；若用户要“最长/最多”，'
        '就如实给最长的，不要改成“最推荐的”。\n\n'
        '当前本站共收录 %d 款工具，下面是按相关性检索出的候选清单（JSON）：\n%s'
    ) % (all_count, all_count, payload)


def build_messages(query, history, candidates, all_count):
    system = build_system_prompt(candidates, all_count)
    messages = [{'role': 'system', 'content': system}]
    # 历史对话（最多 6 条，后端已截断）
    for h in history:
        role = h.get('role')
        content = h.get('content')
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': str(content)[:800]})
    messages.append({'role': 'user', 'content': query[:500]})
    return messages


_RETRYABLE_HTTP = frozenset((429, 500, 502, 503, 504))   # 可换模型重试的上游错误


def _llm_request(provider, model, messages):
    """发起单次 LLM 流式请求（OpenAI 兼容协议）；失败抛 HTTPError / URLError"""
    body = {
        'model': model,
        'messages': messages,
        'stream': True,
        'temperature': TEMPERATURE,
        'max_tokens': MAX_TOKENS,
    }
    body.update(provider.get('extra') or {})
    url = provider['base'].rstrip('/') + '/chat/completions'
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + provider['key'],
        },
    )
    return urllib.request.urlopen(req, timeout=120)


def _iter_llm_response(resp):
    """读取流式响应，逐段 yield 文本内容（千问思考流中的 reasoning_content 会被跳过）"""
    try:
        for raw in resp:
            line = raw.decode('utf-8', errors='replace').strip()
            if not line.startswith('data:'):
                continue
            payload = line[5:].strip()
            if payload == '[DONE]':
                break
            try:
                obj = json.loads(payload)
            except ValueError:
                continue
            choices = obj.get('choices') or []
            if not choices:
                continue
            delta = choices[0].get('delta') or {}
            content = delta.get('content')
            if content:
                yield content
    finally:
        resp.close()


def call_llm_stream(messages, on_note=None, stats=None):
    """调用 LLM 流式接口，逐段 yield 文本内容。

    支持多提供商（默认顺序：千问 -> GLM），每个提供商内部按
    「主模型 -> 备用模型」逐级降级；上游 429/5xx 时标记冷却并短退避后
    换下一个（on_note 收到降级提示，stats 记录实际模型）。
    所有模型都失败时，抛最后一次 HTTPError 交给上层兜底。
    """
    if stats is None:
        stats = {}
    last_err = None
    fallback_count = 0
    for provider in _PROVIDERS:
        model_order = [provider['model']] + [
            m for m in provider['fallbacks'] if m != provider['model']]
        while model_order:
            # 跳过冷却中的模型（若全部冷却则只留第一个，保证有尝试机会）
            candidates = [m for m in model_order if time.time() >= _model_cooldown(
                provider['name'] + ':' + m)]
            if not candidates:
                candidates = model_order[:1]
            model = candidates[0]
            model_order = [m for m in model_order if m != model]
            try:
                resp = _llm_request(provider, model, messages)
                stats['provider'] = provider['name']
                stats['model'] = model
                stats['fallbacks'] = fallback_count
                for chunk in _iter_llm_response(resp):
                    yield chunk
                return
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in _RETRYABLE_HTTP:
                    _mark_model_cooldown(provider['name'] + ':' + model)
                    if model_order:
                        fallback_count += 1
                        if on_note:
                            on_note('当前模型繁忙，已自动切换轻量模型继续回答…')
                        time.sleep(RETRY_BACKOFFS[
                            min(fallback_count - 1, len(RETRY_BACKOFFS) - 1)])
                        continue
                if model_order:
                    # 硬错误：换同提供商的下一个备用模型
                    fallback_count += 1
                    if on_note:
                        on_note('当前模型不可用，已自动切换备用模型继续回答…')
                    continue
                # 本提供商全部失败，交给下一个提供商（若有）
                break
    if last_err is not None:
        stats['fallbacks'] = fallback_count
        raise last_err
    raise RuntimeError('no llm provider configured')


def mock_answer(query, candidates):
    """无 API Key 时的本地演示回答（仅测试用）"""
    if not candidates:
        return '当前工具库暂无匹配结果，换个关键词试试？比如“免费的 AI 写作工具”“视频生成”。'
    lines = ['（本地演示模式：未配置 LLM API Key，以下为检索结果预览）', '']
    for t in candidates[:3]:
        free_txt = '免费可用' if t['free'] else '付费'
        lines.append('**[%s](/tools/%s/)**' % (t['name'], t['slug']))
        lines.append('- 分类：%s ｜ 价格：%s' % (t['category'], free_txt))
        lines.append('- %s' % (t['description'] or t['positioning'] or '暂无简介')[:80])
        lines.append('')
    lines.append('配置 DASHSCOPE_API_KEY 或 ZHIPU_API_KEY 后即可获得真正的 AI 推荐。')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# 限流 / 日志
# ---------------------------------------------------------------------------

_RATE = {}
_RATE_LOCK = threading.Lock()
_UPSTREAM_SEM = threading.Semaphore(1)
_MODEL_COOLDOWN_UNTIL = {}
_MODEL_COOLDOWN_LOCK = threading.Lock()


def _model_cooldown(model):
    with _MODEL_COOLDOWN_LOCK:
        return _MODEL_COOLDOWN_UNTIL.get(model, 0.0)


def _mark_model_cooldown(model):
    with _MODEL_COOLDOWN_LOCK:
        _MODEL_COOLDOWN_UNTIL[model] = time.time() + MODEL_COOLDOWN


def rate_allowed(ip):
    now = time.time()
    with _RATE_LOCK:
        q = _RATE.get(ip)
        if q is None:
            q = deque()
            _RATE[ip] = q
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_PER_MIN:
            return False
        q.append(now)
        return True


def log_event(event):
    try:
        with io.open(LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + '\n')
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 用户点赞存储（口碑信号）
# 防刷设计：每工具每 IP 一次 + 每浏览器 token 一次 + 每 IP 每日上限
#            + 爆发告警日志（供人工复核）；数据与部署目录隔离
# ---------------------------------------------------------------------------

_LIKES_LOCK = threading.Lock()
_LIKES = {'counts': {}, 'likers': {}, 'ip_activity': {}, 'mtime': 0}


def _ip_hash(ip):
    return hashlib.sha256((ip + LIKE_SALT).encode('utf-8')).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 常见问题缓存（P0-1）
# 只缓存"首轮提问 + 成功回答"，key 为归一化问题；命中不占上游并发
# ---------------------------------------------------------------------------

_CACHE_LOCK = threading.Lock()
_CACHE = {}                 # key -> {'answer': str, 'ts': float}
_CACHE_STATS = {'hits': 0, 'misses': 0, 'sets': 0}


def cache_get(query):
    key = _norm(query)
    if not key:
        return None
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item and time.time() - item['ts'] < CACHE_TTL:
            _CACHE_STATS['hits'] += 1
            return item['answer']
        if item:
            del _CACHE[key]
        _CACHE_STATS['misses'] += 1
        return None


def cache_set(query, answer):
    if not answer or MOCK:
        return
    key = _norm(query)
    if not key:
        return
    with _CACHE_LOCK:
        _CACHE[key] = {'answer': answer, 'ts': time.time()}
        if len(_CACHE) > CACHE_MAX:
            for k in sorted(_CACHE, key=lambda x: _CACHE[x]['ts'])[:CACHE_MAX // 2]:
                del _CACHE[k]
        _CACHE_STATS['sets'] += 1


# ---------------------------------------------------------------------------
# 回答反馈存储（P1-4）
# 同一 answer_id + 同一浏览器/IP 允许改一次（有用↔没用）；记录问题原文供调优
# ---------------------------------------------------------------------------

_FB_LOCK = threading.Lock()
_FB = {'votes': {}, 'log': [], 'mtime': 0}
_FB_RATE = {}
_ANSWER_META = {}   # answer_id -> query（近期回答，供反馈日志记录问题原文）


def _fb_rate_allowed(ip):
    now = time.time()
    q = _FB_RATE.get(ip)
    if q is None:
        q = deque()
        _FB_RATE[ip] = q
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= FEEDBACK_RATE_PER_MIN:
        return False
    q.append(now)
    return True


def _load_feedback(force=False):
    global _FB
    try:
        mtime = os.path.getmtime(FEEDBACK_JSON)
    except OSError:
        mtime = 0
    if not force and _FB['mtime'] == mtime and _FB['votes']:
        return _FB
    data = {'votes': {}, 'log': []}
    try:
        with io.open(FEEDBACK_JSON, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            data['votes'] = raw.get('votes', {}) or {}
            data['log'] = raw.get('log', []) or []
    except Exception:
        pass
    _FB = {'votes': data['votes'], 'log': data['log'], 'mtime': mtime}
    return _FB


def _save_feedback():
    tmp = FEEDBACK_JSON + '.tmp'
    try:
        os.makedirs(os.path.dirname(FEEDBACK_JSON), exist_ok=True)
        with io.open(tmp, 'w', encoding='utf-8') as fh:
            json.dump({'votes': _FB['votes'], 'log': _FB['log']}, fh, ensure_ascii=False)
        os.replace(tmp, FEEDBACK_JSON)
        os.chmod(FEEDBACK_JSON, 0o600)
    except Exception as e:
        print('save_feedback error:', e)


def add_feedback(answer_id, query, value, ip, token=''):
    """记录一条反馈。返回 (accepted, changed)；同身份重复投视为改票。"""
    iph = _ip_hash(ip)
    with _FB_LOCK:
        d = _load_feedback()
        votes = d['votes']
        entry = votes.setdefault(answer_id, {})
        key = token or iph
        changed = key in entry
        entry[key] = value
        if len(entry) > 500:
            for k in list(entry)[:-500]:
                del entry[k]
        d['log'].append({
            'answer_id': answer_id,
            'query': query[:200],
            'value': value,
            'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
            'ip': iph,
        })
        if len(d['log']) > FEEDBACK_LOG_MAX:
            d['log'] = d['log'][-FEEDBACK_LOG_MAX:]
        d['mtime'] = time.time()
        _save_feedback()
        return True, changed


def _remember_answer(answer_id, query):
    _ANSWER_META[answer_id] = query[:200]
    if len(_ANSWER_META) > 500:
        for k in list(_ANSWER_META)[:-300]:
            del _ANSWER_META[k]


def _valid_slug_set():
    return set(t['slug'] for t in _load_tools())


def sanitize_links(answer):
    """幻觉后校验（P2-7）：把回答里指向"不存在工具"的链接降级为纯文本。
    返回 (修正后文本, 被修正的 slug 列表)。"""
    valid = _valid_slug_set()
    fixes = []

    def _repl(m):
        name, slug = m.group(1), m.group(2)
        if slug in valid:
            return m.group(0)
        fixes.append(slug)
        return name

    new = re.sub(r'\[([^\]]+)\]\(/tools/([A-Za-z0-9._\-]+)/\)', _repl, answer)
    return new, fixes


def _name_aliases(name):
    """由工具名派生「模型可能输出的写法」候选（安全别名，不含泛化词）：
    1. 完整名：'Copilot（微软）'
    2. 基础名：剥离括号注释 → 'Copilot'
    3. 点号变体：'Copy.ai' → 'Copy ai'（模型常把点写成空格/省略）
    2026-08-20 修复「推送工具无链接」：模型按候选 JSON 输出时习惯把
    带括号注释/点号的名字简化，旧版 build_link_map 只做完整名子串匹配，
    简化写法全部漏链（Windsurf/Copilot/Bolt.new 等必现）。
    """
    out = []
    name = (name or '').strip()
    if not name:
        return out
    out.append(name)
    m = re.match(r'^([^（(]+)', name)
    base = m.group(1).strip() if m else ''
    if base and base != name and len(base) >= 3:
        out.append(base)
    if '.' in name:
        for variant in (name.replace('.', ' '), name.replace('.', '')):
            variant = variant.strip()
            if variant and variant != name and len(variant) >= 4:
                out.append(variant)
    return list(dict.fromkeys(out))


def build_link_map(answer):
    """扫描回答中出现过的工具名，返回 {工具名: '/tools/slug/'}。
    模型有时不按提示输出 markdown 链接，前端拿到这份映射后
    会把纯文本工具名自动变成可点击的详情页链接。
    2026-08-20：支持别名匹配（括号注释剥离 + 点号变体），
    修复模型简化工具名导致的无链接问题。"""
    lower_text = (answer or '').lower()
    out = {}

    def _put(key, slug):
        key = (key or '').strip()
        if not key or key in out:
            return
        if key.lower() in lower_text:
            out[key] = '/tools/%s/' % slug

    for t in _load_tools():
        name = (t.get('name') or '').strip()
        slug = (t.get('slug') or '').strip()
        if not name or not slug:
            continue
        for alias in _name_aliases(name):
            _put(alias, slug)
    return out


def _load_likes(force=False):
    """加载点赞数据（mtime 变化自动重载），并顺手清理超过 24h 的 IP 活动记录"""
    global _LIKES
    try:
        mtime = os.path.getmtime(LIKES_JSON)
    except OSError:
        mtime = 0
    if not force and _LIKES['mtime'] == mtime and _LIKES['counts']:
        return _LIKES
    data = {'counts': {}, 'likers': {}, 'ip_activity': {}}
    try:
        with io.open(LIKES_JSON, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            data['counts'] = raw.get('counts', {}) or {}
            data['likers'] = raw.get('likers', {}) or {}
            data['ip_activity'] = raw.get('ip_activity', {}) or {}
    except Exception:
        pass
    now = time.time()
    for k in list(data['ip_activity'].keys()):
        data['ip_activity'][k] = [t for t in data['ip_activity'][k] if now - t < 86400]
        if not data['ip_activity'][k]:
            del data['ip_activity'][k]
    _LIKES = {
        'counts': data['counts'],
        'likers': data['likers'],
        'ip_activity': data['ip_activity'],
        'mtime': mtime,
    }
    return _LIKES


def _save_likes():
    d = _LIKES
    tmp = LIKES_JSON + '.tmp'
    try:
        os.makedirs(os.path.dirname(LIKES_JSON), exist_ok=True)
        with io.open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(
                {'counts': d['counts'], 'likers': d['likers'], 'ip_activity': d['ip_activity']},
                fh, ensure_ascii=False,
            )
        os.replace(tmp, LIKES_JSON)
        os.chmod(LIKES_JSON, 0o600)
    except Exception as e:
        print('save_likes error:', e)


def like_tool(slug, ip, browser_token=''):
    """给工具点赞。返回 (accepted, liked, new_count, msg)
    accepted=False 表示被防刷拦截；liked=False 且 accepted=True 表示重复点赞。"""
    iph = _ip_hash(ip)
    now = time.time()
    with _LIKES_LOCK:
        d = _load_likes()
        counts = d['counts']
        likers = d['likers']
        activity = d['ip_activity']

        acts = [t for t in activity.get(iph, []) if now - t < 86400]
        if len(acts) >= LIKE_DAILY_CAP:
            return False, False, counts.get(slug, 0), '今天点赞有点多啦，明天再来试试'

        tool_likers = likers.setdefault(slug, [])
        if iph in tool_likers:
            return True, False, counts.get(slug, 0), 'already'
        if browser_token and browser_token in tool_likers:
            return True, False, counts.get(slug, 0), 'already'

        tool_likers.append(browser_token) if browser_token else None
        tool_likers.append(iph)
        if len(tool_likers) > 20000:
            tool_likers[:1000] = []
        counts[slug] = counts.get(slug, 0) + 1
        activity[iph] = acts + [now]
        if len(activity[iph]) > 100:
            activity[iph] = activity[iph][-100:]
        d['mtime'] = now
        _save_likes()

        if counts[slug] >= LIKE_BURST_ALERT and counts[slug] % LIKE_BURST_ALERT == 0:
            log_event({
                'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                'event': 'like_burst_alert',
                'slug': slug,
                'count': counts[slug],
            })
        return True, True, counts[slug], ''


# ---------------------------------------------------------------------------
# HTTP 服务
# ---------------------------------------------------------------------------

class ThreadingHTTPServerCompat(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = 'AIToolAssistant/1.0'
    protocol_version = 'HTTP/1.1'

    # ---------------- 工具方法 ----------------
    def _client_ip(self):
        fwd = self.headers.get('X-Forwarded-For', '')
        if fwd:
            return fwd.split(',')[0].strip()
        return self.client_address[0]

    def _send_json(self, code, obj, extra=None):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_body(self, limit=8192):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return b''
        if length > limit:
            return None
        return self.rfile.read(length)

    def _sse(self, event_name, data):
        line = 'data: %s\n\n' % json.dumps(data, ensure_ascii=False)
        try:
            self.wfile.write(line.encode('utf-8'))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return False
        return True

    def _begin_sse(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store')
        self.send_header('Connection', 'close')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.close_connection = True

    # ---------------- 路由 ----------------
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/health':
            tools = _load_tools()
            self._send_json(200, {
                'ok': True,
                'service': 'ai-assistant',
                'tools': len(tools),
                'likes': sum(_load_likes()['counts'].values()),
                'cache': {
                    'size': len(_CACHE),
                    'hits': _CACHE_STATS['hits'],
                    'misses': _CACHE_STATS['misses'],
                    'sets': _CACHE_STATS['sets'],
                },
                'mode': 'mock' if MOCK else 'live',
                'provider': _PROVIDERS[0]['name'] if _PROVIDERS else None,
                'model': MODEL,
                'fallbacks': MODEL_FALLBACKS,
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            return
        if path == '/api/likes':
            d = _load_likes()
            self._send_json(200, {'ok': True, 'likes': d['counts']})
            return
        self._send_json(404, {'error': 'not found'})

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/like':
            return self._handle_like()
        if path == '/api/feedback':
            return self._handle_feedback()
        if path != '/api/chat':
            self._send_json(404, {'error': 'not found'})
            return

        ip = self._client_ip()
        if not rate_allowed(ip):
            self._send_json(429, {'error': '请求太频繁了，请稍等一分钟再试'})
            return

        raw = self._read_body(limit=16384)
        if raw is None:
            self._send_json(413, {'error': '请求体过大'})
            return
        try:
            data = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {'error': '请求格式错误'})
            return

        query = (data.get('message') or '').strip()
        if not query:
            self._send_json(400, {'error': '请输入你的工具需求'})
            return
        if len(query) > 500:
            query = query[:500]

        history = data.get('history') or []
        if not isinstance(history, list):
            history = []
        history = history[-6:]

        # P0-1 常见问题缓存：仅首轮（无历史）+ 非 mock 时生效；命中不占上游并发
        cache_hit = None
        if not history and not MOCK:
            cache_hit = cache_get(query)
        if cache_hit is not None:
            t0 = time.time()
            self._begin_sse()
            answer_id = hashlib.sha256((query + str(time.time()) + ip).encode('utf-8')).hexdigest()[:12]
            _remember_answer(answer_id, query)
            self._sse('meta', {'answer_id': answer_id})
            for chunk in _chunk_text(cache_hit, 80):
                if not self._sse('message', {'content': chunk}):
                    break
            self._sse('links', {'links': {'map': build_link_map(cache_hit)}})
            self._sse('done', {})
            log_event({
                'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                'ip': ip,
                'query': query,
                'cache': 'hit',
                'latency_ms': int((time.time() - t0) * 1000),
                'mode': 'live',
                'error': None,
            })
            return

        # 全局并发 1（免费档上游限制）：排队而不是直接 503
        if not _UPSTREAM_SEM.acquire(timeout=QUEUE_TIMEOUT):
            self._send_json(503, {'error': '当前咨询的人有点多，请稍后再试'})
            return

        t0 = time.time()
        candidates, hit_cats = [], []
        err = None
        matched_slugs = []
        stream_stats = {}
        try:
            candidates, hit_cats = retrieve(query)
            matched_slugs = [t['slug'] for t in candidates]
            all_count = len(_load_tools())
            messages = build_messages(query, history, candidates, all_count)

            self._begin_sse()
            answer_id = hashlib.sha256((query + str(time.time()) + ip).encode('utf-8')).hexdigest()[:12]
            _remember_answer(answer_id, query)
            self._sse('meta', {'answer_id': answer_id})

            if MOCK:
                answer = mock_answer(query, candidates)
                for chunk in _chunk_text(answer, 40):
                    if not self._sse('message', {'content': chunk}):
                        break
                    time.sleep(0.015)
                self._sse('links', {'links': {'map': build_link_map(answer)}})
                self._sse('done', {})
            else:
                answer_parts = []
                notes = []
                try:
                    for chunk in call_llm_stream(messages, on_note=notes.append, stats=stream_stats):
                        answer_parts.append(chunk)
                        if not self._sse('message', {'content': chunk}):
                            break
                except urllib.error.HTTPError as e:
                    body = e.read().decode('utf-8', errors='replace')[:300]
                    if e.code == 429:
                        self._sse('error', {'error': '当前咨询人数较多，已尝试多个免费模型仍未成功，请稍等片刻再试'})
                    else:
                        self._sse('error', {'error': 'AI 服务上游错误：%s %s' % (e.code, body)})
                    err = 'http_%s' % e.code
                except Exception as e:
                    self._sse('error', {'error': 'AI 服务暂时不可用：%s' % str(e)[:120]})
                    err = str(e)[:200]
                else:
                    full_answer = ''.join(answer_parts)
                    clean, fixes = sanitize_links(full_answer)
                    if fixes:
                        notes.append('已自动修正：%s 不在本站收录范围，已移除其链接' % '、'.join(fixes[:3]))
                    for note_text in notes:
                        self._sse('note', {'note': note_text})
                    self._sse('links', {'links': {'map': build_link_map(clean)}})
                    self._sse('done', {})
                    cache_set(query, clean)
                    if fixes:
                        log_event({
                            'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'event': 'link_sanitized',
                            'query': query,
                            'fixes': fixes,
                        })
        except Exception as e:
            err = str(e)[:200]
            try:
                self._sse('error', {'error': '服务内部错误，请稍后再试'})
            except Exception:
                pass
        finally:
            _UPSTREAM_SEM.release()
            latency = int((time.time() - t0) * 1000)
            log_event({
                'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                'ip': ip,
                'query': query,
                'cache': 'hit' if cache_hit is not None else 'miss',
                'matched': matched_slugs,
                'hit_categories': hit_cats,
                'candidate_count': len(candidates),
                'latency_ms': latency,
                'mode': 'mock' if MOCK else 'live',
                'model': stream_stats.get('model') or MODEL,
                'fallbacks': stream_stats.get('fallbacks', 0),
                'error': err,
            })

    def _handle_like(self):
        """POST /api/like {slug, token} —— 用户点赞（带防刷）"""
        ip = self._client_ip()
        raw = self._read_body(limit=4096)
        if raw is None:
            self._send_json(413, {'error': '请求体过大'})
            return
        try:
            data = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {'error': '请求格式错误'})
            return
        slug = (data.get('slug') or '').strip()
        token = (data.get('token') or '').strip()[:64]
        if not slug or not re.fullmatch(r'[A-Za-z0-9._\-]+', slug):
            self._send_json(400, {'error': 'slug 不合法'})
            return
        valid_slugs = {t['slug'] for t in _load_tools()}
        if slug not in valid_slugs:
            self._send_json(404, {'error': '工具不存在'})
            return

        accepted, liked, count, msg = like_tool(slug, ip, token)
        if not accepted:
            self._send_json(429, {'error': msg})
            return
        log_event({
            'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
            'event': 'like',
            'ip': ip,
            'slug': slug,
            'liked': liked,
            'count': count,
        })
        self._send_json(200, {
            'ok': True,
            'slug': slug,
            'liked': liked,
            'already': not liked,
            'likes': count,
        })

    def _handle_feedback(self):
        """POST /api/feedback {answer_id, value, token} —— AI 回答反馈（有用/没用）"""
        ip = self._client_ip()
        if not _fb_rate_allowed(ip):
            self._send_json(429, {'error': '操作太频繁了，请稍后再试'})
            return
        raw = self._read_body(limit=4096)
        if raw is None:
            self._send_json(413, {'error': '请求体过大'})
            return
        try:
            data = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {'error': '请求格式错误'})
            return
        answer_id = (data.get('answer_id') or '').strip()
        value = data.get('value')
        token = (data.get('token') or '').strip()[:64]
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,64}', answer_id):
            self._send_json(400, {'error': 'answer_id 不合法'})
            return
        try:
            value = int(value)
        except (TypeError, ValueError):
            self._send_json(400, {'error': 'value 不合法'})
            return
        if value not in (1, -1):
            self._send_json(400, {'error': 'value 只能为 1 或 -1'})
            return

        query = _ANSWER_META.get(answer_id, '')
        accepted, changed = add_feedback(answer_id, query, value, ip, token)
        if not accepted:
            self._send_json(429, {'error': '稍后再试'})
            return
        self._send_json(200, {'ok': True, 'answer_id': answer_id, 'value': value, 'changed': changed})


def _chunk_text(text, size):
    for i in range(0, len(text), size):
        yield text[i:i + size]


def main():
    _load_tools(force=True)
    server = ThreadingHTTPServerCompat((HOST, PORT), Handler)
    print('AI 工具助手已启动: http://%s:%d' % (HOST, PORT))
    print('  工具库: %s (%d 款已发布)' % (TOOLS_JSON, len(_INDEX['tools'])))
    print('  模式: %s | 模型: %s' % ('MOCK（未配置 Key）' if MOCK else 'LIVE', MODEL))
    if API_KEY:
        print('  提示：请勿将 Key 暴露给前端，本服务仅监听 127.0.0.1')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
        server.server_close()


if __name__ == '__main__':
    main()

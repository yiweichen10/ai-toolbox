#!/usr/bin/env python3
"""SSG构建脚本：将JSON数据生成为静态HTML文件，SEO友好"""
import json
import os
import re
import sys
import time
import subprocess
import argparse
import hashlib
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 站点配置（统一管理域名）
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'https://www.aitoollab.cn')
BAIDU_PUSH_TOKEN = os.getenv('BAIDU_PUSH_TOKEN', '')  # 百度推送token，留空则跳过百度推送

# 已知失效的URL（404/403/部署删除等），这些工具的"立即使用"按钮无href，保留文字但不跳转
BROKEN_URLS = [
    'https://tome.app',
]

# ── 推广链接系统 ──
# 加载 affiliate_links.json，构建时自动将官网链接替换为推广链接
_AFFILIATE_LINKS = {}
_aff_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'affiliate_links.json')
if os.path.exists(_aff_path):
    try:
        with open(_aff_path, 'r', encoding='utf-8') as _f:
            _raw = json.load(_f)
            for _k, _v in _raw.items():
                if isinstance(_v, dict) and _v.get('url'):
                    _AFFILIATE_LINKS[_k] = _v['url']
                elif isinstance(_v, str) and _v:
                    _AFFILIATE_LINKS[_k] = _v
    except Exception:
        pass

def get_affiliate_url(slug, site='zh'):
    """获取工具的推广链接，无则返回 None"""
    key = f"{site}:{slug}"
    return _AFFILIATE_LINKS.get(key)

def get_tool_link(tool, slug, site='zh'):
    """获取工具的最终链接（优先推广链接），返回 (url, is_affiliate)"""
    aff = get_affiliate_url(slug, site)
    if aff:
        return aff, True
    return tool.get('url', ''), False

# 返回顶部按钮 HTML + 内联脚本（避免在 f-string 中转义花括号）
BACK_TO_TOP_BLOCK = '''<button id="backToTop" aria-label="返回顶部">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"></polyline>
    </svg>
</button>
<script>
document.addEventListener("DOMContentLoaded",function(){var b=document.getElementById("backToTop");if(!b)return;var s=function(){if(window.scrollY>150){b.classList.add("visible")}else{b.classList.remove("visible")}};window.addEventListener("scroll",s,{passive:true});s();b.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"})});});
</script>
<script src="/js/tts-reader.js?v={TTS_JS_VERSION}" defer></script>
<script src="/js/favorites.js" defer></script>'''

# 工具点赞按钮样式（/tools/ 列表页与工具详情页共用）
TOOL_LIKE_CSS = """
.tool-like{display:inline-flex;align-items:center;gap:3px;flex:none;font-size:12px;font-weight:600;color:var(--text-muted);background:rgba(127,127,127,.08);border:1px solid var(--border-light);border-radius:999px;padding:3px 8px;cursor:pointer;transition:var(--transition);user-select:none;}
.tool-like:hover{border-color:var(--primary);color:var(--primary);}
.tool-like.liked{color:var(--primary);border-color:var(--primary);background:rgba(0,166,79,.10);}
.tool-like b{font-weight:700;font-variant-numeric:tabular-nums;}
@media (max-width:640px){.tool-like{font-size:11px;padding:2px 7px;}}
"""

# 工具详情页操作区按钮 v2（2026-08-08）：统一高度/圆角/字号，消除主按钮与次级按钮的违和感
# 只作用于详情页 .tool-header 内，不影响列表页的小型点赞胶囊
TOOL_ACTION_CSS = """
.tool-header .action-bar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-top:14px;}
.tool-header .action-bar .action-btn,
.tool-header .action-bar .tool-like{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:44px;padding:0 22px;border-radius:12px;font-size:14px;font-weight:700;line-height:1;text-decoration:none;transition:var(--transition);cursor:pointer;user-select:none;}
.tool-header .action-bar .action-btn-primary{flex:none;padding:0 30px;background:var(--bg-gradient);color:#fff;box-shadow:var(--shadow-md);border:none;}
.tool-header .action-bar .action-btn-primary:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg);color:#fff;}
.tool-header .action-bar .action-btn-ghost{flex:none;background:var(--surface);border:1.5px solid var(--primary);color:var(--primary);}
.tool-header .action-bar .action-btn-ghost:hover{background:var(--primary);color:#fff;}
.tool-header .action-bar .tool-like{flex:none;background:var(--surface);border:1.5px solid var(--primary);color:var(--primary);}
.tool-header .action-bar .tool-like:hover{background:rgba(0,166,79,.08);color:var(--primary);}
.tool-header .action-bar .tool-like.liked{background:var(--primary);border-color:var(--primary);color:#fff;}
.tool-header .action-bar .tool-like b{font-weight:700;font-variant-numeric:tabular-nums;}
@media (max-width:640px){
  .tool-header .action-bar{gap:8px;}
  .tool-header .action-bar .action-btn,
  .tool-header .action-bar .tool-like{height:42px;padding:0 10px;font-size:13px;flex:1 1 calc(33.333% - 6px);}
}
"""

# ICP 备案标识（统一管理，全站 footer 共用）
ICP_BEIAN = '<a href="https://beian.miit.gov.cn/" target="_blank" rel="nofollow noopener">蜀ICP备2025172163号-2</a>'

# 文章页目录 + 上一篇/下一篇样式（P0-4，2026-08-09）。
# 内联注入文章页 head，避免依赖 optimize_css 全量重跑。
ARTICLE_EXTRA_CSS = '''<style>
.article-toc{background:var(--surface-2,#f8fafc);border:1px solid var(--border-light,#eef2f6);border-left:4px solid #10a37f;border-radius:8px;padding:16px 20px;margin:0 0 24px;font-size:14px;}
.article-toc-title{font-weight:700;margin-bottom:10px;color:var(--text-main,#1e293b);}
.article-toc ol{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px;}
.article-toc a{color:var(--text-muted,#64748b);text-decoration:none;}
.article-toc a:hover{color:#10a37f;}
.article-body h2[id],.article-body h3[id],.article-body h4[id]{scroll-margin-top:200px;}
.article-prev-next{display:flex;justify-content:space-between;gap:16px;margin:28px 0 8px;flex-wrap:wrap;}
.article-prev-next a{display:block;flex:1 1 240px;padding:14px 18px;background:var(--surface,#fff);border:1px solid var(--border-light,#eef2f6);border-radius:10px;font-size:13.5px;color:var(--text-main,#1e293b);text-decoration:none;transition:all .15s ease;}
.article-prev-next a:hover{border-color:#10a37f;box-shadow:var(--shadow-sm);}
.article-prev-next .apn-prev{text-align:left;}
.article-prev-next .apn-next{text-align:right;}
@media (max-width:640px){.article-prev-next a{flex:1 1 100%;}}
@media (max-width:768px){.article-body h2[id],.article-body h3[id],.article-body h4[id]{scroll-margin-top:190px;}}
</style>'''

# 全站 footer 站内链接（P0-5，2026-08-09）：与首页 footer-links 一致，
# 给只有版权+备案的内页补上"关于/联系/收藏/隐私/投稿"出口。
FOOTER_LINKS_HTML = '''    <div class="footer-links">
            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/favorites.html">我的收藏</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
            <a href="mailto:AIToolLabTeam@gmail.com">投稿合作</a>
        </div>'''

from pypinyin import pinyin, Style
from datetime import datetime as _dt_build

# ── 全站动态常量（P0：消除硬编码 2026/100+/12大分类 等陈旧数字）──
BUILD_YEAR = _dt_build.now().year
REVIEW_CATS = {'AI评测', 'AI工具评测', 'AI模型评测', 'tool-review', 'tools-comparison', '对比评测', '观点对比'}  # 评测/对比类文章分类集合
TOOL_COUNT = CAT_COUNT = ART_COUNT = 0  # 在 build_target() 入口计算

# ── 文章内容类型（2026-08-08：22+ 分类归并为 4 类，见 ROADMAP-TODO 第一阶段）
# AI资讯 = 长文资讯（区别于 /news/ 短快讯，2026-08-08 更名）──
ARTICLE_CONTENT_TYPES = ('AI评测', 'AI教程', 'AI资讯', '行业分析')
ARTICLE_CATEGORY_PAGES = [
    {
        'slug': 'reviews',
        'ctype': 'AI评测',
        'h1': 'AI工具评测',
        'page_title': 'AI工具评测 - 深度实测与对比横评 | AI工具宝箱',
        'description': 'AI工具宝箱AI工具评测合集：ChatGPT、Claude、DeepSeek、Midjourney、Kimi等主流AI工具的真实实测、横评对比与选型建议，覆盖价格、免费额度与上手难度，全部基于编辑组实际付费测试数据，帮你决策不踩坑。',
        'keywords': 'AI工具评测,AI工具测评,AI评测,AI工具实测,AI工具对比,AI工具横评',
        'intro': '编辑组亲自实测的AI工具评测与对比：真实数据、真实花费、适用场景，选工具前先看这里。',
        'breadcrumb': 'AI工具评测',
    },
    {
        'slug': 'tutorials',
        'ctype': 'AI教程',
        'h1': 'AI实战教程',
        'page_title': 'AI实战教程 - 从入门到上手 | AI工具宝箱',
'description': 'AI工具宝箱AI实战教程合集：ChatGPT、Claude、DeepSeek、Cursor、Midjourney等热门AI工具的使用教程、入门指南与上手实操，附价格与免费额度说明，从注册配置到实战场景一步步演示，零基础也能跟着学会。',
        'keywords': 'AI教程,AI工具教程,AI实战教程,AI工具怎么用,AI工具入门,AI工具指南',
        'intro': '一步步教你用好AI工具：注册、配置、实战场景全覆盖，从零基础到熟练上手。',
        'breadcrumb': 'AI实战教程',
    },
    {
        'slug': 'analysis',
        'ctype': '行业分析',
        'h1': 'AI行业分析',
        'page_title': 'AI行业分析 - 趋势与深度解读 | AI工具宝箱',
'description': 'AI工具宝箱AI行业分析合集：大模型发布、AI产业格局、市场数据、政策监管等深度分析与趋势解读，覆盖国内外AI厂商动态与前沿技术，附数据来源可溯源，并给出编辑部独立观点与趋势预判，帮你看清AI行业正在发生什么、下一步走向哪里。',
        'keywords': 'AI行业分析,AI趋势,AI行业动态,AI行业趋势,大模型分析,AI产业分析',
        'intro': '跳出单个工具看行业：大模型格局、市场数据与趋势研判的深度解读。',
        'breadcrumb': 'AI行业分析',
    },
    {
        'slug': 'news',
        'ctype': 'AI资讯',
        'h1': 'AI资讯',
        'page_title': 'AI资讯 - 深度长文与行业动态 | AI工具宝箱',
 'description': 'AI工具宝箱AI资讯长文合集：宇树牵手DeepSeek、大模型发布、AI公司融资与行业动态等深度资讯文章，每条都经过编辑整理并附官方来源，数据每日更新，从事件背景到行业影响逐层拆解，并附数据来源与原文链接，帮你快速掌握AI行业正在发生的大事。',
        'keywords': 'AI资讯,AI行业动态,AI新闻,AI资讯长文,AI行业资讯,大模型动态,AI快讯',
        'intro': 'AI 行业深度资讯长文：不只给标题，把来龙去脉和影响讲清楚。',
        'breadcrumb': 'AI资讯',
    },
]

def article_content_type(a):
    """文章内容类型：优先取数据字段，缺失时按分类+标题规则兜底（2026-08-08）。"""
    ct = a.get('content_type') or ''
    if ct in ARTICLE_CONTENT_TYPES:
        return ct
    cat = a.get('category', '')
    title = a.get('title', '')
    _rev = {'AI评测', 'AI工具评测', 'AI模型评测', 'tool-review', 'tools-comparison',
            '对比评测', '观点对比'}
    _tut = {'AI工具教程', '教程指南', 'AI教程'}
    _news = {'AI资讯', 'AI行业动态', '行业动态', 'ai-news', 'industry-news'}
    _ana = {'industry-analysis', '行业趋势', '行业分析', '数据洞察', 'AI趋势', 'AI行业分析'}
    _tut_kw = ('教程', '指南', '入门', '怎么用', '如何使用', '上手', '保姆级',
               '工作流', '实战', '玩法', '使用教程', '完全使用', '流程')
    _rev_kw = ('评测', '实测', '横评', '测评', '对决', '测试', '对比', '推荐',
               '选型', '哪个好', '怎么选', '体验', '低估', '测了', '画了', '真实项目')
    _news_kw = ('快讯', '本周', '上周', '发生了什么', 'AI圈', '新闻', '速览', '日报')
    _ana_kw = ('分析', '趋势', '盘点', '报告', '全景', '格局', '复盘', '深度',
               '行业', '解析', '观察', '解读', '白皮书')
    if cat in _rev:
        return 'AI评测'
    if cat in _tut:
        return 'AI教程'
    if cat in _news:
        return 'AI资讯'
    if any(k in title for k in _news_kw):
        return 'AI资讯'
    if cat in _ana:
        if any(k in title[:28] for k in ('评测', '实测', '横评', '测评')):
            return 'AI评测'
        return '行业分析'
    if any(k in title for k in _tut_kw):
        return 'AI教程'
    if any(k in title[:28] for k in ('评测', '实测', '横评', '测评')):
        return 'AI评测'
    if re.search(r'\b[vV][sS]\b', title):
        return 'AI评测'
    if any(k in title for k in _rev_kw):
        return 'AI评测'
    if any(k in title for k in _ana_kw):
        return '行业分析'
    return '行业分析'

def ensure_article_content_types(articles):
    """新文章自动归类（2026-08-08）：content_type 缺失时按规则内存补齐，返回补写篇数。
    幂等：已归类的不动；配合 article_content_type() 兜底，保证新增文章无需手工维护类型。
    注意：只做内存赋值，不写回 articles.json（构建对数据只读，写回职责归发布管线/分类脚本）。"""
    changed = 0
    for a in articles:
        if a.get('content_type') not in ARTICLE_CONTENT_TYPES:
            a['content_type'] = article_content_type(a)
            changed += 1
    return changed

# 意图驱动标题引擎（2026-07-25）：long_tail / Title / Meta 生成，消除全站统一模板
try:
    from seo_title_helper import gen_long_tail, build_title, build_meta, gen_positioning
except ImportError:
    def gen_long_tail(tool, slug_map=None):
        return "评测：优缺点与真实体验"
    def gen_positioning(tool):
        return f"{(tool.get('category') or 'AI')}工具"
    def build_title(name, lt, year=None):
        return f"{name} - {lt} | AI工具宝箱"
    def build_meta(name, lt, desc, year=None, tool=None):
        return f"{name} - {lt}：{(desc or '')[:150]}"
# slug->name 映射，加载工具后填充，供对比意图取竞品名
_SLUG_MAP = {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 缓存版本号：按文件内容哈希自动生成（内容不变版本不变，内容一变版本必变，无需手动递增）
def _file_cache_version(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:10]
    except Exception:
        return '0'

# ── CSS 安全门禁(2026-08-22 事故后新增, 双保险) ──
# 即使有人跳过 optimize_css 直接 build, 也拦截括号不平衡, 杜绝 media 块吞规则回档。
def _css_safety_check():
    _src_path = os.path.join(BASE_DIR, 'css', 'style.css')
    try:
        _src = open(_src_path, 'r', encoding='utf-8').read()
    except Exception:
        return  # 源文件缺失不阻断(极少情况)
    _opens, _closes = _src.count('{'), _src.count('}')
    if _opens != _closes:
        print(f"❌ CSS 安全校验未通过: style.css 括号不平衡 {{ = {_opens}, }} = {_closes}")
        print("   请先修复漏写的 }, 常见位置是 @media 块结尾, 再重新构建。")
        sys.exit(1)
    # 媒体查询块栈追踪, 定位未闭合块行号
    _stack = []
    for _i, _line in enumerate(_src.split('\n'), 1):
        for _ch in _line:
            if _ch == '{':
                _stack.append((_line.strip()[:40], _i))
            elif _ch == '}':
                if _stack:
                    _stack.pop()
    if _stack:
        _detail = "; ".join(f"「{t}…」第 {ln} 行" for t, ln in _stack[:5])
        _more = f" 等共 {len(_stack)} 个" if len(_stack) > 5 else ""
        print(f"❌ CSS 安全校验未通过: 存在未闭合块(漏写 }}): {_detail}{_more}")
        print("   请先修复 style.css, 再重新构建。")
        sys.exit(1)

_css_safety_check()

CSS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'css', 'style.min.css'))
JS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'js', 'main.js'))
WIDGET_CSS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'css', 'ai-widget.css'))
WIDGET_JS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'js', 'ai-assistant.js'))
LIKES_JS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'js', 'ai-likes.js'))
TTS_JS_VERSION = _file_cache_version(os.path.join(BASE_DIR, 'js', 'tts-reader.js'))
# BACK_TO_TOP_BLOCK 在上方已定义，此处把占位符替换成真实 hash（内容变→hash变→浏览器必拉新）
BACK_TO_TOP_BLOCK = BACK_TO_TOP_BLOCK.replace('{TTS_JS_VERSION}', TTS_JS_VERSION)

# 首屏关键CSS(内联<head>, 消除渲染阻塞) + 全量CSS异步预加载
# style.critical.css 由 scripts/optimize_css.py 生成(改完 style.css 后必须重跑)
CRITICAL_CSS = ""
_CRIT_PATH = os.path.join(BASE_DIR, 'css', 'style.critical.css')
if os.path.exists(_CRIT_PATH):
    with open(_CRIT_PATH, 'r', encoding='utf-8') as _cf:
        CRITICAL_CSS = _cf.read().strip()

# ── HTML 写盘出口：统一折叠多余空行(根因修复, 不在事后另写脚本) ──
# 2026-08-24: 抽到 build_lib/html_utils.py（模块1拆分），此处仅重导出以保持兼容
from build_lib.html_utils import (
    _PRE_BLOCK_RE, _collapse_blank_lines, _emit, _record_build_error,
    extract_faq_section, markdown_to_html, shift_headings, escape_html, set_data_dir,
)
set_data_dir(DATA_DIR)

# ── 工具图标：唯一解析入口，SVG优先，PNG其次 ──
def resolve_icon(slug):
    """统一图标解析：返回 (ext, web_path) 或 (None, '')。
    所有页面（详情/首页/JS）共用此函数，保证图标路径一致。
    ext: '.svg' | '.png' | None
    """
    if not slug:
        return None, ''
    for ext in ('.svg', '.png'):
        local_path = os.path.join(BASE_DIR, 'assets', 'icons', slug + ext)
        if os.path.exists(local_path):
            return ext, f'/assets/icons/{slug}{ext}'
    # 回退：同品牌图标（解决版本升级后旧图标丢失问题）
    # 匹配规则：① 精确品牌基础图标（如 seedance.png / minimax.png）；
    #          ② 同品牌带版本号图标（如 glm-5-1.png / kling-ai.svg）。
    # 例：glm-5-2 无 glm-5-2.svg，自动复用 glm-5-1.png；seedance-2-0 复用 seedance.png。
    if '-' in slug:
        brand = slug.split('-')[0]
        if brand and brand != slug:
            icons_dir = os.path.join(BASE_DIR, 'assets', 'icons')
            try:
                cands = []
                for fn in os.listdir(icons_dir):
                    stem, ext = os.path.splitext(fn)
                    if ext.lstrip('.') in ('svg', 'png') and (stem == brand or stem.startswith(brand + '-')):
                        cands.append(fn)
                if cands:
                    # 优先精确品牌基础图标，其次同品牌其它版本/系列图标
                    cands.sort(key=lambda f: (0 if os.path.splitext(f)[0] == brand else 1, f))
                    fn = cands[0]
                    return os.path.splitext(fn)[1], f'/assets/icons/{fn}'
            except FileNotFoundError:
                pass
    return None, ''

def tool_icon_html(tool, large=False, size=None):
    """生成工具图标HTML。依赖 resolve_icon() 统一解析，本地无图标则回退 emoji+色块。
    size: 'sm'(30px 侧边栏/推荐) | 'md'(48px 卡片) | 'lg'(76px 详情)。large=True 等价于 'lg'。"""
    slug = tool.get('slug', '')
    if not slug:
        return ''
    if size is None:
        size = 'lg' if large else 'md'
    cls = {'sm': 'tool-icon-real-sm', 'md': 'tool-icon-real', 'lg': 'tool-icon-real-lg'}.get(size, 'tool-icon-real')
    ext, web_path = resolve_icon(slug)
    if ext:
        return f'<img src="{web_path}" class="{cls}" alt="{escape_html(tool.get("name",""))}" loading="lazy" width="48" height="48">'
    # 回退: emoji + 色块
    if size == 'lg':
        return f'<div class="tool-icon-lg" style="background:{tool.get("color","#4f46e5")};">{tool.get("emoji","")}</div>'
    return f'<div class="tool-icon" style="background:{tool.get("color","#4f46e5")};">{tool.get("emoji","")}</div>'

# 类目名 → CSS 变量名 / HEX颜色（Logo光晕版卡片用）
CATEGORY_COLOR_MAP = {
    'AI对话': ('chat', '#10b981'),
    'AI写作': ('write', '#6366f1'),
    'AI绘画': ('image', '#f59e0b'),
    'AI编程': ('code', '#3b82f6'),
    'AI视频': ('video', '#ef4444'),
    'AI音频': ('audio', '#8b5cf6'),
    'AI办公': ('office', '#0ea5e9'),
    'AI设计': ('design', '#ec4899'),
    'AI搜索': ('search', '#14b8a6'),
    'AI翻译': ('trans', '#22c55e'),
    'AI自动化': ('auto', '#f97316'),
    'AI效率': ('eff', '#a855f7'),
    'AI智能体': ('agent', '#a855f7'),
    'AI开发': ('dev', '#3b82f6'),
    'AI行业应用': ('industry', '#0ea5e9'),
    '去中心化AI': ('decentralized', '#FF6B35'),
}
def get_category_color_var(category_name):
    """返回类目对应的CSS变量引用，如 var(--cat-chat)"""
    entry = CATEGORY_COLOR_MAP.get(category_name)
    if entry:
        return f'var(--cat-{entry[0]})'
    return 'var(--primary)'

def get_category_glow_styles(category_name):
    """返回内联 style 中的 glow 三件套: --glow / --glow-hover / --glow-border"""
    entry = CATEGORY_COLOR_MAP.get(category_name)
    if entry:
        hexc = entry[1]
        return f'--glow:rgba({_hex_to_rgb(hexc)},0.08);--glow-hover:rgba({_hex_to_rgb(hexc)},0.16);--glow-border:rgba({_hex_to_rgb(hexc)},0.25)'
    return '--glow:rgba(99,102,241,0.08);--glow-hover:rgba(99,102,241,0.16);--glow-border:rgba(99,102,241,0.25)'

def _hex_to_rgb(hexc):
    """将 #10b981 转为 '16,185,129'"""
    h = hexc.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return f'{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}'

def get_price_info(tool):
    """从 tool 数据提取价格信息，返回 (css_class, text)
    兼容两种 tags 格式：字符串列表 ['免费可用'] 或 字典列表 [{'type':'free','text':'免费可用'}]"""
    tags = tool.get('tags', [])
    price = tool.get('price', '')
    # 找免费标签（兼容 str / dict 两种格式）
    for tag in tags:
        if isinstance(tag, dict):
            if tag.get('type') == 'free':
                txt = tag.get('text', '')
                if '免费' in txt or 'Free' in txt.lower() or '开源' in txt:
                    return ('free', txt)
                return ('free', '免费可用')
        elif isinstance(tag, str):
            if '免费' in tag or 'Free' in tag.lower() or '开源' in tag:
                return ('free', tag)
    # 从 price 字段判断
    if price:
        if '免费' in price or 'Free' in price.lower():
            return ('free', '免费可用')
        if '开源' in price:
            return ('free', '开源免费')
    return ('paid', '付费')

def extract_rating_num(rating_str):
    """从 '⭐ 4.9' 提取 '4.9'"""
    if not rating_str:
        return ''
    import re as _re
    m = _re.search(r'[\d.]+', str(rating_str))
    return m.group(0) if m else ''

def make_tool_card_html(tool, i):
    """生成 Logo 光晕版工具卡片 HTML（DESIGN.md v2）"""
    slug = tool.get('slug', '')
    name = escape_html(tool.get('name', ''))
    category = escape_html(tool.get('category', ''))
    desc = escape_html(tool.get('description', ''))
    rating_num = extract_rating_num(tool.get('rating', ''))
    glow_styles = get_category_glow_styles(tool.get('category', ''))
    price_cls, price_text = get_price_info(tool)
    visits = tool.get('visits', '')

    icon_html = tool_icon_html(tool)

    # Badge（防御：badge 可能是字符串而非 dict，归一化避免 AttributeError 崩溃）
    badge_data = tool.get('badge') or {}
    if isinstance(badge_data, str):
        badge_data = {'type': 'pick', 'text': badge_data}
    if badge_data and badge_data.get('text') and badge_data.get('type'):
        badge_html = f'<span class="badge badge-{badge_data["type"]}">{badge_data["text"]}</span>'
    else:
        badge_html = ''

    rating_disp = f'<span class="rating-inline">★ {rating_num}</span>' if rating_num else ''

    return f'''                        <a href="/tools/{slug}/" class="tool-card-link" style="text-decoration:none;color:inherit;">
                        <article class="tool-card fade-in" style="animation-delay: {round(i * 0.05, 2)}s;{glow_styles}">
                            <div class="logo-home">
                                {icon_html}
                            </div>
                            <div class="name-row">
                                <span class="name">{name}</span> {badge_html}
                                {rating_disp}
                            </div>
                            <div class="category">{category}</div>
                            <p class="desc">{desc}</p>
                            <div class="footer-row">
                                <span class="price-pill {price_cls}">{price_text}</span>
                                <span class="visits">{visits}</span>
                            </div>
                        </article>
                        </a>\n'''

# OG图片自动生成：缺失时自动调用gen_seo_images生成
def ensure_og_image(slug, data_obj=None, is_article=False, is_dict=False):
    """检查OG图片是否存在，不存在则自动生成。返回og_image URL或空字符串。"""
    og_image_local = os.path.join(BASE_DIR, 'images', 'og', f'{slug}-og.png')
    og_image_url = f'https://www.aitoollab.cn/images/og/{slug}-og.png'
    if os.path.exists(og_image_local):
        return og_image_url
    # 自动生成（Pillow 中文版，移植英文站专业设计）
    try:
        from gen_og_images_cn import make_article_og, make_tool_og, make_dict_og
        if is_dict and data_obj:
            make_dict_og(data_obj, og_image_local)
        elif is_article and data_obj:
            make_article_og(data_obj, og_image_local)
        elif data_obj and not is_article:
            make_tool_og(data_obj, og_image_local)
        else:
            return ''
        if os.path.exists(og_image_local):
            print(f'  [OG] 自动生成: {slug}-og.png')
            return og_image_url
        else:
            print(f'  [OG] 生成失败: {slug}-og.png')
            return ''
    except Exception as e:
        print(f'  [OG] 生成异常: {slug} - {e}')
        return ''

GLOBAL_NAV = '''    <nav class="global-nav" aria-label="全局导航">
        <div class="global-nav-inner">
            <a href="/" class="gn-item">首页</a>
            <a href="/tools/" class="gn-item">全部AI工具</a>
            <a href="/category/" class="gn-item">工具分类</a>
            <a href="/ranking/" class="gn-item">工具排行</a>
            <a href="/news/" class="gn-item">快讯</a>
            <a href="/dict/" class="gn-item">AI词典</a>
            <a href="/quiz/" class="gn-item">AI工具选择器</a>
            <a href="/live/" class="gn-item">实时面板</a>
            <a href="/compare/" class="gn-item">对比评测</a>
            <a href="/alternatives/" class="gn-item">替代方案</a>
            <a href="/favorites.html" class="gn-item">我的收藏</a>
        </div>
    </nav>'''

# 全局搜索条（P0-1，2026-08-09）：注入到首页之外的所有页面 </header> 之后。
# 提交走 GET /?q=，与 404 页、SearchAction 结构化数据共用同一条搜索链路；
# 首页 main.js 读取 q 参数自动执行搜索。
GLOBAL_SEARCH_HTML = '''    <div class="global-search-bar" id="globalSearchBar">
        <form class="search-box" action="/" method="get" role="search" aria-label="站内搜索">
            <input type="search" name="q" id="globalSearchInput" placeholder="搜索AI工具或文章..." autocomplete="off">
            <button type="submit" aria-label="搜索">🔍</button>
        </form>
    </div>'''

# 全局搜索条样式（内联注入，避免依赖 optimize_css 全量重跑）
GLOBAL_SEARCH_CSS = '''<style id="global-search-style">
.global-search-bar{background:var(--surface);border-bottom:1px solid var(--border-light);padding:10px 16px;position:sticky;top:108px;z-index:150}
.global-search-bar .search-box{max-width:640px;margin:0 auto}
@media (min-width:769px){.global-search-bar{padding:12px 32px}}
@media (max-width:768px){.global-search-bar{top:98px}}
</style>'''

# 站点标识（2026-08-10 品牌更新，08-11 改版）：居中对称的「方框 + 内嵌四角星光」。
# 方框象征宝箱/收纳，星光代表 AI；星光嵌在方框正中，避免旧版「烛台+火苗」错觉。
# 与 assets/logo/logo-mark.svg 保持一致；全站头部旧 emoji/实体/旧扳手 SVG 由
# inject_site_logo() 幂等替换为它。改图形时同步 scripts/generate_site_logo.py。
SITE_LOGO_MARK = (
    '<svg class="site-logo-mark" viewBox="0 0 24 24" width="22" height="22" '
    'fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<rect x="3.4" y="4.2" width="17.2" height="16.4" rx="3.4"/>'
    '<path d="M12 7.5 Q14.19 10.21 16.9 12.4 Q14.19 14.59 12 17.3 '
    'Q9.81 14.59 7.1 12.4 Q9.81 10.21 12 7.5 Z" '
    'fill="currentColor" stroke="none"/></svg>'
)

DARK_MODE_HTML = '''    <button id="darkModeToggle" class="dark-toggle-fab" aria-label="切换暗色模式" title="暗色模式">🌙</button>
    <script>
(function(){
  var root=document.documentElement, btn=document.getElementById('darkModeToggle');
  try{if(localStorage.getItem('theme')==='dark')root.setAttribute('data-theme','dark');}catch(e){}
  function updateLabel(){
    if(btn)btn.textContent=root.getAttribute('data-theme')==='dark'?'☀️':'🌙';
  }
  updateLabel();
  if(btn)btn.addEventListener('click',function(){
    var isDark=root.getAttribute('data-theme')==='dark';
    root.setAttribute('data-theme',isDark?'light':'dark');
    try{localStorage.setItem('theme',isDark?'light':'dark');}catch(e){}
    updateLabel();
  });
})();
    </script>'''

BAIDU_TONGJI = '''<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?7cf34c7c8b66be4564949354dbc51337";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();
</script>'''

# 为常用分类提供固定且语义化的英文slug，优先使用这些
CATEGORY_SLUG_MAP = {
    "AI对话": "ai-chat",
    "AI写作": "ai-writing",
    "AI绘画": "ai-painting",
    "AI编程": "ai-coding",
    "AI视频": "ai-video",
    "AI音频": "ai-audio",
    "AI办公": "ai-office",
    "AI设计": "ai-design",
    "AI搜索": "ai-search",
    "AI翻译": "ai-translation",
    "AI自动化": "ai-automation",
    "AI效率": "ai-efficiency",
    "AI智能体": "ai-agent",
    "AI开发": "ai-development",
    "AI行业应用": "ai-verticals",
    "AI学习": "ai-learning",
    "AI检测": "ai-detection",
    "AI提示词": "ai-prompt",
    "去中心化AI": "decentralized-ai",
}

def get_category_slug(category_name):
    """
    根据中文分类名生成SEO友好的英文slug。
    优先使用预设映射，否则使用拼音。
    """
    if category_name in CATEGORY_SLUG_MAP:
        return CATEGORY_SLUG_MAP[category_name]
    
    # 使用pypinyin生成拼音，并转换为连字符连接的小写形式
    pinyin_list = pinyin(category_name, style=Style.NORMAL)
    slug = '-'.join([item[0] for item in pinyin_list if item and item[0].strip()]).lower()
    return slug

def _parse_rating(val, default=4.0):
    """将写脏的 rating 字段解析为 float。

    兼容多种脏格式：'⭐4.8' / '⭐ 4.8' / '4.8（Apple App Store，约8.5万评分）' /
    '4.8分' / '暂无' / 空值。仅提取首个数字片段，提取失败回退 default。
    """
    s = str(val or '').strip()
    if not s:
        return default
    m = re.search(r'\d+(?:\.\d+)?', s)
    if not m:
        return default
    try:
        return float(m.group())
    except (ValueError, TypeError):
        return default

_TOOL_LINK_MAP = None
_LINK_STOPWORDS = {'AI', 'API', 'GPT', 'Chat', 'ChatGPT', '工具', '助手',
                   '人工智能', '大模型', '机器人', 'AI工具', 'APP', 'App', '软件'}

def load_tools():
    """目录优先加载工具数据。有 data/tools/*.json 则聚合，否则回退单体 tools.json。"""
    import glob as _glob
    d = os.path.join(DATA_DIR, 'tools')
    if os.path.isdir(d):
        files = sorted(_glob.glob(os.path.join(d, '*.json')))
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
    import glob as _glob
    d = os.path.join(DATA_DIR, 'articles')
    if os.path.isdir(d):
        files = sorted(_glob.glob(os.path.join(d, '*.json')))
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
            # 只内链已发布工具，未发布（published=False）不生成链接，避免 404
            if not t.get('published', True):
                continue
            nm = (t.get('name') or '').strip()
            sl = t.get('slug')
            if nm and sl:
                m.append((nm, sl))
        m.sort(key=lambda x: len(x[0]), reverse=True)
        _TOOL_LINK_MAP = m
    return _TOOL_LINK_MAP

# 内链正则缓存：工具名超过 512 会击穿 re.compile 内置缓存，导致每个工具页重复编译 7.7万次正则（35s/页）。
# 改为模块级缓存，每个工具名全局只编译一次（2026-08-05 修复）。
_LINK_PAT_CACHE = {}
def _get_link_pat(name):
    pat = _LINK_PAT_CACHE.get(name)
    if pat is None:
        if re.search(r'[\u4e00-\u9fff]', name):
            pat = re.compile(re.escape(name))
        else:
            pat = re.compile(r'(?<![A-Za-z0-9])' + re.escape(name) + r'(?![A-Za-z0-9])', re.I)
        _LINK_PAT_CACHE[name] = pat
    return pat

def inject_internal_links(html, current_slug='', max_links=5):
    """在正文 HTML 的文本节点中，把提到的其他工具名替换为指向 /tools/slug/ 的内链。
    规则：
    - 每个工具（slug）在单页内最多内链一次（仅首次出现时），避免重复内链。
    - 只处理标签之间的纯文本，跳过已在 <a> 内的文本，避免破坏标签或嵌套 <a>。
    """
    if not html:
        return html
    link_map = get_tool_link_map()
    parts = re.split(r'(<[^>]+>)', html)
    in_link = False
    count = 0
    linked_slugs = set()  # 已内链的 slug，保证单页内同一工具只链一次
    for i, part in enumerate(parts):
        if not part:
            continue
        if part.startswith('<'):
            if re.match(r'<a\b', part, re.I) and 'href' in part:
                in_link = True
            elif part.startswith('</a>'):
                in_link = False
            continue
        if in_link or count >= max_links:
            continue
        for name, slug in link_map:
            if slug == current_slug or slug in linked_slugs:
                continue
            if name in _LINK_STOPWORDS or len(name) < 3:
                continue
            pat = _get_link_pat(name)
            m = pat.search(part)
            if m:
                matched = m.group(0)
                repl = f'<a href="/tools/{slug}/" class="ilink">{matched}</a>'
                part = part[:m.start()] + repl + part[m.end():]
                parts[i] = part
                count += 1
                linked_slugs.add(slug)
                break  # 替换后跳出：避免后续短工具名在新插入的<a>内嵌套匹配
    return ''.join(parts)

# 已发布工具 slug 集合缓存（坏链清理用）
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

def clean_broken_tool_links(html):
    """把指向未发布/不存在工具/文章的链接降级为纯文本，避免 404（2026-08-07 修复）。
    覆盖 /tools/<slug>/、/tools/<slug>/index.html、/articles/<slug>/、带域名的完整 URL。
    2026-08-08 修复：/articles/ 下的非文章路径（分类页 reviews/tutorials/analysis、
    列表分页 page/N）不是文章链接，不能被降级——正则收紧为 URL 到 slug 即结束，
    并对已知分类页 slug 白名单放行。"""
    published = get_published_tool_slugs()
    try:
        _arts = load_articles()
        art_slugs = {a.get('slug') for a in _arts}
    except Exception:
        art_slugs = set()
    # /articles/ 下的非文章目录（内容分类页），保持链接
    _valid_article_dirs = {cp['slug'] for cp in ARTICLE_CATEGORY_PAGES} | {'page'}

    def _fix(m):
        kind = m.group(1)   # 'tools' 或 'articles'
        slug = m.group(2)   # 实际 slug
        if kind == 'tools' and slug in published:
            return m.group(0)
        if kind == 'articles' and (slug in art_slugs or slug in _valid_article_dirs):
            return m.group(0)
        return m.group(3)  # 降级为纯文本，保留链接文字

    return re.sub(
        r'<a\s[^>]*?href="[^"]*?/(tools|articles)/([A-Za-z0-9._\-]+)(?:/index\.html|/(?:\?[^"]*)?)?"[^>]*>(.*?)</a>',
        _fix, html, flags=re.I | re.S)

def get_category_stats(tools):
    """
    统计每个分类下的工具数量，并返回一个字典。
    例如：{'AI对话': 8, 'AI绘画': 12}
    """
    category_counts = {}
    for tool in tools:
        if tool.get('published', False) and 'category' in tool:
            category = tool['category']
            category_counts[category] = category_counts.get(category, 0) + 1
    return category_counts

def build_tool_title(tool):
    """功能定位流标题：从工具自身 description 提炼定位，不依赖百度原词（消除跨实体噪声）。"""
    name = tool['name']
    pos = gen_positioning(tool)
    return build_title(name, pos, BUILD_YEAR)

def build_tool_cross_links(tool, all_compares=None, all_alternatives=None, all_rankings=None):
    """生成工具页『相关对比/替代/排行』区块，救活孤岛详情页（P0-6）。"""
    slug = tool['slug']
    cat = tool.get('category', '')
    cards = ''
    # P0-3（2026-08-09）：同名不同 slug 的对比/替代页只保留一个，避免用户看到重复链接
    seen_titles = set()

    # 本工具参与的对比页
    for c in (all_compares or []):
        if slug in c.get('compared_tools', []) and c.get('slug'):
            _t = (c.get('title') or '').strip()
            if _t and _t in seen_titles:
                continue
            seen_titles.add(_t)
            cards += (f'<a href="/compare/{c["slug"]}/" class="cross-link-card">'
                      f'⚖️ {escape_html(_t)}</a>\n')

    # 以本工具为目标的替代页
    for a in (all_alternatives or []):
        if a.get('target_tool') == slug and a.get('slug'):
            _t = (a.get('title') or '').strip()
            if _t and _t in seen_titles:
                continue
            seen_titles.add(_t)
            cards += (f'<a href="/alternatives/{a["slug"]}/" class="cross-link-card">'
                      f'🔄 {escape_html(_t)}</a>\n')

    # 本分类的排行榜
    for r in (all_rankings or []):
        if r.get('type') == 'category' and r.get('category') == cat and r.get('slug'):
            cards += (f'<a href="/ranking/{r["slug"]}/" class="cross-link-card">'
                      f'📊 {escape_html(r["title"])}</a>\n')
            break

    if not cards:
        return ''
    return f'''<div class="related-tools tool-cross-links">
        <h3>🔗 {escape_html(tool["name"])} 相关对比、替代与排行</h3>
        <div class="related-grid">{cards}</div>
    </div>'''

def build_compare_section_html(tool, tool_map):
    """渲染 A-vs-B 竞品对比小节(数据来自已核查竞品的实时字段, 结论数据驱动)。"""
    cs = tool.get('compare_section')
    if not cs or not cs.get('competitors'):
        return ''
    comps = [tool_map[s] for s in cs['competitors'] if s in tool_map]
    if len(comps) < 2:
        return ''
    rows = [tool] + comps
    head = ('<thead><tr><th>工具</th><th>编辑评分</th><th>价格</th><th>核心功能</th><th>平台</th></tr></thead>')
    body = '<tbody>'
    for i, t in enumerate(rows):
        hl = ' class="compare-current"' if i == 0 else ''
        feats = '、'.join((t.get('features') or [])[:3]) or (t.get('verified_features') or [])[:3] or '—'
        if isinstance(feats, list):
            feats = '、'.join(feats)
        body += (f'<tr{hl}><td><a href="/tools/{t["slug"]}/">'
                 f'{escape_html(t["name"])}</a></td>'
                 f'<td>{escape_html(str(t.get("rating", "")))}</td>'
                 f'<td>{escape_html(str(t.get("price", "")))}</td>'
                 f'<td>{escape_html(str(feats))}</td>'
                 f'<td>{escape_html(str(t.get("platform", "") or t.get("verified_platform", "")))}</td></tr>')
    body += '</tbody>'
    verdict = cs.get('verdict', '')
    return f'''<div class="compare-section">
        <h3>🆚 {escape_html(tool["name"])} 竞品对比</h3>
        <div class="compare-table-wrap"><table>
            {head}{body}
        </table></div>
        <p class="compare-verdict">{escape_html(verdict)}</p>
        <p class="compare-note">* 对比基于已核查的同赛道竞品数据, 编辑评分代表本站对该工具受欢迎度/实用度的评定。</p>
    </div>'''

def build_tool_page(tool, all_tools, all_articles=None, all_compares=None, all_alternatives=None, all_rankings=None):
    """生成单个工具详情页的完整HTML"""
    slug = tool['slug']

    # ── SEO关键词：优先用seo_keywords字段，fallback到模板 ───────────────
    seo_kw_list = tool.get('seo_keywords', [])
    if seo_kw_list:
        seo_kw = ','.join(k.strip() for k in seo_kw_list if k.strip())
    else:
        seo_kw = f"{tool['name']},{tool['name']}评测,{tool['name']}使用教程,{tool.get('category','')},AI工具"

    # ── 相关工具（自动补足到5个：同分类2-3个 + 跨分类2-3个）──────────────
    related_html = ''
    manually_related = tool.get('related', [])
    manually_related_tools = [t for t in all_tools if t['slug'] in manually_related and t['slug'] != slug]

    same_category = [t for t in all_tools if t['slug'] != slug and t.get('category') == tool.get('category')]
    other_category = [t for t in all_tools if t['slug'] != slug and t.get('category') != tool.get('category')]

    import random
    same_shuffled = same_category.copy()
    other_shuffled = other_category.copy()
    random.seed(42)  # 保证每次生成结果稳定

    # 优先用手动指定的，超出的自动补
    selected = manually_related_tools.copy()
    for t in same_shuffled:
        if len(selected) >= 5:
            break
        if t not in selected:
            selected.append(t)
    for t in other_shuffled:
        if len(selected) >= 5:
            break
        if t not in selected:
            selected.append(t)

    if selected:
        related_cards = ''
        for r in selected[:5]:
            related_cards += f'''<a href="/tools/{r['slug']}/" class="related-card">
                {tool_icon_html(r, size='sm')}
                <div style="font-weight:600;">{r['name']}</div>
                <div style="font-size:13px;color:#666;">{r['category']}</div>
            </a>
'''
        related_html = f'''<div class="related-tools" id="relatedSection">
            <h3>🔗 相关工具推荐</h3>
            <div class="related-grid">{related_cards}</div>
        </div>'''

    # ── 竞品对比小节（A-vs-B, 基于已核查数据）────────────────────────
    _tool_map = {t['slug']: t for t in all_tools}
    compare_html = build_compare_section_html(tool, _tool_map)

    # ── 相关文章（工具页底部推荐2-3篇相关文章）────────────────────────
    related_articles_html = ''
    matched = []
    if all_articles:
        tool_name = tool['name'].lower()
        # 优先匹配工具名的文章
        matched = []
        for a in all_articles:
            title_lower = a.get('title', '').lower()
            desc_lower = a.get('description', '').lower()
            if tool_name in title_lower or tool_name in desc_lower:
                matched.append(a)
        # 没有精确匹配的，取同类文章
        if len(matched) < 2:
            category_articles = [a for a in all_articles if a.get('category') == tool.get('category') and a not in matched]
            matched.extend(category_articles[:3 - len(matched)])
        # 还不够，取最新文章
        if len(matched) < 2:
            for a in all_articles:
                if a not in matched:
                    matched.append(a)
                    if len(matched) >= 3:
                        break

        if matched:
            cards = ''
            for a in matched[:3]:
                cards += f'''<a href="/articles/{a['slug']}/" class="related-card">
                    <div style="font-weight:600;margin-bottom:4px;">📖 {escape_html(a['title'][:30])}</div>
                    <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
                </a>
'''
            related_articles_html = f'''<div class="related-tools">
                <h3>📚 相关文章</h3>
                <div class="related-grid">{cards}</div>
            </div>'''

    # ── 侧边栏 HTML（从同一个 selected/matched 数据生成） ──
    sidebar_tools_html = ''
    if selected:
        items = ''
        for r in selected[:5]:
            is_free = '免费' in r.get('price', '') or r.get('price', '') == ''
            tag_html = ' <span class="rel-tag free">免费</span>' if is_free else ''
            items += f'''<li class="rel-tool-item">
                {tool_icon_html(r, size='sm')}
                <a href="/tools/{r['slug']}/">{r['name']}</a>{tag_html}
            </li>'''
        sidebar_tools_html = f'''<div class="sidebar-card twocol-only">
            <h4>🔧 同类热门工具</h4>
            {items}
        </div>'''

    sidebar_articles_html = ''
    if matched:
        items = ''
        for a in matched[:3]:
            items += f"<li><a href='/articles/{a['slug']}/'>{escape_html(a['title'][:35])}</a></li>"
        sidebar_articles_html = f'''<div class="sidebar-card twocol-only">
            <h4>📖 相关文章</h4>
            <ul>{items}</ul>
        </div>'''

    # 文章内容预处理（P0-3，2026-08-09）：优缺点分析交给独立区块；FAQ 小节交给模板 faq-section。
    # 必须在 FAQ 区块之前执行——FAQ 区块需要 content_faqs 合并去重。
    content_md = tool.get('content', '')
    content_md = re.sub(r'## 优缺点分析[\s\S]*?(?=## \w)', '', content_md)
    content_md = re.sub(r'## 优缺点分析[\s\S]*$', '', content_md)
    content_md, content_faqs = extract_faq_section(content_md)

    # FAQ 区块
    faq_html = ''
    faq_schema = []
    # P0-3（2026-08-09）：合并 tool.faq 字段与正文剥离出的 FAQ，按问题去重。
    _merged_faq = []
    _seen_q = set()
    def _norm_q_key(s):
        # 去重键：去掉尾部标点/空白并小写，避免同一问题因"？/无问号"差异被判为两条
        return re.sub(r'[\s?？:：。.!！]+$', '', s).strip().lower()
    for faq_item in (tool.get('faq') or []):
        _q = (faq_item.get('question') or faq_item.get('q') or '').strip()
        _a = (faq_item.get('answer') or faq_item.get('a') or '').strip()
        _key = _norm_q_key(_q)
        if _q and _a and _key not in _seen_q:
            _seen_q.add(_key)
            _merged_faq.append({'question': _q, 'answer': _a})
    for _q, _a in content_faqs:
        _key = _norm_q_key(_q)
        if _q and _a and _key not in _seen_q:
            _seen_q.add(_key)
            _merged_faq.append({'question': _q, 'answer': _a})
    if _merged_faq:
        for faq_item in _merged_faq:
            question = faq_item['question']
            answer = faq_item['answer']
            faq_html += f'''<div class="faq-item">
                <div class="faq-q">{escape_html(question)}</div>
                <div class="faq-a">{markdown_to_html(answer)}</div>
            </div>\n'''
            # FAQ Schema
            faq_schema.append({
                '@type': 'Question',
                'name': question,
                'acceptedAnswer': {
                    '@type': 'Answer',
                    'text': answer
                }
            })
        faq_html = f'''<div class="faq-section">
            <h3>❓ 常见问题</h3>
            {faq_html}
        </div>'''

    # 跨页区块：救活对比/替代/排行孤岛页（P0-7）
    cross_links_html = build_tool_cross_links(tool, all_compares, all_alternatives, all_rankings)

    # 功能列表
    features_html = ''
    if tool.get('features'):
        for f in tool['features']:
            features_html += f'<div class="feature-item">{f}</div>\n'
        features_html = f'<div class="features-grid">{features_html}</div>'

    # 优缺点
    pros_cons_html = ''
    if tool.get('pros') and tool.get('cons'):
        pros_html = ''.join(f'<li>{p}</li>' for p in tool['pros'])
        cons_html = ''.join(f'<li>{c}</li>' for c in tool['cons'])
        pros_cons_html = f'''<div class="pros-cons">
            <div class="pros">
                <h4>👍 优点</h4>
                <ul>{pros_html}</ul>
            </div>
            <div class="cons">
                <h4>👎 缺点</h4>
                <ul>{cons_html}</ul>
            </div>
        </div>'''

    # 徽章（防御：badge 可能是字符串而非 dict，归一化避免 AttributeError 崩溃）
    badge_html = ''
    _b = tool.get('badge')
    if isinstance(_b, str):
        _b = {'type': 'pick', 'text': _b}
    if isinstance(_b, dict) and _b.get('text'):
        badge_color = {'hot': '#ff4444', 'new': '#00aa00', 'pick': '#667eea'}.get(_b.get('type'), '#667eea')
        badge_html = f' <span class="badge" style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{_b["text"]}</span>'

    # 平台
    platform_html = ''
    if tool.get('platform'):
        platform_html = f'<div class="tool-meta-item">📦 <strong>平台</strong>：{tool["platform"]}</div>'

    # 访问量短语（2026-08-16 评分行压缩：保留客观硬数据，无数据则不显示，避免"暂无数据"尴尬）
    _visits_raw = str(tool.get('visits', '') or '').strip()
    _visits_clause = f' · 月访问约{_visits_raw}' if _visits_raw and _visits_raw not in ('暂无数据', '0', 'None') else ''

    # 结构化数据
    from datetime import datetime, timedelta
    today_iso = datetime.now().strftime('%Y-%m-%d')
    # 2026-08-01 修复: datePublished 优先用 published_date(首次发布时间), created_date(收录时间)作兜底
    # 字段语义: created_date=入库/收录时间(永不改) | published_date=首次发布时间 | updated_date=最近更新
    date_published = tool.get('datePublished', tool.get('date_published',
                        tool.get('published_date',
                         tool.get('created_date', today_iso))))
    # dateModified：优先用显式"最后更新"字段。
    # 2026-08-01 修复：原只查 dateModified/date_modified/last_updated，漏掉了数据里实际使用的
    # updated_date 字段，导致设置了 updated_date 的工具（如腾讯混元 updated_date=2026-07-26）
    # 其"更新"日期回落到"收录"日，页面上"更新"与"收录"两个日期相等。
    # 注意：绝不能默认用"今天"——否则每次构建所有工具都变今天，被搜索引擎视为作弊，
    # 且会导致"最近一周发布的工具"更新日期全部聚成同一天（2026-07-17 的 bug 根因）
    _date_mod_raw = tool.get('dateModified',
                      tool.get('date_modified',
                       tool.get('last_updated',
                        tool.get('updated_date', ''))))
    if _date_mod_raw:
        date_modified = _date_mod_raw
        # 安全护栏：若更新日早于收录日（数据异常），回退到收录日，避免出现"更新比收录还早"
        _cd_raw = tool.get('created_date') or tool.get('datePublished') or tool.get('date_published')
        if _cd_raw:
            try:
                if datetime.strptime(date_modified[:10], '%Y-%m-%d') < datetime.strptime(_cd_raw[:10], '%Y-%m-%d'):
                    date_modified = _cd_raw[:10]
            except Exception:
                pass
    elif tool.get('published_date') or tool.get('created_date'):
        # 2026-08-01 修复: 无显式更新字段时, dateModified 回落到"发布时间"(published_date)优先,
        # 其次才是收录时间(created_date) —— 避免"更新日期 < 发布日期"的逻辑矛盾
        # (如 wps-ai: 发布2026-07-31, 收录2026-03-26, 若回落收录日会显示"更新3/26早发布7/31")
        _mod_fallback = tool.get('published_date') or tool.get('created_date')
        try:
            _md = datetime.strptime(str(_mod_fallback)[:10], '%Y-%m-%d')
            date_modified = _md.strftime('%Y-%m-%d')
        except Exception:
            date_modified = date_published
    else:
        date_modified = date_published

    # 最终护栏: dateModified 绝不能早于 datePublished（更新不早于发布）
    try:
        if datetime.strptime(str(date_modified)[:10], '%Y-%m-%d') < datetime.strptime(str(date_published)[:10], '%Y-%m-%d'):
            date_modified = str(date_published)[:10]
    except Exception:
        pass

    category_slug_for_schema = get_category_slug(tool.get('category', ''))
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoollab.cn/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "全部工具",
                "item": "https://www.aitoollab.cn/tools/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": tool.get('category', ''),
                "item": f"https://www.aitoollab.cn/category/{category_slug_for_schema}/"
            },
            {
                "@type": "ListItem",
                "position": 4,
                "name": tool['name'],
                "item": f"https://www.aitoollab.cn/tools/{slug}/"
            }
        ]
    }

    # 价格/offers数组化（从tool数据提取免费版和付费版两档）
    # 修复问题8：正确解析"免费版+Plus $20/月"这类含"+"的多档价格
    raw_price = tool.get('price', '')
    price_str = str(raw_price).strip()
    import re as _re_price
    offers_data = []

    # 解析价格字符串中的所有价格档位
    # 匹配 $数字/月 或 ¥数字/月 或 数字元/月 等格式
    price_matches = _re_price.findall(r'[\$¥￥]?\s*(\d+(?:\.\d+)?)\s*/?\s*(?:月|month|year|年)', price_str, _re_price.IGNORECASE)

    # 始终有免费版 offer（如果没有明确说"付费"）
    if '免费' in price_str or not price_str or price_str in ('Free', 'free'):
        offers_data.append({
            "@type": "Offer", "name": "免费版", "price": "0",
            "priceCurrency": "USD", "description": f"{tool['name']}免费版基础功能"
        })

    # 解析出的付费档位
    for i, price_num in enumerate(price_matches):
        # 判断货币
        currency = "USD"
        if '¥' in price_str or '￥' in price_str or '元' in price_str:
            currency = "CNY"
        tier_name = "付费版" if i == 0 else f"付费版{i+1}"
        offers_data.append({
            "@type": "Offer", "name": tier_name, "price": price_num,
            "priceCurrency": currency, "description": f"{tool['name']}{tier_name}：{price_str}"
        })

    # 如果没解析出价格且字符串明确说付费，兜底
    if not offers_data and price_str:
        offers_data = [
            {"@type": "Offer", "name": "免费版", "price": "0", "priceCurrency": "USD", "description": f"{tool['name']}免费版基础功能"},
            {"@type": "Offer", "name": "付费版", "price": "0", "priceCurrency": "USD", "description": f"{tool['name']}付费版：{price_str}"}
        ]

    # developer信息（P0 Schema去厂商化：统一为编辑组）
    dev_org = {"@type": "Organization",
                "name": "AI工具宝箱编辑组",
                "url": "https://www.aitoollab.cn/author/",
                "description": "专注 AI 工具实测与对比研究的独立编辑团队"}

    # 修复问题1：ratingCount 使用编辑组实测样本量，不再用厂商visits伪造
    _editorial_rc = int(tool.get('editorial_rating_count') or 1)

    # 修复问题2：applicationCategory 按实际分类映射，不再全部用 ProductivityApplication
    _category_map = {
        'AI对话': 'ChatApplication', 'AI写作': 'WritingApplication', 'AI绘画': 'DesignApplication',
        'AI编程': 'DeveloperApplication', 'AI视频': 'VideoEditingApplication', 'AI音频': 'MusicApplication',
        'AI办公': 'BusinessApplication', 'AI设计': 'DesignApplication', 'AI搜索': 'SearchApplication',
        'AI翻译': 'TranslationApplication', 'AI自动化': 'BusinessApplication', 'AI效率': 'ProductivityApplication',
        'AI智能体': 'ProductivityApplication', 'AI开发': 'DeveloperApplication', 'AI行业应用': 'BusinessApplication'
    }
    _app_category = _category_map.get(tool.get('category', ''), 'ProductivityApplication')

    # 修复问题4：添加 url 字段（工具官网）
    _tool_url = tool.get('url', '')

    # 修复问题5：添加 image 字段（OG图作为工具图）
    _tool_image = f"https://www.aitoollab.cn/images/og/{slug}-og.png"

    software_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": tool['name'],
        "url": _tool_url if _tool_url else f"https://www.aitoollab.cn/tools/{slug}/",
        "image": _tool_image,
        "applicationCategory": _app_category,
        "applicationSubCategory": tool.get('category', ''),
        "operatingSystem": tool.get('platform', 'Web'),
        "description": tool['description'],
        "datePublished": date_published,
        "dateModified": date_modified,
        "offers": offers_data,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": _parse_rating(tool.get('rating', '')),
            "ratingCount": _editorial_rc,
            "bestRating": 5,
            "worstRating": 1
        },
        "inLanguage": ["zh", "en"]
    }

    # developer信息（始终添加author，无developer时用工具名称兜底）
    software_data["author"] = dev_org

    # 补充 featureList（如有features字段）
    if tool.get('features'):
        software_data["featureList"] = tool['features']

    # 修复问题6：添加 isRelatedTo（同类工具关联，最多5个）
    # 注意：关联工具用 WebSite 类型而非 SoftwareApplication，避免 Google 因缺少 offers 必填字段判为 invalid
    _related_tools = tool.get('related', [])
    if _related_tools and isinstance(_related_tools, list):
        _is_related_to = []
        for rel_slug in _related_tools[:5]:
            if isinstance(rel_slug, str):
                _is_related_to.append({
                    "@type": "WebSite",
                    "name": rel_slug,
                    "url": f"https://www.aitoollab.cn/tools/{rel_slug}/"
                })
        if _is_related_to:
            software_data["isRelatedTo"] = _is_related_to

    # 补充 abstract（取description前160字）
    software_data["abstract"] = tool['description'][:160] if len(tool['description']) > 160 else tool['description']

    # 补充 speakable（TTS语音播报锚点）
    software_data["speakable"] = {
        "@type": "SpeakableSpecification",
        "cssSelector": [".article-body h2", ".article-body h3", ".tool-header-info h2", ".tool-summary"]
    }

    # 修复问题7：优缺点写入 Schema（positiveNotes/negativeNotes）
    _pros = tool.get('pros', [])
    _cons = tool.get('cons', [])
    _rating_num = tool.get('rating_value', 4.0)
    if isinstance(_rating_num, str):
        _rating_num = _parse_rating(_rating_num)
    else:
        try:
            _rating_num = _parse_rating(tool.get('rating', '4.0'))
        except Exception:
            _rating_num = 4.0

    _review_body = {
        "@type": "Review",
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": _rating_num,
            "bestRating": 5
        },
        "author": {"@type": "Organization", "name": "AI工具宝箱编辑组"}
    }
    # 优点作为 positiveNotes
    if _pros and isinstance(_pros, list):
        _review_body["positiveNotes"] = {
            "@type": "ItemList",
            "itemListElement": [{"@type": "ListItem", "position": i+1, "name": p} for i, p in enumerate(_pros[:5])]
        }
    # 缺点作为 negativeNotes
    if _cons and isinstance(_cons, list):
        _review_body["negativeNotes"] = {
            "@type": "ItemList",
            "itemListElement": [{"@type": "ListItem", "position": i+1, "name": c} for i, c in enumerate(_cons[:5])]
        }
    software_data["review"] = _review_body

    structured_data = json.dumps(software_data, ensure_ascii=False, indent=2)
    breadcrumb_json = json.dumps(breadcrumb_data, ensure_ascii=False, indent=2)

    # FAQ Schema（输出到<head>，用于Google丰富摘要）
    faq_page_schema = ''
    if faq_schema:
        faq_page_schema_data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_schema
        }
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_page_schema_data, ensure_ascii=False)}</script>'

    # OG Image（自动生成缺失的OG图片）
    og_image = ensure_og_image(slug, data_obj=tool, is_article=False)

    # 信息图
    infographic_path = os.path.join(BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(tool['name'])}功能亮点信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(tool['name'])} 核心功能一览</figcaption>
        </figure>'''

    # 失效URL的"立即使用"按钮（无href，保留文字）
    _tool_link, _is_aff = get_tool_link(tool, slug, 'zh')
    if _tool_link in BROKEN_URLS:
        action_btn_html = '<span class="action-btn action-btn-primary disabled">立即使用</span>'
    elif _tool_link == '':
        # 空URL（如已下架工具）→ 指向站内同类替代品页面
        action_btn_html = '<a href="/tools/gamma/" class="action-btn action-btn-primary">查看替代工具</a>'
    else:
        _rel = 'nofollow noopener sponsored' if _is_aff else 'nofollow noopener'
        action_btn_html = f'<a href="{_tool_link}" target="_blank" rel="{_rel}" class="action-btn action-btn-primary">立即使用</a>'

    # 文章内容（content_md 已在 FAQ 区块前预处理：优缺点 / FAQ 小节剥离）
    content_html = markdown_to_html(content_md)
    content_html = shift_headings(content_html, up=1)   # h1->h2, h2->h3... 正文与模板H1解耦
    content_html = inject_internal_links(content_html, slug)
    # [#404修复] 坏链清理：未发布/不存在工具的链接降级为纯文本
    content_html = clean_broken_tool_links(content_html)

    _tool_title = build_tool_title(tool)
    _tool_title_short = _tool_title.split(' - ')[0]
    _tool_pos = gen_positioning(tool)
    _tool_meta = build_meta(tool['name'], _tool_pos, tool.get('description', ''), BUILD_YEAR, tool=tool)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_tool_title)}</title>
    <meta name="description" content="{escape_html(_tool_meta)}">
    <meta name="keywords" content="{escape_html(seo_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/tools/{slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_tool_title)}">
    <meta property="og:description" content="{escape_html(_tool_meta)}">
    <meta property="og:url" content="https://www.aitoollab.cn/tools/{slug}/">''' + (f'\n    <meta property="og:image" content="{og_image}">\n    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">\n' if og_image else '') + f'''    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_tool_title_short)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(_tool_meta)}">''' + (f'\n    <meta name="twitter:image" content="{og_image}">' if og_image else '') + f'''
    <style>{CRITICAL_CSS}</style>
    <style>{TOOL_LIKE_CSS}</style>
    <style>{TOOL_ACTION_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
<link rel="stylesheet" href="/css/ai-widget.css?v={WIDGET_CSS_VERSION}">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{structured_data}</script>
    {faq_page_schema}
{BAIDU_TONGJI}
</head>
<body data-page-type="tool" data-category="{escape_html(tool.get('category', ''))}" data-ai-tool="{escape_html(tool['name'])}" data-ai-tool-slug="{slug}">
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/tools/">全部工具</a> &gt; <a href="/category/{category_slug_for_schema}/">{escape_html(tool['category'])}</a> &gt; <span>{escape_html(tool['name'])}</span>
    </nav>

    <main class="article-container-wide">
        <div class="content-main">
        <div class="tool-header">
            <div class="tool-header-top">
                {tool_icon_html(tool, large=True)}
                <div class="tool-header-info">
                    <h1>{escape_html(tool['name'])}{badge_html}</h1>
                    <div class="tool-header-meta">编辑评分 {tool['rating']} <span class="rating-note">（受欢迎度/实用度）{_visits_clause}</span></div>
                </div>
            </div>
            <div class="tool-header-desc">
                <p class="subtitle">{escape_html(tool['description'])}</p>
            </div>
            <div class="tool-meta">
                <div class="tool-meta-item">🌐 <strong>官网</strong>：{tool['url'].replace('https://', '')}</div>
                <div class="tool-meta-item">💰 <strong>价格</strong>：{tool.get('price', '')}</div>
                {platform_html}
                <div class="tool-meta-item">🏷️ <strong>分类</strong>：{escape_html(tool['category'])}</div>
                <div class="tool-meta-item tool-meta-dates">📅 <strong>收录</strong> <time datetime="{date_published}" itemprop="datePublished">{date_published}</time> · 🔄 <strong>更新</strong> <time datetime="{date_modified}" itemprop="dateModified">{date_modified}</time></div>
            </div>
            <div class="action-bar">
                {action_btn_html}
                <button type="button" class="action-btn action-btn-ghost fav-btn" data-fav-slug="{slug}">☆ 收藏</button>
                <span class="tool-like" role="button" tabindex="0" data-slug="{slug}" aria-label="给 {escape_html(tool['name'])} 点赞" title="好用，点个赞">👍 <b class="tool-like-count">0</b></span>
                <a href="/category/" class="action-btn action-btn-ghost">全部工具</a>
                <button type="button" class="action-btn action-btn-ghost" data-copy-link data-label="复制链接">复制链接</button>
                <a href="/contact.html?tool={slug}" class="action-btn action-btn-ghost" title="价格、链接或信息有误？告诉我们">信息有误？</a>
            </div>
        </div>

        {features_html}

        <article class="article-body" data-tts>
            <div class="tool-summary">
                <strong>📋 编辑总结</strong><br>
                <span>{escape_html(tool['description'])} {'' if tool.get('price','') in ('','免费') else f'定价：{tool.get('price','')}。'}{'编辑评分：' + tool['rating'] + '。'}</span>
            </div>
            {content_html}
        </article>

        {infographic_html}

        {pros_cons_html}

        {faq_html}

        {compare_html}

        {cross_links_html}

            <div class="content-related">
                {related_html}
                {related_articles_html}
            </div>

            <div class="mobile-ad-inline">📱 继续阅读 · 猜你喜欢</div>
        </div><!-- /.content-main -->

        <div class="page-sidebar-wrap">
        <aside class="page-sidebar">
            <div class="ad-slot ad-slot-large"></div>
            {sidebar_tools_html}
            {sidebar_articles_html}
        </aside>
        </div>
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
    <script src="/js/ai-likes.js?v={LIKES_JS_VERSION}" defer></script>
    <script src="/js/ai-assistant.js?v={WIDGET_JS_VERSION}" defer></script>
    <script src="/ads/loader.js" defer></script>
</body>
</html>'''
    return html

def build_compare_page(compare_data, all_tools, all_articles=None, existing_compare_slugs=None):
    """
    生成对比页面 (Phase 2: 程序化SEO)
    URL格式: /compare/{toolA-vs-toolB}/index.html
    覆盖关键词: "XX vs XX" / "XX和XX对比" / "XX XX哪个好"
    """
    slug = compare_data.get('slug', 'unknown')
    title = compare_data.get('title', 'AI工具对比')
    subtitle = compare_data.get('subtitle', '')
    keywords = compare_data.get('keywords', [])
    content_md = compare_data.get('content', '')
    faq_list = compare_data.get('faq', [])
    compared_slugs = compare_data.get('compared_tools', compare_data.get('compared_tools', []))
    quick_verdict = compare_data.get('quick_verdict', {})

    # 获取被对比的工具对象
    compared_tools = []
    for s in compared_slugs:
        t = next((tool for tool in all_tools if tool['slug'] == s), None)
        if t:
            compared_tools.append(t)

    # Meta description（2026-08-06：兜底从「短句」升级为完整描述，消除 Bing 过短警告）
    _cmp_names = [t.get('name', '') for t in compared_tools if t.get('name')]
    if len(_cmp_names) >= 2:
        _cmp_fallback = (f"{_cmp_names[0]}和{_cmp_names[1]}哪个好？{BUILD_YEAR}年深度对比评测："
                         f"从功能、价格、优缺点、适用场景到真实实测数据逐项拆解，涵盖免费额度、"
                         f"中文可用性与上手难度，逐项打分对比后给出按预算和场景的最优选择，"
                         f"附完整选型建议，帮你一次看清差距、快速选出最适合自己的AI工具。")
    else:
        _cmp_fallback = (f"{title}：{BUILD_YEAR}年AI工具深度对比评测，从功能、价格、优缺点、"
                         f"适用场景到真实实测数据逐项拆解，涵盖免费额度与中文可用性，"
                         f"逐项打分后附完整选型建议与避坑提示，帮你快速做出最适合自己的选择。")
    _cmp_meta = compare_data.get('meta_description') or ''
    # 2026-08-13（阶段2.3）：门槛 100 → 115，避免 100~114 字的数据描述被 Bing 判过短
    meta_desc = _cmp_meta if len(_cmp_meta) >= 115 else _cmp_fallback

    # 对比工具头部（并排展示）
    compare_headers = ''
    for t in compared_tools:
        compare_headers += f'''
            <div class="compare-tool-card">
                {tool_icon_html(t, large=True)}
                <div style="font-weight:700;font-size:18px;margin-top:8px;">{escape_html(t['name'])}</div>
                <div style="font-size:13px;color:#666;">{t.get('price', '')}</div>
            </div>'''
    
    # Quick Verdict 区块
    verdict_html = ''
    if quick_verdict:
        verdict_items = ''
        for key, label in [('overall_winner', '🏆 综合推荐'), ('best_for_beginners', '🌱 新手推荐'),
                           ('best_value', '💰 性价比之选'), ('best_for_pro', '🚀 专业用户推荐')]:
            if key in quick_verdict:
                winner = quick_verdict[key]
                # 找到对应的工具
                winner_tool = next((t for t in compared_tools if t['name'] in winner or winner in t['name']), None)
                winner_name = winner_tool['name'] if winner_tool else winner
                verdict_items += f'<li><strong>{label}</strong>：{winner_name}</li>\n'
        if verdict_items:
            verdict_html = f'''<div class="quick-verdict" id="verdict">
                <h3>⚡ 快速结论</h3>
                <ul>{verdict_items}</ul>
            </div>'''

    # FAQ
    faq_html = ''
    faq_schema = []
    for faq_item in faq_list:
        q = faq_item.get('question') or faq_item.get('q', '')
        a = faq_item.get('answer') or faq_item.get('a', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{faq_html}</div>'

    # FAQ Schema
    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Article Schema（对比文章也是Article类型）- AEO+GEO 增强 EEAT 信号 2026-06-23
    from datetime import datetime as _dt
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "dateModified": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "inLanguage": "zh-CN",
        "author": {
            "@type": "Organization",
            "name": "AI工具宝箱编辑组",
            "url": "https://www.aitoollab.cn/",
            "description": "专注 AI 工具实测与对比研究的独立编辑团队",
            "knowsAbout": ["AI工具评测", "AI模型对比", "AEO内容优化", "GEO生成式引擎优化"]
        },
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoollab.cn/images/logo.png"
            },
            "foundingDate": "2026-03-21",
            "slogan": "实测数据驱动 AI 工具决策",
            "sameAs": ["https://github.com/yiweichen10/ai-toolbox"]
        },
        "isPartOf": {
            "@type": "WebSite",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/"
        }
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "工具对比", "item": "https://www.aitoollab.cn/compare/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/compare/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # 相关链接（每个被对比的工具链接到自己的工具页）
    tool_link_parts = []
    for t in compared_tools:
        s = t['slug']
        c = t['color']
        e = t['emoji']
        n = t['name']
        tool_link_parts.append(f'<a href="/tools/{s}/" style="display:inline-block;background:{c}22;color:{c};padding:6px 16px;border-radius:20px;text-decoration:none;font-size:14px;margin:4px;">{e} {n}详情</a>')
    tool_links = ''.join(tool_link_parts)

    # 内部链接：相关对比 + 相关替代方案
    related_compares_html = ''
    # 从所有已发布工具中找其他可能相关的对比组合（2026-08-13：只链接真实存在的对比页，消除 Bing 4xx 死链）
    _existing_cmp = set(existing_compare_slugs) if existing_compare_slugs is not None else None
    other_tools = [t for t in all_tools if t['slug'] not in compared_slugs][:5]
    if other_tools and compared_tools:
        extra_links = ''
        main_tool = compared_tools[0] if compared_tools else None
        for ot in other_tools[:4]:
            combo_slug = build_compare_slug_from_slugs([main_tool['slug'], ot['slug']])
            if _existing_cmp is not None and combo_slug not in _existing_cmp:
                continue
            extra_links += f'<a href="/compare/{combo_slug}/" style="font-size:13px;color:#4285F4;text-decoration:none;display:block;padding:4px 0;">→ {main_tool["name"]} vs {ot["name"]}</a>'
        if extra_links:
            related_compares_html = f'''<div class="related-tools" style="margin-top:30px;">
                <h3>🔗 更多相关对比</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{extra_links}</div>
            </div>'''

    content_html = markdown_to_html(content_md)

    # OG Image
    og_image = ensure_og_image(slug, data_obj=compare_data, is_article=True)

    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具对比,AI工具评测">
    <link rel="canonical" href="https://www.aitoollab.cn/compare/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/compare/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/compare/">工具对比</a> &gt; <span>{' vs '.join([t['name'] for t in compared_tools])}</span>
    </nav>

    <main class="article-container">
        <h1 style="text-align:center;font-size:30px;margin:8px 0 16px;color:#222;">{escape_html(title)}</h1>
        <div class="compare-header" style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;padding:24px;background:linear-gradient(135deg,#f8faff,#f0f4ff);border-radius:12px;margin-bottom:24px;">
            {compare_headers}
        </div>

        {verdict_html}

        <h2 id="overview" style="font-size:22px;color:#333;">{escape_html(subtitle) if subtitle else ''}</h2>

        <div style="margin:16px 0;display:flex;flex-wrap:wrap;gap:8px;">
            {tool_links}
        </div>

        <article class="article-body" data-tts>
            {content_html}
        </article>

        {faq_html}

        {related_compares_html}
    </main>

    <footer class="footer">
        <p>&copy; {BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_alternatives_page(alt_data, all_tools, all_articles=None):
    """
    生成替代方案页面 (Phase 3: 替代方案页)
    URL格式: /alternatives/{tool-slug}-alternatives/index.html
    覆盖关键词: "XX替代" / "XX类似工具" / "XX平替" / "代替XX"
    """
    slug = alt_data.get('slug', 'unknown')
    title = alt_data.get('title', 'AI工具替代方案')
    keywords = alt_data.get('keywords', [])
    content_md = alt_data.get('content', '')
    faq_list = alt_data.get('faq', [])
    target_slug = alt_data.get('target_tool', '')

    # 目标工具
    target_tool = next((t for t in all_tools if t['slug'] == target_slug), None)

    # Meta description（2026-08-06：兜底从「短句」升级为完整描述，消除 Bing 过短警告）
    _alt_name = target_tool.get('name', '') if target_tool else ''
    if _alt_name:
        _alt_fallback = (f"{_alt_name}替代方案大全 {BUILD_YEAR}：最好用的替代工具盘点，含免费平替、"
                         f"国产替代与同类工具对比，逐款给出价格、功能差异与真实实测点评，"
                         f"解决访问限制、价格过高、功能不足等常见问题，并附选型建议、避坑提示"
                         f"与上手成本说明，帮你快速选对最适合自己的替代工具。")
    else:
        _alt_fallback = (f"{title} {BUILD_YEAR}：最好用的替代工具盘点，含免费平替、国产替代与同类工具对比，"
                         f"逐款给出价格、功能差异与真实实测点评，并附选型建议与避坑提示，"
                         f"帮你解决访问限制与价格问题，找到最合适、最省钱的AI工具。")
    _alt_meta = alt_data.get('meta_description') or ''
    # 2026-08-13（阶段2.3）：门槛 100 → 115，避免 100~114 字的数据描述被 Bing 判过短
    meta_desc = _alt_meta if len(_alt_meta) >= 115 else _alt_fallback

    # FAQ
    faq_html = ''
    faq_schema = []
    for fi in faq_list:
        q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{faq_html}</div>'

    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # OG Image（必须在 article_schema 之前计算）
    og_image = ensure_og_image(slug, data_obj=alt_data, is_article=True)

    from datetime import datetime as _dt2
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": alt_data.get("last_updated", _dt2.now().strftime('%Y-%m-%d')),
        "dateModified": alt_data.get("last_updated", _dt2.now().strftime('%Y-%m-%d')),
        "image": og_image,
        "author": {"@type": "Organization", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/author/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱",
                      "logo": {"@type": "ImageObject", "url": "https://www.aitoollab.cn/images/logo.png"}}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "替代方案", "item": "https://www.aitoollab.cn/alternatives/"},
            {"@type": "ListItem", "position": 3, "name": target_tool['name'] if target_tool else slug, "item": f"https://www.aitoollab.cn/alternatives/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # 目标工具卡片
    target_card_html = ''
    if target_tool:
            target_card_html = f'''<div id="target" style="background:#fff5e6;border:1px solid #ffd666;border-radius:10px;padding:20px;margin:20px 0;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
            {tool_icon_html(target_tool, size='md')}
            <div><strong>寻找替代方案：</strong>{target_tool['name']}</div>
            <div style="color:#666;font-size:14px;">{target_tool.get('price','')}</div>
            <a href="/tools/{target_slug}/" style="margin-left:auto;color:#4285F4;text-decoration:none;font-size:14px;">查看原工具详情 →</a>
        </div>'''

    content_html = markdown_to_html(content_md)
    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具替代,AI工具推荐">
    <link rel="canonical" href="https://www.aitoollab.cn/alternatives/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/alternatives/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/alternatives/">替代方案</a> &gt; <span>{target_tool['name'] if target_tool else slug}</span>
    </nav>

    <main class="article-container">
        <h1 style="text-align:center;font-size:30px;margin:8px 0 16px;color:#222;">{escape_html(title)}</h1>
        {target_card_html}

        <article class="article-body">
            {content_html}
        </article>

        {faq_html}
    </main>

    <footer class="footer">
        <p>&copy; {BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_compare_slug_from_slugs(slugs):
    """从slug列表构建对比页slug（供内部链接使用）"""
    return '-'.join(sorted(slugs))

def load_compare_data():
    """加载对比数据文件"""
    compare_file = os.path.join(DATA_DIR, 'compare_data.json')
    if os.path.exists(compare_file):
        with open(compare_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"compares": [], "alternatives": [], "metadata": {}}

def load_quiz_data():
    """加载Quiz数据文件 (Phase 4)"""
    quiz_file = os.path.join(DATA_DIR, 'quiz_data.json')
    if os.path.exists(quiz_file):
        with open(quiz_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"quizzes": [], "metadata": {}}

def load_ranking_data():
    """加载排名数据文件 (Phase 5)"""
    ranking_file = os.path.join(DATA_DIR, 'ranking_data.json')
    if os.path.exists(ranking_file):
        with open(ranking_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"rankings": [], "metadata": {}}

# ════════════════════════════════════════════════════════
# Phase 4: Quiz 页面构建
# ════════════════════════════════════════════════════════

def build_quiz_page(quiz_data, all_tools, all_articles=None):
    """
    生成 Quiz/工具选择器页面 (Phase 4)
    URL: /quiz/{slug}/index.html 或 /quiz/index.html (总入口)
    覆盖关键词: "AI工具选择器"、"哪个AI工具好"、"AI工具推荐测试"
    """
    slug = quiz_data.get('slug', 'unknown')
    title = quiz_data.get('title', 'AI工具选择器')
    keywords = quiz_data.get('keywords', [])
    questions = quiz_data.get('questions', [])
    content = quiz_data.get('content')  # AI生成的内容
    rec_tool_slugs = quiz_data.get('recommended_tools', [])
    category = quiz_data.get('category', 'all')
    is_main_entry = (quiz_data.get('target_url') == '/quiz/') or (slug == 'ai-tool-finder-2026')

    # Meta description（2026-08-06：短兜底升级为完整描述，消除 Bing 过短警告）
    _qz_meta = quiz_data.get('meta_description') or ''
    if len(_qz_meta) >= 115:
        meta_desc = _qz_meta
    else:
        _qz_cat = 'AI' if category == 'all' else category
        meta_desc = (f"{title}：通过{len(questions)}道场景化问答，结合功能需求、预算与使用习惯，"
                     f"快速定位最适合你的{_qz_cat}工具，附推荐工具清单、价格与真实实测点评，"
                     f"从免费额度、上手难度到核心能力多维度匹配，逐步缩小选择范围，"
                     f"最终给出首选与备选方案，帮你告别选择困难，一键找到合适的AI工具。")

    # 构建问答交互 HTML
    questions_html = ''
    for i, q in enumerate(questions):
        qid = q.get('id', f'q{i+1}')
        options_html = ''
        for j, opt in enumerate(q.get('options', [])):
            val = opt.get('value', f'opt{j}')
            label_text = opt.get('label', '')
            options_html += f'''                <label class="quiz-option" data-question="{qid}" data-value="{val}">
                    <input type="radio" name="{qid}" value="{val}"> {escape_html(label_text)}
                </label>\n'''
        questions_html += f'''            <div class="quiz-question" data-question-id="{qid}">
                <h3>{i+1}. {escape_html(q['text'])}</h3>
                <div class="quiz-options">{options_html}                </div>
            </div>
'''

    # 推荐工具卡片（基于答案匹配）——附带工具属性用于前端过滤
    rec_tools_html = ''
    # 构建工具属性 JSON 供前端匹配使用
    _tool_attr_map = {}
    if rec_tool_slugs:
        for rs in rec_tool_slugs[:12]:
            tool = next((t for t in all_tools if t['slug'] == rs), None)
            if not tool:
                continue
            _tags = [tag.get('text', '') if isinstance(tag, dict) else str(tag) for tag in tool.get('tags', [])]
            _tool_attr_map[tool['slug']] = {
                'name': tool['name'],
                'category': tool.get('category', ''),
                'price': tool.get('price', ''),
                'tags': _tags,
                'is_free': '免费' in tool.get('price', '') or tool.get('price', '') == '',
                'has_api': any('API' in str(f) for f in tool.get('features', [])),
                'platform': tool.get('platform', ''),
            }
            rec_tools_html += f'''            <div class="quiz-recommendation" data-tool-slug="{tool['slug']}" data-category="{tool.get('category','')}" data-is-free='{str(_tool_attr_map[tool['slug']]['is_free']).lower()}' data-tags='{json.dumps(_tags, ensure_ascii=False)}' style="display:none;">
                <a href="/tools/{tool['slug']}/" class="rec-card">
                    {tool_icon_html(tool, size='sm')}
                    <div class="rec-info">
                        <strong>{escape_html(tool['name'])}</strong>
                        <span>{escape_html(tool.get('price',''))} | {tool['rating']}</span>
                        <p>{escape_html(tool['description'][:80])}</p>
                    </div>
                    <span class="rec-arrow">查看详情 →</span>
                </a>
            </div>\n'''

    # AI内容区域
    content_html = ''
    faq_section = ''
    faq_schema_list = []

    if content:
        # Intro
        intro = content.get('intro', '')
        if intro:
            content_html += f'<div class="quiz-intro">{markdown_to_html(intro)}</div>'

        # Tool recommendations from AI
        for tr in content.get('tool_recommendations', []):
            tname = tr.get('tool_name', 'Unknown')
            tprofile = tr.get('match_profile', '')
            strengths = tr.get('strengths', [])
            weaknesses = tr.get('weaknesses', [])
            strengths_html = ''.join(f'<li>{s}</li>' for s in strengths)
            weaknesses_html = ''.join(f'<li>{w}</li>' for w in weaknesses)
            content_html += f'''<div class="tool-rec-detail">
                <h3>{tname}</h3>
                <p>{tprofile}</p>
                <div class="tw-col">
                    <div><strong>优势</strong><ul>{strengths_html}</ul></div>
                    <div><strong>不足</strong><ul>{weaknesses_html}</ul></div>
                </div>
            </div>'''

        # Content sections
        for sec in content.get('content_sections', []):
            heading = sec.get('heading', '')
            body = sec.get('body', '')
            if heading and body:
                content_html += f'<section><h2>{escape_html(heading)}</h2>{markdown_to_html(body)}</section>'

        # FAQ
        faq_items = content.get('faq', [])
        for fi in faq_items:
            q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
            if q and a:
                faq_section += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
                faq_schema_list.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})

        # Conclusion
        conclusion = content.get('conclusion', '')
        if conclusion:
            content_html += f'<div class="quiz-conclusion">{markdown_to_html(conclusion)}</div>'

    if faq_section:
        faq_section = f'<div class="faq-section"><h3>常见问题</h3>{faq_section}</div>'

    # FAQ Schema
    faq_page_schema = ''
    if faq_schema_list:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_list}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Article Schema
    from datetime import datetime as _dtq
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": quiz_data.get("last_updated", _dtq.now().strftime('%Y-%m-%d')),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具选择器", "item": "https://www.aitoollab.cn/quiz/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    og_image = ensure_og_image(slug, data_obj=quiz_data, is_article=True)
    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具选择器,AI工具推荐">
    <link rel="canonical" href="https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
{BAIDU_TONGJI}
    <style>
    .quiz-container {{ max-width:800px;margin:0 auto; }}
    .quiz-progress {{ display:flex;justify-content:space-between;margin-bottom:24px;padding:12px;background:var(--surface-2,#f8f9fa);border-radius:10px; }}
    .quiz-progress .step {{ font-size:12px;color:var(--text-muted,#999); }}
    .quiz-progress .step.active {{ color:#4285F4;font-weight:700; }}
    .quiz-question {{ background:var(--surface,#fff);padding:24px;border-radius:12px;margin-bottom:16px;box-shadow:var(--shadow-sm,0 1px 4px rgba(0,0,0,0.08)); }}
    .quiz-question h3 {{ margin:0 0 16px;color:var(--text-main,#333); }}
    .quiz-options {{ display:flex;flex-direction:column;gap:10px; }}
    .quiz-option {{ display:block;padding:14px 18px;border:2px solid var(--border,#e8e8e8);border-radius:10px;cursor:pointer;transition:all 0.2s;font-size:15px;color:var(--text-main); }}
    .quiz-option:hover {{ border-color:#4285F4;background:rgba(66,133,244,0.08); }}
    .quiz-option input:checked + span, .quiz-option.selected {{ border-color:#4285F4;background:rgba(66,133,244,0.14); }}
    .quiz-option input {{ display:none; }}
    .quiz-result {{ text-align:center;padding:32px;display:none; }}
    .quiz-result h2 {{ color:#4285F4;margin-bottom:20px; }}
    .quiz-recommendation {{ margin:12px 0; }}
    .rec-card {{ display:flex;align-items:center;gap:16px;padding:16px;border:1px solid var(--border,#e8e8e8);border-radius:12px;text-decoration:none;color:inherit;transition:all 0.2s; }}
    .rec-card:hover {{ border-color:#4285F4;box-shadow:0 4px 12px rgba(66,133,244,0.15);transform:translateY(-1px); }}
    .rec-icon {{ width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0; }}
    .rec-info {{ flex:1; }}
    .rec-info strong {{ display:block;font-size:16px; }}
    .rec-info span {{ color:var(--text-muted,#666);font-size:13px; }}
    .rec-info p {{ margin:4px 0 0;color:var(--text-muted,#888);font-size:13px; }}
    .rec-arrow {{ color:#4285F4;font-size:14px;flex-shrink:0; }}
    .btn-quiz-submit {{ display:block;width:100%;padding:16px;background:linear-gradient(135deg,#4285F4,#5b9aff);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:700;cursor:pointer;margin-top:16px;transition:opacity 0.2s; }}
    .btn-quiz-submit:hover {{ opacity:0.9; }}
    .quiz-intro {{ background:var(--surface-2,#f0f7ff);padding:20px;border-radius:10px;margin-bottom:24px;border-left:4px solid #4285F4; }}
    .quiz-conclusion {{ background:var(--surface-2,#f8f9fa);padding:20px;border-radius:10px;margin-top:24px; }}
    .tool-rec-detail {{ margin:20px 0;padding:20px;background:var(--surface,#fff);border-radius:10px;border:1px solid var(--border,#eee); }}
    .tool-rec-detail h3 {{ color:var(--text-main,#333);margin-top:0; }}
    [data-theme="dark"] .quiz-intro {{ background:var(--surface-2) !important; }}
    [data-theme="dark"] .quiz-progress, [data-theme="dark"] .quiz-question,
    [data-theme="dark"] .quiz-conclusion, [data-theme="dark"] .tool-rec-detail {{ background:var(--surface) !important; }}
    [data-theme="dark"] .quiz-option {{ border-color:var(--border) !important; }}
    [data-theme="dark"] .quiz-option:hover, [data-theme="dark"] .quiz-option.selected,
    [data-theme="dark"] .quiz-option input:checked + span {{ background:rgba(66,133,244,0.14) !important;border-color:#4285F4 !important; }}
    .tw-col {{ display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px; }}
    @media(max-width:600px){{ .tw-col{{grid-template-columns:1fr;}} .rec-card{{flex-wrap:wrap;}} }}
    </style>
'''

    # Build progress steps HTML (outside f-string to avoid scope issues)
    _ps_parts = []
    for i, q in enumerate(questions):
        _qid = q.get('id', 'q' + str(i+1))
        _qtext = escape_html(q['text'][:15])
        _active = ' active' if i == 0 else ''
        _ps_parts.append('<span class="step' + _active + '" data-step="' + _qid + '">' + str(i+1) + '. ' + _qtext + '</span>')
    _ps_parts.append('<span class="step" data-step="result">结果</span>')
    progress_steps = '\n                    '.join(_ps_parts)

    html += f'''
</head>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/quiz/">AI工具选择器</a> &gt; <span>{title[:25]}...</span>
    </nav>

    <main class="article-container">
        <div class="quiz-container">
            <h1 style="text-align:center;">{escape_html(title)}</h1>

            <div id="quizForm">
                <div class="quiz-progress">
                    {progress_steps}
                </div>

{questions_html}
                <button class="btn-quiz-submit" onclick="showQuizResult()">查看我的推荐工具</button>
            </div>

            <div id="quizResult" class="quiz-result">
                <h2>根据你的需求，我们推荐以下AI工具</h2>
{rec_tools_html}
                <button class="btn-quiz-submit" style="margin-top:20px;" onclick="resetQuiz()" style="background:#667eea;">重新测试</button>
            </div>

            {content_html}

            {faq_section}
        </div>
    </main>

    <footer class="footer">
        <p>&copy; {BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + ICP_BEIAN + '''</p>
    </footer>
''' + BACK_TO_TOP_BLOCK + '''
<script>
// Quiz 交互逻辑 v2 — 支持取消选择 + 智能匹配推荐
(function(){
    // 点击选项：支持选中/取消
    document.querySelectorAll('.quiz-option').forEach(function(opt){
        opt.addEventListener('click', function(e){
            // 阻止 label 默认行为，手动控制 radio
            e.preventDefault();
            var radio = this.querySelector('input[type="radio"]');
            var name = radio.name;
            // 如果已选中，则取消；否则选中
            if (this.classList.contains('selected')) {
                this.classList.remove('selected');
                radio.checked = false;
            } else {
                document.querySelectorAll('.quiz-option input[name="'+name+'"]').forEach(function(o){
                    o.closest('.quiz-option').classList.remove('selected');
                    o.checked = false;
                });
                this.classList.add('selected');
                radio.checked = true;
            }
            updateProgress();
        });
    });

    // 更新进度条高亮
    function updateProgress(){
        var answered = document.querySelectorAll('.quiz-option.selected').length;
        var total = document.querySelectorAll('.quiz-question').length;
        document.querySelectorAll('.quiz-progress .step').forEach(function(s,i){
            s.classList.toggle('active', i < answered);
        });
    }

    // 答案 → 工具匹配规则
    var ANSWER_MATCH_RULES = {
        q1: function(v, tool){
            var cat = tool.getAttribute('data-category') || '';
            var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
            var map = {
                'chat':   ['AI对话','AI搜索','AI效率'],
                'writing':['AI写作','AI办公'],
                'image':  ['AI绘画','AI设计'],
                'code':   ['AI编程','AI自动化']
            };
            var match = map[v] || [];
            return match.indexOf(cat) !== -1 || match.some(function(t){ return tags.indexOf(t) !== -1; });
        },
        q2: function(v, tool){
            if(v === 'free') return tool.getAttribute('data-is-free') === 'true';
            if(v === 'any') return true;
            if(v === 'low'){
                var p = (tool.getAttribute('data-tags')||'[]');
                return p.indexOf('免费增值') !== -1 || p.indexOf('免费可用') !== -1;
            }
            return true;
        },
        q3: function(v, tool){
            if(v === 'cn'){
                var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
                return tags.indexOf('国内可用') !== -1 || tags.indexOf('国产') !== -1;
            }
            return true;
        },
        q4: function(v, tool){
            return true; // 用户类型不硬过滤，只影响排序
        },
        q5: function(v, tool){
            return true; // 看重什么不硬过滤，只影响排序
        }
    };

    // 答案 → 排序加分（软匹配）
    function computeScore(answers, tool){
        var score = 0;
        if(answers.q1){
            var cat = tool.getAttribute('data-category') || '';
            var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
            var map = {'chat':['AI对话'],'writing':['AI写作'],'image':['AI绘画','AI设计'],'code':['AI编程']};
            var m = map[answers.q1] || [];
            if(m.indexOf(cat) !== -1) score += 10;
            if(m.some(function(t){ return tags.indexOf(t) !== -1; })) score += 5;
        }
        if(answers.q2 === 'free' && tool.getAttribute('data-is-free') === 'true') score += 8;
        if(answers.q2 === 'any') score += 3;
        if(answers.q4 === 'pro' || answers.q4 === 'power') score += 3;
        return score;
    }

    window.showQuizResult = function(){
        var answers = {};
        document.querySelectorAll('.quiz-option input:checked').forEach(function(el){
            answers[el.name] = el.value;
        });
        var totalQ = ''' + str(len(questions)) + ''';
        if(Object.keys(answers).length < totalQ){
            alert('请回答完所有问题后再查看推荐！（或点击已选选项可取消选择）');
            return;
        }

        document.getElementById('quizForm').style.display = 'none';
        var resultDiv = document.getElementById('quizResult');
        resultDiv.style.display = 'block';

        // 智能匹配：根据答案过滤+排序推荐工具
        var cards = resultDiv.querySelectorAll('.quiz-recommendation');
        var scored = [];
        cards.forEach(function(el){
            var matchCount = 0;
            var slug = el.getAttribute('data-tool-slug');
            for(var qid in answers){
                var ruleFn = ANSWER_MATCH_RULES[qid];
                if(ruleFn && ruleFn(answers[qid], el)){
                    matchCount++;
                }
            }
            var sortScore = computeScore(answers, el);
            scored.push({el: el, match: matchCount, sortScore: sortScore});
        });

        // 按匹配数降序 → 排序分降序
        scored.sort(function(a,b){
            if(b.match !== a.match) return b.match - a.match;
            return b.sortScore - a.sortScore;
        });

        // 显示匹配度最高的前6个，其余隐藏
        scored.forEach(function(item, i){
            if(i < 6 && item.match > 0){
                item.el.style.display = 'block';
                item.el.style.order = i;
            } else {
                item.el.style.display = 'none';
            }
        });

        // 如果没有任何匹配（理论不该发生），显示全部
        var visible = resultDiv.querySelectorAll('.quiz-recommendation[style*="display: block"], .quiz-recommendation[style*="display:block"]');
        if(visible.length === 0){
            scored.forEach(function(item){ item.el.style.display = 'block'; });
        }

        // 更新进度条
        document.querySelectorAll('.quiz-progress .step').forEach(function(s){ s.classList.add('active'); });

        window.scrollTo({top: resultDiv.offsetTop - 20, behavior:'smooth'});
    };

    window.resetQuiz = function(){
        document.getElementById('quizResult').style.display = 'none';
        document.getElementById('quizForm').style.display = 'block';
        document.querySelectorAll('.quiz-option input').forEach(function(el){ el.checked = false; });
        document.querySelectorAll('.quiz-option').forEach(function(el){ el.classList.remove('selected'); });
        document.querySelectorAll('.quiz-recommendation').forEach(function(el){ el.style.display = 'none'; el.style.order = ''; });
        updateProgress();
        window.scrollTo({top:0, behavior:'smooth'});
    };
})();
</script>
</body>
</html>'''
    return html

# ════════════════════════════════════════════════════════
# Phase 5: Ranking 页面构建
# ════════════════════════════════════════════════════════

def build_ranking_page(ranking_data, all_tools, all_articles=None):
    """
    生成排名页面 (Phase 5)
    URL: /ranking/{slug}/index.html 或 /ranking/index.html (总榜入口)
    覆盖关键词: "AI工具排行榜"、"AI工具排名2026"、"热门AI工具"
    """
    slug = ranking_data.get('slug', 'unknown')
    title = ranking_data.get('title', 'AI工具排行榜')
    keywords = ranking_data.get('keywords', [])
    ranked_tools = ranking_data.get('ranked_tools', [])[:20]  # 展示前20
    # 2026-08-13（Bing 4xx 修复）：只展示已发布工具，避免排行页指向未发布工具的死链
    _rk_published = get_published_tool_slugs()
    ranked_tools = [t for t in ranked_tools if t.get('slug') in _rk_published]
    total_tools = ranking_data.get('total_tools', len(ranked_tools))
    content = ranking_data.get('content') or {}  # AI分析内容（None时用空字典）
    rtype = ranking_data.get('type', 'special')
    category = ranking_data.get('category', '')
    icon = ranking_data.get('icon', '📊')
    methodology = ranking_data.get('methodology', {})
    last_updated = ranking_data.get('last_updated', '')

    is_overall = (slug == '2026-ai-tools-overall-ranking')

    # Meta description（2026-08-06：短兜底升级为完整描述，消除 Bing 过短警告）
    _rk_meta = ranking_data.get('meta_description') or ''
    if len(_rk_meta) >= 115:
        meta_desc = _rk_meta
    else:
        _rk_cat = category or 'AI'
        _rk_name = _rk_cat.replace('AI', '', 1) if _rk_cat.startswith('AI') else _rk_cat
        meta_desc = (f"{title}：{BUILD_YEAR}年最新{_rk_cat}工具排行，基于热度与实测数据综合评分，"
                     f"收录{total_tools}款工具，逐款给出价格、免费额度、功能亮点与上榜理由，"
                     f"覆盖主流及国产AI工具，每日更新、数据可溯源，帮你快速选出最值得用的"
                     f"{_rk_name}AI工具，避开踩坑。")

    # v6.5: 预计算有实测评测的工具 slug 集合（用于上榜理由）
    _reviewed_slugs = set()
    if all_articles:
        for _a in all_articles:
            _rel = _a.get('related_tools') or []
            if isinstance(_rel, list):
                for _r in _rel:
                    if isinstance(_r, str):
                        _reviewed_slugs.add(_r)

    def _rank_reason(item):
        """从真实数据生成一句话上榜理由"""
        parts = []
        _v = str(item.get('visits') or '').strip()
        if _v:
            parts.append('月访问 ' + _v)
        _r = str(item.get('rating') or '').strip().replace('⭐', '').strip()
        if _r:
            parts.append('评分 ' + _r)
        _p = str(item.get('price') or '').strip()
        if '免费' in _p:
            parts.append('免费可用')
        elif _p:
            parts.append(_p[:18])
        if item.get('slug') in _reviewed_slugs:
            parts.append('有实测评测')
        return ' · '.join(parts[:3]) or '编辑收录'

    # 排名表格
    table_rows = ''
    medals = ['\U0001F947', '\U0001F948', '\U0001F949']  # 金银铜
    top3_html = ''
    # P0/UX（2026-08-09）：排行页统一用真实工具 LOGO（assets/icons），无图标才回退 emoji 色块
    def _rank_icon(item, size=40):
        slug = item.get('slug', '')
        _, web_path = resolve_icon(slug)
        if web_path:
            return (f'<img src="{web_path}" alt="{escape_html(item.get("name", ""))}" loading="lazy" '
                    f'width="{size}" height="{size}" '
                    f'style="width:{size}px;height:{size}px;border-radius:10px;object-fit:contain;'
                    f'background:#fff;padding:3px;border:1px solid var(--border-light);flex:none;">')
        return (f'<span style="font-size:{int(size * 0.55)}px;background:{item.get("color", "#667eea")};'
                f'width:{size}px;height:{size}px;border-radius:10px;display:inline-flex;'
                f'align-items:center;justify-content:center;flex:none;">{item.get("emoji", "🔧")}</span>')

    for i, item in enumerate(ranked_tools[:3]):
        top3_html += f'<a class="rank-top3-card" href="/tools/{item["slug"]}/">'
        top3_html += '<span class="rt3-medal">' + medals[i] + '</span>'
        top3_html += '<span class="rt3-icon">' + _rank_icon(item, 52) + '</span>'
        top3_html += '<span class="rt3-body"><span class="rt3-name">' + escape_html(item.get('name', '')) + '</span>'
        top3_html += '<span class="rt3-reason">' + escape_html(_rank_reason(item)) + '</span></span></a>'
    if top3_html:
        top3_html = '<div class="rank-top3">' + top3_html + '</div>'
    for i, item in enumerate(ranked_tools):
        rank = item.get('rank', i+1)
        medal = medals[i] if i < 3 else str(rank)
        score = item.get('score', 0)
        sd = item.get('scores', {})
        tool_name = item.get('name', 'Unknown')
        tool_emoji = item.get('emoji', '🔧')
        tool_color = item.get('color', '#666')
        price = item.get('price', '')
        rating = item.get('rating', '')
        badge_html = ''
        badge = item.get('badge', {})
        if isinstance(badge, dict) and badge.get('text'):
            btype = badge.get('type', '')
            bcolor_map = {'hot': '#ff4444', 'new': '#00aa00', 'pick': '#667eea'}
            bcolor = bcolor_map.get(btype, '#667eea')
            badge_html = '<span class="badge" style="background:' + bcolor + ';color:#fff;font-size:11px;padding:2px 6px;border-radius:3px;">' + badge['text'] + '</span>'
        
        # 分数条
        if rank <= 3:
            bar_color = '#4285F4'
        elif rank <= 10:
            bar_color = '#667eea'
        else:
            bar_color = '#999'
        bar_width = min(score, 100)
        
        # 趋势箭头
        if rank <= 3:
            trend_color = '#00aa00'
            trend_sym = '&#8593;'
        elif rank > 15:
            trend_color = '#ff4444'
            trend_sym = ''
        else:
            trend_color = '#666'
            trend_sym = '&#8594;' if rank <= 10 else ''
        
        table_rows += f'''                <tr class="rank-row" data-rank="{rank}">
                    <td class="rank-num">{medal}</td>
                    <td class="rank-tool">
                        <a href="/tools/{item['slug']}/" style="display:flex;align-items:center;gap:10px;text-decoration:none;color:inherit;">
                            {_rank_icon(item, 40)}
                            <span style="font-weight:600;">{escape_html(tool_name)}</span> {badge_html}
                        </a>
                    </td>
                    <td class="rank-reason">{_rank_reason(item)}</td>
                    <td class="rank-score">
                        <div class="score-bar"><div class="score-fill" style="width:{bar_width}%;background:{bar_color};"></div></div>
                        <span class="score-val">{score}</span>
                    </td>
                    <td class="rank-rating">{rating or '-'}</td>
                    <td class="rank-price">{escape_html(price) or '免费'}</td>
                    <td class="rank-trend">
                        <span style="color:{trend_color};">{trend_sym}</span>
                    </td>
                </tr>
'''

    # AI内容区域
    content_html = ''
    faq_section = ''
    faq_schema_list = []
    trend_badge = ''
    from datetime import datetime as _rdt

    if content:
        # Summary / 综述
        summary = content.get('summary', '')
        if summary:
            content_html += f'<div class="ranking-summary">{markdown_to_html(summary)}</div>'
            trend_badge = '<div class="live-badge">实时更新 · 数据截至 ' + (last_updated or _rdt.now().strftime('%Y-%m-%d')) + '</div>'

        # Top3 分析
        top3 = content.get('top3_analysis', [])
        if top3:
            top3_html = ''
            for ta in top3:
                top3_html += f'''<div class="podium-analysis">
                    <h3>第{ta['rank']}名 - {ta.get('tool_name','')}</h3>
                    {markdown_to_html(ta.get('analysis',''))}
                </div>'''
            content_html += f'<div class="top3-section">{top3_html}</div>'

        # 趋势分析
        trend = content.get('trend_analysis', '')
        if trend:
            content_html += f'<div class="trend-section"><h2>行业趋势分析</h2>{markdown_to_html(trend)}</div>'

        # 分类洞察
        insights = content.get('category_insights', [])
        if insights:
            ins_html = ''.join(f'<div class="insight-card"><h3>{escape_html(i["insight_title"])}</h3>{markdown_to_html(i["content"])}</div>' for i in insights)
            content_html += f'<div class="insights-section"><h2>深度洞察</h2>{ins_html}</div>'

        # FAQ
        for fi in content.get('faq', []):
            q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
            if q and a:
                faq_section += f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'
                faq_schema_list.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})

        # Conclusion
        conclusion = content.get('conclusion', '')
        if conclusion:
            content_html += f'<div class="ranking-conclusion">{markdown_to_html(conclusion)}</div>'

    if faq_section:
        faq_section = f'<div class="faq-section"><h3>关于本排名</h3>{faq_section}</div>'

    # FAQ Schema
    faq_ps = ''
    if faq_schema_list:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_list}
        faq_ps = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Schema (use _rdt already imported above)
    # _dtr alias for backward compat
    _dtr = _rdt
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": ranking_data.get("last_updated", _dtr.now().strftime('%Y-%m-%d'))[:10],
        "dateModified": last_updated[:10] if last_updated else _dtr.now().strftime('%Y-%m-%d'),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # ItemList Schema：把排名工具列表结构化，GEO 价值最高
    # AI 搜索引擎可直接引用"第1名是XX，第2名是XX"
    _item_list_elements = []
    for _i, _it in enumerate(ranked_tools[:20], 1):
        _item_list_elements.append({
            "@type": "ListItem",
            "position": _i,
            "name": _it.get('name', ''),
            "url": f"https://www.aitoollab.cn/tools/{_it.get('slug', '')}/",
        })
    if _item_list_elements:
        _item_list_schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": title,
            "description": meta_desc,
            "numberOfItems": len(_item_list_elements),
            "itemListElement": _item_list_elements
        }
        item_list_schema_json = json.dumps(_item_list_schema, ensure_ascii=False, indent=2)
    else:
        item_list_schema_json = ''

    # Breadcrumb
    bc_name_2 = "AI工具排行榜" if is_overall else (category + "排行榜" if category else "排行榜")
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具排行", "item": "https://www.aitoollab.cn/ranking/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/ranking/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    og_image = ensure_og_image(slug, data_obj=ranking_data, is_article=True)

    # 相关链接：其他排名
    related_links = ''
    other_ranks = [
        ('2026-ai-tools-overall-ranking', '综合热度榜'),
        ('best-free-ai-tools-ranking-2026', '免费工具榜'),
        ('best-value-ai-tools-ranking-2026', '性价比榜'),
        ('rising-ai-tools-2026-trending', '新兴趋势榜')
    ]
    for rslug, rname in other_ranks:
        if rslug != slug:
            related_links += f'<a href="/ranking/{rslug}/" class="rank-sub-link">{rname} →</a>\n'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具排行榜,AI工具排名,AI热度排行">
    <link rel="canonical" href="https://www.aitoollab.cn/ranking/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/ranking/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    <script type="application/ld+json">{item_list_schema_json}</script>
    {faq_ps}
{BAIDU_TONGJI}
    <style>
    .ranking-container {{ max-width:1200px; }}
    .ranking-hero {{ display:flex;align-items:center;gap:14px;text-align:left;padding:16px 20px;background:linear-gradient(135deg,#f0f4ff,#e8f0fe);border-radius:14px;margin-bottom:16px; }}
    .ranking-hero .hero-icon {{ font-size:32px;margin:0;flex:none;width:52px;height:52px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.72);border-radius:14px; }}
    .ranking-hero .hero-text {{ flex:1;min-width:0; }}
    .ranking-hero h1 {{ margin:0;font-size:22px; }}
    .ranking-hero p {{ color:#666;margin:3px 0 0;font-size:13.5px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden; }}
    .ranking-hero .live-badge {{ margin-top:0;margin-left:auto;flex:none; }}
    @media (max-width:640px) {{ .ranking-hero {{ flex-wrap:wrap;padding:14px;gap:10px; }} .ranking-hero h1 {{ font-size:19px; }} .ranking-hero .hero-icon {{ width:42px;height:42px;font-size:26px; }} .ranking-hero .live-badge {{ margin-left:0; }} }}
    .live-badge {{ display:inline-block;background:#00c853;color:#fff;font-size:12px;padding:3px 12px;border-radius:12px;margin-top:10px;font-weight:600;animation:pulse 2s infinite; }}
    @keyframes pulse {{ 0%{{opacity:1}} 50%{{opacity:.7}} 100%{{opacity:1}} }}
    .ranking-table-wrap {{ overflow-x:auto;background:var(--surface,#fff);border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:28px; }}
    .ranking-table {{ width:100%;border-collapse:collapse;min-width:600px; }}
    .ranking-table th {{ background:var(--surface-2,#f8f9fa);padding:14px 12px;text-align:left;font-size:13px;color:var(--text-muted,#666);border-bottom:2px solid var(--border,#eee);white-space:nowrap; }}
    .ranking-table td {{ padding:12px;border-bottom:1px solid var(--border-light,#f0f0f0);vertical-align:middle; }}
    .rank-row:hover {{ background:var(--surface-2,#f8f9ff); }}
    .rank-num {{ font-size:20px;text-align:center;width:50px;font-weight:700; }}
    .rank-tool a {{ font-weight:600; }}
    .rank-tool a > span {{ max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    .rank-score {{ min-width:120px; }}
    .score-bar {{ width:80px;height:6px;background:#eee;border-radius:3px;display:inline-block;vertical-align:middle;overflow:hidden; }}
    .score-fill {{ height:100%;border-radius:3px;transition:width .5s; }}
    .score-val {{ font-weight:700;font-size:14px;margin-left:6px; }}
    .rank-rating {{ white-space:nowrap; }}
    .rank-price {{ color:#666;font-size:13px;white-space:nowrap;max-width:240px;overflow:hidden;text-overflow:ellipsis; }}
    .rank-trend {{ text-align:center;font-size:16px; }}
    .rank-sub-nav {{ display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;justify-content:center; }}
    .rank-sub-link {{ display:inline-block;padding:8px 16px;background:#f0f4ff;color:#4285F4;border-radius:20px;text-decoration:none;font-size:13px;font-weight:600;transition:all .2s; }}
    .rank-sub-link:hover {{ background:#4285F4;color:#fff; }}
    .rank-reason {{ font-size:12px;color:var(--text-muted,#888);max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    .rank-top3 {{ display:flex;gap:12px;margin-bottom:16px; }}
    .rank-top3-card {{ flex:1;display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--surface,#fff);border:1px solid var(--border,#eee);border-radius:12px;text-decoration:none;color:inherit;transition:box-shadow .15s,transform .15s;min-width:0; }}
    .rank-top3-card:hover {{ box-shadow:0 6px 18px rgba(0,0,0,.08);transform:translateY(-2px); }}
    .rt3-medal {{ font-size:22px;flex:none; }}
    .rt3-icon {{ width:40px;height:40px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;font-size:20px;flex:none; }}
    .rt3-body {{ min-width:0;display:flex;flex-direction:column; }}
    .rt3-name {{ font-size:14px;font-weight:700;color:var(--text-main,#333); }}
    .rt3-reason {{ font-size:12px;color:var(--text-muted,#888);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    @media (max-width:768px) {{ .rank-top3 {{ flex-direction:column;gap:8px; }} .ranking-table-wrap {{ overflow:hidden;background:transparent;box-shadow:none;border-radius:0;margin-bottom:20px; }} .ranking-table {{ width:100%;min-width:0; }} .ranking-table thead {{ display:none; }} .ranking-table tbody {{ display:flex;flex-direction:column;gap:8px; }} .ranking-table tbody, .ranking-table tr, .ranking-table td {{ display:block; }} .ranking-table tr.rank-row {{ display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:2px 10px;align-items:center;background:#fff;border:1px solid #eee;border-radius:12px;padding:10px 12px; }} .ranking-table tr.rank-row > td {{ min-width:0;padding:0; }} .rank-num {{ grid-row:1/3;grid-column:1;width:auto;font-size:16px;font-weight:700;text-align:center; }} .rank-tool {{ grid-row:1;grid-column:2; }} .rank-tool .badge {{ display:none; }} .rank-tool a {{ gap:8px;font-size:13.5px;min-width:0; }} .rank-tool a > span {{ max-width:100%;white-space:normal;overflow:hidden; }} .rank-score {{ grid-row:1;grid-column:3;display:flex;align-items:center;gap:6px;min-width:0; }} .score-bar {{ width:56px; }} .score-val {{ display:inline;font-size:13px;font-weight:700;margin-left:0; }} .rank-rating {{ grid-row:2;grid-column:3;font-size:12px;color:#888;white-space:nowrap; }} .rank-price {{ grid-row:2;grid-column:2;max-width:none;white-space:normal;font-size:12px;line-height:1.35;overflow-wrap:anywhere; }} .ranking-table td.rank-reason, .ranking-table td.rank-trend {{ display:none; }} }}
    .ranking-summary {{ background:#f0f7ff;padding:20px 24px;border-left:4px solid #4285F4;border-radius:8px;margin-bottom:24px;font-size:15px;line-height:1.8; }}
    .podium-analysis {{ background:#fff;padding:20px;border-radius:10px;margin:12px 0;border:1px solid #eee; }}
    .podium-analysis h3 {{ color:#333;margin-top:0; }}
    .trend-section,.insights-section {{ margin:28px 0; }}
    .insight-card {{ background:#fafbfc;padding:20px;border-radius:10px;margin:12px 0;border-left:4px solid #667eea; }}
    .insight-card h3 {{ margin-top:0;color:#333; }}
    .ranking-conclusion {{ background:#f8f9fa;padding:24px;border-radius:10px;margin-top:24px; }}
    .methodology-note {{ background:#fffbf0;border:1px solid #ffd666;border-radius:8px;padding:16px 20px;margin:20px 0;font-size:13px;color:#856404; }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href/">首页</a> &gt; <a href="/ranking/">AI工具排行</a> &gt; <span>{title[:25]}...</span>
    </nav>

    <main class="article-container ranking-container">
        <div class="ranking-hero">
            <div class="hero-icon">{icon}</div>
            <div class="hero-text">
                <h1>{escape_html(title)}</h1>
                <p>{escape_html(meta_desc[:120])}</p>
            </div>
            {trend_badge}
        </div>

        <div class="rank-sub-nav">
            {related_links}
        </div>

        {top3_html}

        <div class="ranking-table-wrap">
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>工具名称</th>
                        <th>上榜理由</th>
                        <th>综合分</th>
                        <th>评分</th>
                        <th>价格</th>
                        <th>趋势</th>
                    </tr>
                </thead>
                <tbody>
{table_rows}
                </tbody>
            </table>
        </div>

        {content_html}

        {faq_section}

        <section class="ranking-analysis" style="margin:32px 0 24px;padding:24px;background:var(--surface-2,#f8fafc);border-radius:12px;">
            <h2 style="font-size:20px;font-weight:700;margin-bottom:16px;">📊 {title}深度解读</h2>
            <p style="line-height:1.8;color:var(--text-muted,#475569);margin-bottom:14px;">本榜单收录了{total_tools}款主流AI工具，综合评分基于热度、质量、功能、价值和新鲜度五大维度。榜单每日自动更新，确保数据时效性。排名前列的工具在用户访问量、功能完整度和性价比方面表现突出，是当前AI工具市场的头部产品。</p>
            <p style="line-height:1.8;color:var(--text-muted,#475569);margin-bottom:14px;">从榜单趋势来看，AI对话和AI编程类工具持续领跑，免费和免费增值模式的工具占据多数席位。国产AI工具（如DeepSeek、Kimi、豆包）在中文场景下表现优秀，与国际工具形成有力竞争。建议用户根据具体使用场景和预算选择，多数工具提供免费版可供试用。</p>
            <p style="line-height:1.8;color:var(--text-muted,#475569);">如需更精准的推荐，可使用我们的<a href="/quiz/" style="color:#4285F4;">AI工具选择器</a>，3分钟找到最适合你的AI助手。也可查看<a href="/category/" style="color:#4285F4;">全部分类</a>浏览特定领域的工具。</p>
        </section>

        <div class="methodology-note">
            <strong>排名说明：</strong>本排名基于多维度数据综合计算（热度30% + 质量25% + 功能20% + 价格15% + 新鲜度10%），每日自动更新。数据来源于工具官方信息、用户评价聚合和市场活跃度指标。排名仅供参考，具体选择请根据个人需求和实际体验决定。
        </div>
    </main>

    <footer class="footer">
        <p>&copy; {BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 更新于 {(last_updated or _rdt.now().strftime('%Y-%m-%d %H:%M'))} &middot; ''' + ICP_BEIAN + '''</p>
    </footer>
''' + BACK_TO_TOP_BLOCK + '''
 </body>
</html>'''
    return html

# ═══════════════════════════════════════════════════════
# Phase 5b: Live Dashboard 数据加载与页面构建（动态数据面板）
# ═══════════════════════════════════════════════════════

def load_live_data():
    """加载 live dashboard 数据"""
    path = os.path.join(DATA_DIR, 'live_data.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    print(f'  [WARN] live_data.json not found at {path}')
    return {}

def _build_ranking_index_page(all_rankings):
    """生成 ranking/index.html 总入口页：列出所有排行榜链接（2026-08-13：移除 Meta Refresh，改为真实栏目页）"""
    items_html = ''
    for rd in all_rankings:
        rslug = rd.get('slug', '')
        title = rd.get('title', rslug)
        icon = rd.get('icon', '📊')
        category = rd.get('category', '')
        if not rslug:
            continue
        # 短标题（去掉年份前缀等）
        short_title = title.replace('2026年', '').replace('2026', '').strip()
        cat_tag = f'<span style="font-size:11px;color:#888;">{category}</span>' if category else ''
        items_html += f'''    <li>
      <a href="/ranking/{rslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">{icon}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(short_title)}</div>
          {cat_tag}
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具排行榜 - 全部榜单 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部排行榜：综合热度榜、免费工具榜、性价比榜、分类排行等19个分类与主题榜单，覆盖AI对话、写作、绘画、编程、视频、办公等全领域，均基于热度与实测数据综合评分并每日更新，附价格、免费额度与上榜理由，帮你快速选出最值得用的AI工具。">
    <link rel="canonical" href="https://www.aitoollab.cn/ranking/">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">📊 AI工具排行榜</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_rankings)}</strong> 个榜单 · 覆盖AI全领域 · 每日更新
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html

def _build_compare_index_page(all_compares):
    """生成 compare/index.html 总入口页：列出所有对比评测链接"""
    items_html = ''
    for cp in (all_compares or []):
        cslug = cp.get('slug', '')
        title = cp.get('title', cslug)
        if not cslug:
            continue
        items_html += f'''    <li>
      <a href="/compare/{cslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">⚖️</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(title)}</div>
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''
    if not items_html:
        items_html = '<li style="padding:24px;text-align:center;color:#999;">暂无对比评测内容</li>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具对比评测 - 全部对比 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部对比评测：ChatGPT vs Claude、Midjourney vs Flux 等40+组深度对比，从功能、价格、优缺点到适用场景逐项拆解，并给出按预算和场景的选型结论，基于真实使用数据，帮你快速选出最适合自己的AI工具。">
    <link rel="canonical" href="https://www.aitoollab.cn/compare/">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">⚖️ AI工具对比评测</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_compares or [])}</strong> 篇深度对比 · 帮你选对AI工具
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html

def _build_alternatives_index_page(all_alternatives):
    """生成 alternatives/index.html 总入口页：列出所有替代方案链接"""
    items_html = ''
    for alt in (all_alternatives or []):
        aslug = alt.get('slug', '')
        title = alt.get('title', aslug)
        if not aslug:
            continue
        items_html += f'''    <li>
      <a href="/alternatives/{aslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">🔄</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(title)}</div>
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''
    if not items_html:
        items_html = '<li style="padding:24px;text-align:center;color:#999;">暂无替代方案内容</li>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具替代方案推荐 - 全部替代方案 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部替代方案推荐：寻找ChatGPT、Midjourney、Cursor等热门AI工具的最佳平替，含免费方案、国产替代与同类工具对比，附真实实测点评与选型建议，帮你解决访问限制、价格过高与功能不足等问题，数据每日更新、内容可溯源。">
    <link rel="canonical" href="https://www.aitoollab.cn/alternatives/">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">🔄 AI工具替代方案</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_alternatives or [])}</strong> 个替代方案 · 找到最适合你的AI工具
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html

def build_live_page(live_data, page_config, all_tools, articles):
    """
    构建 live dashboard 的子页面。
    type: dashboard | matrix | trend | heatmap | battle
    """
    from datetime import datetime as _ldt

    page_type = page_config.get('type', 'dashboard')
    page_slug = page_config.get('slug', 'unknown')
    page_title = page_config.get('title', 'AI工具实时监控面板')
    keywords = page_config.get('keywords', [])
    meta_desc = page_config.get('meta_description', '')
    # P2-16: 如果 meta_desc 偏短（<115字），自动补充关键词和描述（2026-08-13 阈值 80→115，后缀加长）
    if len(meta_desc) < 115:
        _live_desc_suffix = f"AI工具宝箱提供{page_title}功能，涵盖多维度数据分析，帮助用户快速了解AI工具市场格局和趋势变化，支持按分类、价格与热度筛选对比。数据每日自动更新、来源可溯源，覆盖{TOOL_COUNT}款主流AI工具。"
        meta_desc = meta_desc + _live_desc_suffix if meta_desc else _live_desc_suffix
    icon_emoji = page_config.get('icon', '\U0001f4ca')

    stats = live_data.get('stats', {})
    matrix_data = live_data.get('comparison_matrix', {})
    trends_data = live_data.get('trends', {})
    heatmap_data = live_data.get('heatmap', {})
    h2h_data = live_data.get('head_to_head', {})
    last_updated = stats.get('last_updated') or ''

    # ---- 根据类型构建不同内容区 ----
    if page_type == 'matrix':
        section_html = _live_section_matrix(matrix_data)
    elif page_type == 'trend':
        section_html = _live_section_trend(trends_data)
    elif page_type == 'heatmap':
        section_html = _live_section_heatmap(heatmap_data)
    elif page_type == 'battle':
        section_html = _live_section_battle(h2h_data)
    else:
        section_html = _live_section_dashboard(stats, matrix_data, trends_data, heatmap_data, h2h_data)

    nav_tabs = _live_nav_tabs(page_slug)

    # ── Schema: WebPage + BreadcrumbList ──
    _live_date = (last_updated or _ldt.now().strftime('%Y-%m-%d'))[:10]
    _live_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page_title,
        "description": meta_desc,
        "url": f"https://www.aitoollab.cn/live/{page_slug}/",
        "dateModified": _live_date,
        "inLanguage": "zh-CN",
        "isPartOf": {
            "@type": "WebSite",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/"
        },
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    _live_schema_json = json.dumps(_live_schema, ensure_ascii=False, indent=2)
    _live_breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "实时面板", "item": "https://www.aitoollab.cn/live/dashboard/"},
            {"@type": "ListItem", "position": 3, "name": page_title, "item": f"https://www.aitoollab.cn/live/{page_slug}/"}
        ]
    }
    _live_breadcrumb_json = json.dumps(_live_breadcrumb, ensure_ascii=False, indent=2)

    # OG 图
    _live_og_image = ensure_og_image(page_slug)

    # Build HTML parts
    header_nav = '<header class="header">\n        <div class="header-inner">\n            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>\n        </div>\n    </header>'
    page_icon = '<span class="tool-icon-lg">' + icon_emoji + '</span>'
    h1_tag = '<h1>' + escape_html(page_title) + '</h1>'
    subtitle = '<p class="subtitle">' + escape_html(meta_desc) + '</p>'
    update_info = '<div class="last-update">📅 数据更新：' + escape_html(last_updated) + '</div>'
    methodology = '<div class="methodology-note"><strong>数据说明：</strong>本面板数据由AIToolBox团队每日自动更新聚合，来源包括工具官方信息、公开搜索热度、用户评价等。所有数据仅供参考，具体选择请以各工具官方页面为准。</div>'
    footer = '<footer class="footer"><p>&copy; ' + str(BUILD_YEAR) + ' AI工具宝箱 · 每日精选优质AI工具 · 更新于 ' + _ldt.now().strftime('%Y-%m-%d %H:%M') + ' · ' + ICP_BEIAN + '</p></footer>'

    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <title>' + escape_html(page_title) + ' - AI工具宝箱</title>\n'
        '    <meta name="description" content="' + escape_html(meta_desc) + '">\n'
        '    <meta name="keywords" content="' + ','.join(keywords) + ',AI工具宝箱,aitoollab.cn">\n'
        '    <link rel="canonical" href="https://www.aitoollab.cn/live/' + page_slug + '/">\n'
        '    <meta property="og:type" content="website">\n'
        '    <meta property="og:title" content="' + escape_html(page_title) + ' - AI工具宝箱">\n'
        '    <meta property="og:description" content="' + escape_html(meta_desc) + '">\n'
        '    <meta property="og:url" content="https://www.aitoollab.cn/live/' + page_slug + '/">\n'
        '    <meta property="og:image" content="' + (_live_og_image or 'https://www.aitoollab.cn/images/logo.png') + '">\n'
        '    <meta property="og:image:width" content="1200">\n'
        '    <meta property="og:image:height" content="630">\n'
        '    <meta name="twitter:card" content="summary_large_image">\n'
        '    <meta name="twitter:title" content="' + escape_html(page_title) + ' - AI工具宝箱">\n'
        '    <meta name="twitter:description" content="' + escape_html(meta_desc) + '">\n'
        '    <meta name="twitter:image" content="' + (_live_og_image or 'https://www.aitoollab.cn/images/logo.png') + '">\n'
        '<style>' + CRITICAL_CSS + '</style>'
        "<link rel=\"preload\" href=\"/css/style.min.css?v=" + CSS_VERSION + "\" as=\"style\" onload=\"this.rel='stylesheet'\">"
        "<noscript><link rel=\"stylesheet\" href=\"/css/style.min.css?v=" + CSS_VERSION + "\"></noscript>"
        '    <script type="application/ld+json">' + _live_breadcrumb_json + '</script>\n'
        '    <script type="application/ld+json">' + _live_schema_json + '</script>\n'
        '</head>\n<body>\n'
        + header_nav + '\n\n    ' + nav_tabs + '\n\n'
        '    <main class="container main-content">\n'
        '        <div class="page-header">\n            '
        + page_icon + '\n            '
        + h1_tag + '\n            '
        + subtitle + '\n            '
        + update_info + '\n'
        '        </div>\n\n        '
        + section_html + '\n\n        '
        + methodology + '\n'
        '    </main>\n\n    '
        + footer + '\n'
        + BACK_TO_TOP_BLOCK + '\n'
        '</body>\n</html>'
    )
    return html

def _live_nav_tabs(active_slug):
    tabs = [
        ('dashboard', '📊 总览面板'),
        ('compare-matrix', '🔍 对比矩阵'),
        ('trend-tracker', '📈 趋势追踪'),
        ('market-heatmap', '🗺️ 市场热力图'),
        ('head-to-head', '⚔️ 巅峰对决'),
    ]
    links_parts = []
    for s, label in tabs:
        cls = ' class="active"' if s == active_slug else ''
        links_parts.append('<a href="/live/' + s + '/"' + cls + '>' + label + '</a>')
    return '<nav class="live-nav"><div class="container">' + ' '.join(links_parts) + '</div></nav>'

def _live_section_dashboard(stats, matrix, trends, heatmap, h2h):
    total_tools = stats.get('total_tools', 0)
    total_cats = stats.get('total_categories', 0)
    avg_rating = stats.get('avg_rating', 0)
    today_active = str(stats.get('today_active', '0'))
    week_new = str(stats.get('this_week_new', 0))
    price_dist = stats.get('price_distribution', {})
    pf = str(price_dist.get('free', 0))
    pfm = str(price_dist.get('freemium', 0))
    pp_val = max(int(price_dist.get('paid', 0)), 1)

    parts = []

    # 统计卡片
    parts.append('<section class="live-stats-grid">'
        '<div class="stat-card stat-primary"><div class="stat-number">%s</div><div class="stat-label">收录工具总数</div></div>'
        '<div class="stat-card"><div class="stat-number">%s</div><div class="stat-label">覆盖分类</div></div>'
        '<div class="stat-card"><div class="stat-number">⭐ %s</div><div class="stat-label">平均评分</div></div>'
        '<div class="stat-card"><div class="stat-number">%s</div><div class="stat-label">今日活跃</div></div>'
        '<div class="stat-card"><div class="stat-number">+%s</div><div class="stat-label">本周新增</div></div>'
        '</section>' % (str(total_tools), str(total_cats), str(avg_rating), today_active, week_new))

    # 价格分布
    parts.append('<section class="live-section"><h2>💰 价格分布概览</h2><div class="price-dist-bar">'
        '<div class="price-item" style="flex:%s"><div class="price-badge free">免费</div><div class="price-count">%s 款</div></div>'
        '<div class="price-item" style="flex:%s"><div class="price-badge freemium">免费增值</div><div class="price-count">%s 款</div></div>'
        '<div class="price-item" style="flex:%s"><div class="price-badge paid">付费</div><div class="price-count">%s 款</div></div>'
        '</div></section>' % (pf, pf, pfm, pfm, str(pp_val), pp_val))

    # 趋势预览 Top 5
    cat_trends = trends.get('categories', [])[:5]
    if cat_trends:
        rows = ''
        for ct in cat_trends:
            pct = ct.get('change_percent', 0)
            if pct > 20: tag, arrow = '🔥 爆发', '🔺'
            elif pct > 10: tag, arrow = '📈 上升', '🔺'
            elif pct >= 0: tag, arrow = '➡️ 稳定', '📊'
            else: tag, arrow = '🔻 回落', '🔻'
            ccolor = '#00aa00' if pct > 10 else ('#cc0000' if pct < 0 else '#333')
            rows += ('<div class="trend-row"><span class="trend-cat-icon">%s</span>'
                '<span class="trend-cat-name">%s</span>'
                '<span class="trend-cat-val">%s</span>'
                '<span style="color:%s">%s %+.1f%%</span></div>') % (ct.get('icon',''), ct.get('category',''), str(ct.get('current_value','')), ccolor, arrow, pct)
        parts.append('<section class="live-section"><h2>📈 分类热度趋势 Top 5</h2><div class="trend-preview-list">' + rows + '</div>'
            '<p style="text-align:center;margin-top:12px;"><a href="/live/trend-tracker/" class="btn btn-sm">查看完整趋势 →</a></p></section>')

    # 对比矩阵预览（前8个）
    tools_list = matrix.get('tools', [])[:8]
    dims_list = matrix.get('dimensions', [])
    if tools_list and dims_list:
        headers = ''.join(['<th>' + d['name'] + '</th>' for d in dims_list])
        body_rows = ''
        for t in tools_list:
            vals = t.get('values', {})
            cells = ''
            for d in dims_list:
                v = vals.get(d['id'], '')
                dt = d.get('type', '')
                if dt == 'number': cells += '<td class="num">' + str(v) + '</td>'
                elif dt == 'badge': cells += '<td class="badge-cell">' + str(v) + '</td>'
                else: cells += '<td>' + str(v) + '</td>'
            body_rows += ('<tr><td class="tool-link-cell"><a href="%s" style="color:%s;font-weight:600;text-decoration:none;">%s %s</a></td>%s</tr>') % (
                t.get('detail_url','#'), t.get('color','#333'), t.get('emoji',''), t.get('name',''), cells)
        total_m = len(matrix.get('tools', []))
        parts.append('<section class="live-section"><h2>🔍 核心能力快速对比</h2><div class="table-responsive"><table class="live-matrix-table">'
            '<thead><tr><th>工具</th>' + headers + '</tr></thead><tbody>' + body_rows + '</tbody></table></div>'
            '<p style="text-align:center;margin-top:12px;"><a href="/live/compare-matrix/" class="btn btn-sm">查看完整矩阵（%s款工具）→</a></p></section>' % str(total_m))

    # PK对决预览
    battles = h2h.get('battles', [])[:3]
    if battles:
        b_items = ''
        for b in battles:
            verdict_short = (b.get('verdict','') or '')[:90]
            b_items += '<div class="battle-preview-card"><h4>%s</h4><p class="verdict-sm">%s...</p>' % (b.get('title',''), verdict_short)
            b_items += '<a href="/live/head-to-head/" class="btn btn-sm">查看详情 →</a></div>'
        parts.append('<section class="live-section"><h2>⚔️ 热门对决</h2><div class="battle-preview-grid">' + b_items + '</div></section>')

    return '\n'.join(parts)

def _live_section_matrix(matrix_data):
    tools_list = matrix_data.get('tools', [])
    dims_list = matrix_data.get('dimensions', [])
    headers = '<th>工具</th>' + ''.join(['<th>' + d['name'] + '</th>' for d in dims_list])
    body_rows = ''
    for t in tools_list:
        vals = t.get('values', {})
        cells = ''
        for d in dims_list:
            v = vals.get(d['id'], '')
            dt = d.get('type', '')
            if dt == 'number': cells += '<td class="num">' + str(v) + '</td>'
            elif dt == 'level':
                n = int(v) if str(v).isdigit() else 0
                stars = '★' * n + '☆' * (5 - n)
                cells += '<td class="level-cell"><span class="star-level">' + stars + '</span></td>'
            elif dt == 'badge':
                bc = 'badge-yes' if v == '✅' else ('badge-no' if v == '❌' else 'badge-neutral')
                cells += '<td class="badge-cell"><span class="%s">%s</span></td>' % (bc, str(v))
            else: cells += '<td>' + str(v) + '</td>'
        body_rows += '<tr><td class="tool-link-cell"><a href="%s" style="display:flex;align-items:center;gap:6px;color:%s;font-weight:600;text-decoration:none;">' % (t.get('detail_url','#'), t.get('color','#333'))
        body_rows += '<span style="font-size:18px;">%s</span><span>%s</span></a></td>%s</tr>' % (t.get('emoji',''), t.get('name',''), cells)

    title = matrix_data.get('title') or ''
    desc = matrix_data.get('description') or ''
    total_n = len(tools_list)
    dim_n = len(dims_list)
    return ('<section class="live-section fullwidth"><h2>%s</h2><p class="desc">%s</p>'
        '<div class="table-responsive"><table class="live-matrix-table">'
        '<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
        '<p style="text-align:center;margin-top:15px;font-size:14px;color:#666;">'
        '💡 点击工具名可跳转到详细评测页 | 共收录 %s 款工具 × %s 个维度</p></section>') % (title, desc, headers, body_rows, str(total_n), str(dim_n))

def _live_section_trend(trends):
    cats = trends.get('categories', [])
    top_tools = trends.get('top_tools', [])

    cat_cards = ''
    for ct in cats:
        pct = ct.get('change_percent', 0)
        if pct > 20: status_cls, tag = 'trend-hot', '🔥 爆发'
        elif pct > 10: status_cls, tag = 'trend-up', '📈 上升'
        elif pct >= 0: status_cls, tag = 'trend-stable', '➡️ 稳定'
        else: status_cls, tag = 'trend-down', '🔻 回落'

        weekly = ct.get('weekly_data', [])
        pts = _make_sparkline(weekly)

        cat_cards += ('<div class="trend-card %s">'
            '<div class="trend-header">'
            '<span class="trend-ct-icon">%s</span>'
            '<span class="trend-ct-name">%s</span>'
            '<span class="trend-tag">%s</span>'
            '</div>'
            '<div class="trend-body">'
            '<div class="trend-big-num">%s</div>'
            '<div class="trend-pct">%+.1f%%</div>'
            '<div class="trend-tool-count">%s 款工具</div>'
            '</div>'
            '<div class="spark-line">%s</div>'
            '</div>') % (status_cls, ct.get('icon',''), ct.get('category',''), tag,
                        str(ct.get('current_value','-')), pct, str(ct.get('tool_count',0)), pts)

    period_str = trends.get('period', '')
    result = '<section class="live-section"><h2>📂 各分类热度趋势（%s）</h2><div class="trend-cards-grid">%s</div></section>' % (period_str, cat_cards)

    tool_rows = ''
    for tt in top_tools[:10]:
        tp = tt.get('change_percent', 0)
        if tp > 5: arr = '🔺'
        elif tp >= 0: arr = '➡️'
        else: arr = '🔻'
        tc = '#00aa00' if tp > 10 else ('#cc0000' if tp < 0 else '#333')
        tool_rows += ('<tr><td><span style="font-size:16px;">%s</span> <strong>%s</strong></td>'
            '<td class="num">%s</td>'
            '<td style="color:%s;font-weight:600">%s %+.1f%%</td></tr>') % (tt.get('emoji',''), tt.get('name',''), str(tt.get('current_value','-')), tc, arr, tp)

    if tool_rows:
        result += ('<section class="live-section fullwidth"><h2>🏆 热门工具趋势排行</h2>'
            '<div class="table-responsive"><table class="live-matrix-table">'
            '<thead><tr><th>工具</th><th>当前热度</th><th>变化</th></tr></thead>'
            '<tbody>%s</tbody></table></div></section>') % tool_rows

    return result

def _make_sparkline(weekly_data):
    if not weekly_data:
        return ''
    values = [w.get('value', 0) for w in weekly_data]
    n = len(values)
    vmin, vmax = min(values), max(values)
    span = vmax - vmin if vmax != vmin else 1
    w_width = min(n * 25, 200)
    pts = []
    for i, v in enumerate(values):
        x = int(i * (w_width / max(n - 1, 1)))
        y = int(50 - ((v - vmin) / span) * 45)
        pts.append('%d,%d' % (x, y))
    pts_str = ','.join(pts)
    return '<svg width="%d" height="50" viewBox="0 0 %d 50" preserveAspectRatio="none"><polyline fill="rgba(66,133,244,0.1)" stroke="#4285F4" stroke-width="2" points="%s" /></svg>' % (w_width, w_width, pts_str)

def _live_section_heatmap(heatmap_data):
    items = heatmap_data.get('heatmap', [])
    p_labels = heatmap_data.get('price_labels', {})

    cards = ''
    for item in items:
        by_price = item.get('by_price', {})
        pcells = ''
        for pt in ['free', 'freemium']:
            pdata = by_price.get(pt, {})
            pc = pdata.get('count', 0)
            names = pdata.get('names', [])
            pl = p_labels.get(pt, pt)
            intensity = min(pc * 30, 255)
            bg = 'rgba(66,133,244,%.2f)' % (intensity / 255) if pc > 0 else 'transparent'
            bc = '#4285F4' if pc > 0 else '#ddd'
            names_txt = ', '.join(names[:3])
            if len(names) > 3:
                names_txt += ' 等%d款' % len(names)
            pcells += ('<div class="heat-cell" style="background:%s;border-color:%s">'
                '<div class="heat-label">%s</div>'
                '<div class="heat-count">%d 款</div>'
                '<div class="heat-tools">%s</div></div>') % (bg, bc, pl, pc, names_txt)

        rec_slug = item.get('recommended_slug', '#')
        cards += ('<div class="heat-row">'
            '<div class="heat-category">'
            '<span class="heat-cat-icon">%s</span>'
            '<span class="heat-cat-name">%s</span>'
            '<span class="heat-cat-meta">%d款 · ⭐%s</span>'
            '</div>'
            '<div class="heat-prices">%s</div>'
            '<div class="heat-rec">'
            '<div class="heat-feature">%s</div>'
            '<a href="/tools/%s/" class="btn btn-xs">推荐</a>'
            '</div></div>') % (item.get('icon',''), item.get('category',''), item.get('tool_count',0),
                                   str(item.get('avg_rating',0)), pcells, item.get('top_feature',''), rec_slug)

    title = heatmap_data.get('title') or ''
    desc = heatmap_data.get('description') or ''
    return '<section class="live-section fullwidth"><h2>%s</h2><p class="desc">%s</p><div class="heatmap-container">%s</div></section>' % (title, desc, cards)

def _live_section_battle(h2h):
    battles = h2h.get('battles', [])

    cards = ''
    for b in battles:
        dims = b.get('comparison_dimensions', [])
        a_name = (b.get('tools_a') or ['A'])[0]
        b_names = ', '.join(b.get('tools_b') or ['B'])

        dim_rows = ''
        sa, sb = 0, 0
        for d in dims:
            w = d.get('winner', '')
            wa = '✅' if w == 'a' else ('❌' if w == 'b' else '➖')
            wb = '✅' if w == 'b' else ('❌' if w == 'a' else '➖')
            if w == 'a': sa += 1
            elif w == 'b': sb += 1
            dim_rows += ('<tr><td class="dim-name">%s</td><td class="dim-val-a">%s %s</td><td class="dim-val-b">%s %s</td></tr>') % (
                d.get('dim',''), str(d.get('a','')), wa, str(d.get('b','')), wb)

        verdict = b.get('verdict', '')
        cards += ('<article class="battle-card">'
            '<h3 class="battle-title">%s</h3>'
            '<div class="battle-vs">'
            '<div class="team-a"><span class="team-label">%s</span><span class="score">%d</span></div>'
            '<span class="vs-badge">VS</span>'
            '<div class="team-b"><span class="team-label">%s</span><span class="score">%d</span></div>'
            '</div>'
            '<table class="battle-dim-table">'
            '<thead><tr><th>维度</th><th>A方</th><th>B方</th></tr></thead>'
            '<tbody>%s</tbody></table>'
            '<div class="battle-verdict"><strong>结论：</strong>%s</div>'
            '</article>') % (b.get('title',''), a_name, sa, b_names, sb, dim_rows, verdict)

    title = h2h.get('title') or ''
    desc = h2h.get('description') or ''
    return '<section class="live-section fullwidth"><h2>%s</h2><p class="desc">%s</p><div class="battle-container">%s</div></section>' % (title, desc, cards)

def _build_category_index_page(tools_by_category):
    """生成 category/index.html 总入口页：分类宫格卡片（点击进入类目），卡片样式对齐首页热门榜 TOP30 的 hot-mini 紧凑小卡片"""
    # 分类排序：固定顺序在前，其余按名称
    ordered_categories = ["AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频", "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率", "AI智能体", "AI开发", "AI行业应用", "AI学习", "AI检测", "AI提示词", "去中心化AI"]
    category_emojis = {
        "AI对话": "💬", "AI写作": "✍️", "AI绘画": "🎨", "AI编程": "💻",
        "AI视频": "🎬", "AI音频": "🎵", "AI办公": "📁", "AI设计": "🎯",
        "AI搜索": "🔍", "AI翻译": "🌐", "AI自动化": "⚙️", "AI效率": "⚡",
        "AI智能体": "🤖", "AI开发": "🛠️", "AI行业应用": "🏢",
        "AI学习": "📚", "AI检测": "🕵️", "AI提示词": "💬", "去中心化AI": "🔗",
    }
    # 分类徽标底色（对齐全站 --cat-* 色板）
    category_colors = {
        "AI对话": "#10b981", "AI写作": "#00C250", "AI绘画": "#f59e0b",
        "AI编程": "#3b82f6", "AI视频": "#ef4444", "AI音频": "#8b5cf6",
        "AI办公": "#0ea5e9", "AI设计": "#ec4899", "AI搜索": "#14b8a6",
        "AI翻译": "#22c55e", "AI自动化": "#f97316", "AI效率": "#a855f7",
        "AI智能体": "#a855f7", "AI开发": "#3b82f6", "AI行业应用": "#0ea5e9",
        "AI学习": "#6366f1", "AI检测": "#ef4444", "AI提示词": "#8b5cf6", "去中心化AI": "#FF6B35",
    }
    cat_names = [c for c in ordered_categories if c in tools_by_category]
    cat_names += [c for c in tools_by_category if c not in ordered_categories]

    total_cats = len(tools_by_category)
    total_tools = sum(len(v) for v in tools_by_category.values())

    # 分类卡片：hot-mini 紧凑小卡片（对齐首页热门榜结构：彩色图标块 + 名称 + 元信息），点击进入对应类目页
    cards_html = ''
    for cat_name in cat_names:
        cat_slug = get_category_slug(cat_name)
        emoji = category_emojis.get(cat_name, '📂')
        color = category_colors.get(cat_name, '#4f46e5')
        count = len(tools_by_category[cat_name])
        cards_html += (
            '<a class="hot-mini" href="/category/%s/" title="%s">'
            '<div class="hot-mini-logo-fallback" style="background:%s">%s</div>'
            '<span class="hot-mini-name">%s</span>'
            '<span class="hot-mini-meta">%d 款工具</span>'
            '</a>\n' % (cat_slug, escape_html(cat_name), color, emoji, escape_html(cat_name), count)
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）
    # 背景：文章页/工具详情页已做完 SEO+GEO，唯独分类线是空白。此前本枢纽页
    #       零 schema、零 OG、零面包屑，正文仅 hero 两句 + 卡片宫格（薄内容），
    #       且 19 个子类目在枢纽层不可见，只能从父分类页进入。
    # 目标：① 搜索引擎能理解"这是覆盖 N 个分类 / M 款工具的集合页"；
    #       ② AI 引擎（豆包/Kimi/元宝/ChatGPT）能直接抽取分类事实作答并引用本站。
    # 手法：结构化事实（速查表 + ItemList）+ 直接答案段 + FAQ + 时效信号。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'

    # 各分类典型使用场景 —— GEO 关键：让 AI 能回答"XX 场景该用哪类工具"
    category_scenes = {
        "AI对话": "日常问答、资料整理、写作与代码辅助",
        "AI写作": "公众号文案、营销稿、论文润色与改写",
        "AI绘画": "插画创作、电商配图、海报与概念设计",
        "AI编程": "代码补全、Bug修复、单元测试与重构",
        "AI视频": "短视频成片、数字人口播、字幕与剪辑",
        "AI音频": "语音合成、音频转写、配乐与降噪",
        "AI办公": "PPT生成、表格处理、会议纪要与文档总结",
        "AI设计": "UI设计、原型图、Logo与品牌视觉",
        "AI搜索": "联网搜索、文献检索、带引用来源的问答",
        "AI翻译": "文档翻译、字幕翻译、多语言本地化",
        "AI自动化": "工作流编排、数据同步、跨应用自动执行",
        "AI效率": "笔记管理、任务规划、信息聚合与提效",
        "AI智能体": "任务型Agent、自动调研、多步骤任务执行",
        "AI开发": "模型调用、向量数据库、AI应用开发框架",
        "AI行业应用": "医疗、法律、教育、电商等垂直场景",
    }

    def _top_tools(_lst, n=3):
        """按评分取该分类代表工具（GEO：具体工具名比抽象描述更易被 AI 引用）"""
        try:
            _s = sorted(_lst, key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0), reverse=True)
        except Exception:
            _s = _lst
        return [t.get('name', '') for t in _s[:n] if t.get('name')]

    # ── GEO 速查表：分类 / 工具数 / 典型场景 / 代表工具 ──
    # 表格是 AI 引擎抽取引用率最高的结构，比散落的卡片有效得多
    table_rows = ''
    for cat_name in cat_names:
        _cslug = get_category_slug(cat_name)
        _clist = tools_by_category[cat_name]
        _scene = category_scenes.get(cat_name, f'{cat_name}相关场景')
        _reps = _top_tools(_clist, 3)
        _reps_txt = '、'.join(escape_html(r) for r in _reps) if _reps else '持续收录中'
        table_rows += (
            '<tr>'
            f'<td><a href="/category/{_cslug}/"><strong>{escape_html(cat_name)}</strong></a></td>'
            f'<td style="text-align:center;">{len(_clist)}</td>'
            f'<td>{escape_html(_scene)}</td>'
            f'<td>{_reps_txt}</td>'
            '</tr>\n'
        )

    # ── 子类目入口：19 个细分场景此前在枢纽页不可见（只能从父分类页进）──
    _subdef = get_subcat_def()
    subcat_block_html = ''
    _subcat_total = 0
    for _p_slug, _pdata in _subdef.items():
        _subs = _pdata.get('subcats', {})
        if not _subs:
            continue
        _subcat_total += len(_subs)
        _p_name = _pdata.get('name', _p_slug)
        _links = ''.join(
            f'<a href="/category/{_s}/" class="subcat-pill">{escape_html(_sd.get("name", ""))}</a>'
            for _s, _sd in _subs.items()
        )
        subcat_block_html += (
            f'<div class="subcat-row"><span class="subcat-parent">'
            f'<a href="/category/{_p_slug}/">{escape_html(_p_name)}</a></span>{_links}</div>\n'
        )
    subcat_section_html = ''
    if subcat_block_html:
        subcat_section_html = f'''    <section class="cat-section" id="subcats">
        <h2>按细分场景查找（{_subcat_total} 个子类目）</h2>
        <p class="cat-section-desc">主分类偏宽泛时，可直接进入更精准的细分场景页面。</p>
{subcat_block_html}    </section>
'''

    # ── FAQ（GEO 核心）：纯文本答案，同时供页面渲染与 FAQPage schema 使用 ──
    _by_size = sorted(cat_names, key=lambda c: len(tools_by_category[c]), reverse=True)
    _top5_txt = '、'.join(f'{c}（{len(tools_by_category[c])}款）' for c in _by_size[:5])
    _all_cats_txt = '、'.join(cat_names)
    faq_items = [
        (
            "AI工具一共分为哪些类别？",
            f"AI工具宝箱把收录的 {total_tools} 款 AI 工具划分为 {total_cats} 个主分类，"
            f"分别是：{_all_cats_txt}。其中工具数量最多的是 {_top5_txt}。"
            f"每个主分类下还有更细的子类目，可按具体使用场景进一步筛选。"
        ),
        (
            "新手第一次用AI工具，应该从哪一类开始？",
            "建议从 AI对话 类工具入手，这类工具通用性最强，问答、写作、翻译、代码解释都能覆盖，"
            "无需学习成本。熟悉之后再按你的具体工作场景切入垂直分类：做内容选 AI写作、做图选 AI绘画、"
            "写代码选 AI编程、做汇报选 AI办公。"
        ),
        (
            "这些AI工具分类里有免费的吗？",
            "有。绝大多数分类都同时收录免费与付费工具，常见形式是免费额度加付费订阅。"
            "每款工具的详情页都标注了价格模式（免费/免费试用/付费），分类页支持按评分与热度排序，"
            "可优先查看标注免费的工具。"
        ),
        (
            "怎么快速找到最适合自己的AI工具？",
            "三个办法：一是用本页的分类速查表，按典型使用场景直接定位分类；"
            "二是进入子类目页，场景更精准；三是使用站内的 AI 工具选择器，回答几个问题后由系统推荐。"
            "如果已经锁定两三款候选，可以看对比页做横向比较。"
        ),
        (
            "分类和工具库多久更新一次？",
            f"工具库每日更新，分类结构随新工具收录动态调整。本页数据最后更新于 {_today_iso}，"
            f"当前共 {total_cats} 个主分类、{_subcat_total} 个子类目、{total_tools} 款工具。"
        ),
    ]
    faq_html = ''.join(
        f'<details class="cat-faq-item"><summary>{escape_html(_q)}</summary>'
        f'<div class="cat-faq-a"><p>{escape_html(_a)}</p></div></details>\n'
        for _q, _a in faq_items
    )

    # 新手入口分类：优先 AI对话（通用性最强），缺失时退回工具数最多的分类
    # 注意 slug 由 get_category_slug 生成（AI对话 → ai-chat），不可硬编码拼音
    _entry_cat = "AI对话" if "AI对话" in tools_by_category else (_by_size[0] if _by_size else "")
    _entry_link = (
        f'<a href="/category/{get_category_slug(_entry_cat)}/">{escape_html(_entry_cat)}</a>'
        if _entry_cat else '任一主分类'
    )

    # ── 结构化数据：用 json.dumps 生成，避免 f-string 大括号转义出错 ──
    _breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具分类", "item": f"{_SITE}/category/"},
        ],
    }
    _collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"AI工具推荐与导航大全 - {total_cats}大分类{total_tools}款AI工具",
        "description": f"AI工具宝箱按使用场景划分的 {total_cats} 个 AI 工具分类，"
                       f"共收录 {total_tools} 款工具，覆盖对话、写作、绘画、编程、视频等全领域。",
        "url": f"{_SITE}/category/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".cat-section h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"AI工具{total_cats}大分类",
            "numberOfItems": total_cats,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": _i + 1,
                    "name": f"{_c}工具",
                    "url": f"{_SITE}/category/{get_category_slug(_c)}/",
                    "description": f"{category_scenes.get(_c, _c + '相关场景')}，"
                                   f"收录 {len(tools_by_category[_c])} 款工具。",
                }
                for _i, _c in enumerate(_by_size)
            ],
        },
    }
    _faq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": _q,
                "acceptedAnswer": {"@type": "Answer", "text": _a},
            }
            for _q, _a in faq_items
        ],
    }
    _breadcrumb_json = json.dumps(_breadcrumb_sd, ensure_ascii=False)
    _collection_json = json.dumps(_collection_sd, ensure_ascii=False)
    _faq_json = json.dumps(_faq_sd, ensure_ascii=False)

    # ── Title / Description（2026-08-03 重写）──
    # 说明：站内未接关键词工具，以下词根为经验判断（覆盖"分类/大全/导航/合集"四类
    #       常见搜法 + 数字增强点击率），非搜索量数据验证结果。接入 GSC 后应回头校准。
    _page_title = f'AI工具推荐与导航大全 {total_cats}大分类 {total_tools}款 {BUILD_YEAR}'
    _page_desc = (f'{BUILD_YEAR}年AI工具推荐与导航大全：按使用场景划分为{total_cats}个主分类、'
                  f'{_subcat_total}个细分场景，共收录{total_tools}款AI工具（含免费工具）。'
                  f'涵盖AI对话、AI写作、AI绘画、AI视频、AI编程等全领域，'
                  f'每个分类附工具数量、典型场景与代表工具，帮你快速定位需要的AI工具。')
    _page_kw = (f'AI工具推荐,AI工具导航,AI工具大全,AI工具分类,AI工具有哪些,'
                f'AI软件分类,AI工具推荐{BUILD_YEAR},免费AI工具')

    # ── 页面内联样式：hot-mini（对齐首页热门榜 TOP30）+ 分类宫格容器 ──
    # 注意：固定宽度（沿用 .cat-grid 原样式 max-width:960px 居中），不做全屏自动宽度
    page_css = '''<style id="cat-page-hot-mini-style">
#catMiniGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px 10px;
}
.hot-mini {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px; border-radius: 12px; text-decoration: none; color: inherit;
  background: rgba(127,127,127,0.06);
  border: 1px solid rgba(127,127,127,0.12);
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.hot-mini:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.10);
  background: rgba(127,127,127,0.10);
}
.hot-mini-logo-fallback {
  width: 30px; height: 30px; border-radius: 8px; flex: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; color: #fff; line-height: 1;
}
.hot-mini-name {
  font-size: 12.5px; font-weight: 600; text-align: center; line-height: 1.2;
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hot-mini-meta { font-size: 11px; color: var(--text-muted, #64748b); }
@media (max-width: 640px) {
  #catMiniGrid { grid-template-columns: repeat(auto-fill, minmax(98px, 1fr)); gap: 10px 8px; padding: 0 14px; }
  .hot-mini-name { font-size: 12px; }
}
/* ── SEO+GEO 区块样式（2026-08-03 新增）── */
.cat-section {
  max-width: 960px; margin: 28px auto 0; padding: 0 14px;
}
.cat-section h2 {
  font-size: 20px; font-weight: 700; margin: 0 0 8px;
}
.cat-section-desc {
  font-size: 14px; color: var(--text-muted, #64748b); margin: 0 0 14px; line-height: 1.7;
}
.geo-answer {
  max-width: 960px; margin: 20px auto 0; padding: 16px 18px;
  background: rgba(0,166,79,0.06);
  border: 1px solid rgba(0,166,79,0.22);
  border-left: 4px solid #00A64F;
  border-radius: 10px; font-size: 15px; line-height: 1.85;
}
.geo-answer strong { color: #00A64F; }
.cat-table-wrap { overflow-x: auto; }
.cat-table {
  width: 100%; border-collapse: collapse; font-size: 14px;
  background: rgba(127,127,127,0.03); border-radius: 10px; overflow: hidden;
}
.cat-table th, .cat-table td {
  padding: 10px 12px; text-align: left;
  border-bottom: 1px solid rgba(127,127,127,0.14);
}
.cat-table th {
  background: rgba(127,127,127,0.08); font-weight: 600; white-space: nowrap;
}
.cat-table tr:last-child td { border-bottom: none; }
.cat-table a { color: #00A64F; text-decoration: none; }
.cat-table a:hover { text-decoration: underline; }
.subcat-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 9px 0; border-bottom: 1px dashed rgba(127,127,127,0.18);
}
.subcat-row:last-child { border-bottom: none; }
.subcat-parent {
  min-width: 96px; font-weight: 600; font-size: 13.5px;
}
.subcat-parent a { color: inherit; text-decoration: none; }
.subcat-pill {
  display: inline-block; padding: 3px 11px; border-radius: 20px;
  background: rgba(58,91,217,0.08); border: 1px solid rgba(58,91,217,0.18);
  color: #3a5bd9; text-decoration: none; font-size: 12.5px;
}
.subcat-pill:hover { background: rgba(58,91,217,0.16); }
.cat-faq-item {
  border: 1px solid rgba(127,127,127,0.16); border-radius: 10px;
  margin-bottom: 8px; background: rgba(127,127,127,0.03);
}
.cat-faq-item summary {
  cursor: pointer; padding: 12px 16px; font-weight: 600; font-size: 14.5px;
  list-style: none;
}
.cat-faq-item summary::-webkit-details-marker { display: none; }
.cat-faq-item summary::before { content: "Q "; color: #00A64F; font-weight: 700; }
.cat-faq-a { padding: 0 16px 14px; font-size: 14px; line-height: 1.85; color: var(--text-muted, #475569); }
.cat-faq-a p { margin: 0; }
.cat-updated {
  max-width: 960px; margin: 18px auto 0; padding: 0 14px;
  font-size: 12.5px; color: var(--text-muted, #94a3b8);
}
@media (max-width: 640px) {
  .cat-section h2 { font-size: 18px; }
  .cat-table th, .cat-table td { padding: 8px 9px; font-size: 13px; }
  .subcat-parent { min-width: 100%; }
}
</style>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_page_title)}</title>
    <meta name="description" content="{escape_html(_page_desc)}">
    <meta name="keywords" content="{escape_html(_page_kw)}">
    <link rel="canonical" href="{_SITE}/category/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_page_title)}">
    <meta property="og:description" content="{escape_html(_page_desc)}">
    <meta property="og:url" content="{_SITE}/category/">
    <meta property="og:image" content="{_SITE}/images/og/aitoolbox-og.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_page_title)}">
    <meta name="twitter:description" content="{escape_html(_page_desc)}">
    <meta name="twitter:image" content="{_SITE}/images/og/aitoolbox-og.png">
    <style>{CRITICAL_CSS}</style>
{page_css}
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_breadcrumb_json}</script>
    <script type="application/ld+json">{_collection_json}</script>
    <script type="application/ld+json">{_faq_json}</script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>AI工具分类</span>
    </nav>

    <div class="cat-hero">
        <h1>📂 AI工具分类大全</h1>
        <p>共 <strong>{total_cats}</strong> 个主分类 · <strong>{_subcat_total}</strong> 个细分场景 · 收录 <strong>{total_tools}</strong> 款工具</p>
        <p>按场景挑选，点击进入查看该分类下全部工具的评测与对比。</p>
    </div>

    <div class="geo-answer">
        <p>AI工具宝箱把目前收录的 <strong>{total_tools} 款 AI 工具</strong>按使用场景划分为
        <strong>{total_cats} 个主分类</strong>与 <strong>{_subcat_total} 个细分子类目</strong>。
        主分类包括{escape_html(_all_cats_txt)}。
        如果你不确定该从哪里开始，通用场景优先看 {_entry_link}，
        再按具体工作内容进入垂直分类；下方速查表列出了每个分类的工具数量、典型使用场景与代表工具。</p>
    </div>

    <div class="cat-grid" id="catMiniGrid">
{cards_html}    </div>

    <section class="cat-section" id="cat-table">
        <h2>AI工具分类速查表（{total_cats}大分类对照）</h2>
        <p class="cat-section-desc">按典型使用场景快速定位分类，代表工具按用户评分排序。</p>
        <div class="cat-table-wrap">
        <table class="cat-table">
            <thead>
                <tr><th>分类</th><th>工具数</th><th>典型使用场景</th><th>代表工具</th></tr>
            </thead>
            <tbody>
{table_rows}            </tbody>
        </table>
        </div>
    </section>

{subcat_section_html}    <section class="cat-section" id="faq">
        <h2>关于AI工具分类的常见问题</h2>
{faq_html}    </section>

    <p class="cat-updated">本页数据最后更新：{_today_iso} · 工具库每日更新</p>

    <div class="cat-back">
        <a href="/">← 返回首页，查看更多精选工具</a>
    </div>
    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p>
        <div class="footer-links">
            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
        </div>
        <p>用AI提升效率，让每个人都能享受技术红利。</p>
    </footer>
    {BACK_TO_TOP_BLOCK}
</body>
</html>'''
    return html

def get_subcat_def():
    """加载子类目定义 data/subcategories.json → {parent_slug:{name, subcats:{slug:{name,intro,how_to_choose}}}}"""
    if 'subcat_def_cache' not in globals():
        try:
            with open(os.path.join(DATA_DIR, 'subcategories.json'), 'r', encoding='utf-8') as f:
                globals()['subcat_def_cache'] = json.load(f)
        except Exception:
            globals()['subcat_def_cache'] = {}
    return globals()['subcat_def_cache']

def build_category_page(category_name, tools_in_category, all_categories=None):
    """生成单个分类页的完整HTML

    all_categories: {分类名: [工具]} —— 仅用于生成横向互链（相关分类），可为空。
    """
    category_slug = get_category_slug(category_name)
    
    # 加载分类导言（P0-6）
    try:
        intros_path = os.path.join(DATA_DIR, 'category_intros.json')
        if 'category_intros_cache' not in globals():
            with open(intros_path, 'r', encoding='utf-8') as f:
                globals()['category_intros_cache'] = json.load(f)
        category_intros = globals()['category_intros_cache']
    except:
        category_intros = {}
    
    tools_html = ''
    for i, t in enumerate(tools_in_category):
        tools_html += make_tool_card_html(t, i)

    # 子类目导航（仅在当前分类有子类时注入；扁平独立页，非JS tab）
    _subcat_nav_html = ''
    _subdef = get_subcat_def()
    if category_slug in _subdef:
        _sub_links = ''.join(
            f'<a href="/category/{s}/" class="subcat-link" style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;background:#eef2fb;border:1px solid #dde4f3;border-radius:20px;color:#3a5bd9;text-decoration:none;font-size:13px;">{escape_html(sd.get("name",""))}</a>'
            for s, sd in _subdef[category_slug].get('subcats', {}).items()
        )
        if _sub_links:
            _subcat_nav_html = (
                '<div class="subcat-nav" style="margin:14px 0 4px;padding:12px 16px;'
                'background:#f6f8fc;border:1px solid #e6ebf3;border-radius:10px;'
                'font-size:14px;color:#556;">按场景筛选：' + _sub_links + '</div>'
            )

    # 分类页H1：强制带"工具"实体词 + 导言插槽（P0-6）
    _cat_h1 = category_name if category_name.endswith('工具') else category_name + '工具'
    # 分类导言：从 JSON 读取，无则用默认占位
    _cat_intro_data = category_intros.get(category_slug, {})
    _cat_intro_html = ''
    if _cat_intro_data.get('intro'):
        _cat_intro_html += _cat_intro_data['intro']
    if _cat_intro_data.get('how_to_choose'):
        _cat_intro_html += '\n' + _cat_intro_data['how_to_choose']
    if not _cat_intro_html.strip():
        _cat_intro_html = f'<p>{BUILD_YEAR}年最受欢迎的 <strong>{escape_html(category_name)}工具</strong> 合集，共收录 <strong>{len(tools_in_category)}</strong> 款，覆盖免费与付费。下面按评分与热度排序，帮你快速决策。</p>'

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）
    # 原状：CollectionPage 是空壳（无 mainEntity，AI 引擎读不到集合里有哪些工具）、
    #       无 FAQPage、无 speakable、无时效信号、主分类之间零横向互链。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'
    _cat_n = len(tools_in_category)

    try:
        _ranked = sorted(tools_in_category,
                         key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0),
                         reverse=True)
    except Exception:
        _ranked = list(tools_in_category)

    # ItemList：把集合内容显式喂给搜索/AI 引擎（此前完全缺失，是 GEO 最大短板）
    _item_elems = []
    for _i, _t in enumerate(_ranked[:20]):
        _tslug = _t.get('slug', '')
        _el = {
            "@type": "ListItem",
            "position": _i + 1,
            "name": _t.get('name', ''),
            "url": f"{_SITE}/tools/{_tslug}/" if _tslug else f"{_SITE}/category/{category_slug}/",
        }
        _td = (_t.get('description') or '').strip()
        if _td:
            _el["description"] = _td[:120]
        _item_elems.append(_el)

    _top3 = [t.get('name', '') for t in _ranked[:3] if t.get('name')]
    _top3_txt = '、'.join(_top3) if _top3 else '多款主流工具'

    # ── 分类页标题（5118 2026-08-03 核实后重写）──
    # 结论：① "{分类}工具"精确词在百度指数库多为0，真实头部词是裸分类名（AI视频指数1732等）
    #       ② 各分类真实搜索修饰词不同（制作/公文/PDF/logo/助手…），须差异化
    #       ③ 标题内括号=中性标点零排名价值但占2字符预算 → 删；「- AI工具宝箱」无品牌搜索量 → 删
    # 模板：{修饰后主体} {N}款 {BUILD_YEAR}，无括号、无品牌后缀
    _CAT_TITLE_BODY = {
        "AI对话": "AI对话机器人工具推荐",        # 机器人是更真实说法
        "AI写作": "AI公文写作工具推荐",          # 公文写作为热子题
        "AI视频": "AI视频制作工具推荐",          # 制作/生成，移动端巨量
        "AI绘画": "AI绘画免费在线工具推荐",      # 免费/在线
        "AI音频": "AI音频工具推荐",              # ≈0需求，裸名即可
        "AI翻译": "AI PDF翻译工具推荐",          # PDF 为热子题
        "AI搜索": "AI搜索工具推荐",              # 裸名为主，SEO优化放描述
        "AI办公": "AI办公工具推荐",              # 需求中规中矩
        "AI设计": "AI设计工具推荐",              # 改宽泛（20:55）：原"AI logo设计"与子类目ai-brand-design抢词，logo词由子类目承接
        "AI开发": "AI应用开发工具推荐",          # 应用开发
        "AI编程": "AI编程助手推荐",              # 助手是主搜索词
        "AI自动化": "AI自动化工具推荐",          # ≈0需求
        "AI效率": "AI效率工具推荐",              # ≈0需求
        "AI智能体": "AI智能体搭建工具推荐",      # 搭建/平台
        "AI行业应用": "AI行业应用工具推荐",      # ≈0需求
        "AI学习": "AI学习教程与入门网站推荐",    # 5118: AI教程指数191为类目内最高
        "AI检测": "AI检测与论文查重工具推荐",    # 5118: 论文查重808为绝对头部
        "AI提示词": "AI提示词工具与提示词库推荐", # 5118: AI提示词88/提示词143
    }
    _fallback_body = f'{category_name}工具推荐'
    # 三要素定制：category_intros.json 可覆盖 title_body（5118 核量词），无则走内置表
    _cat_title_body = (_cat_intro_data.get('title_body') or
                       _CAT_TITLE_BODY.get(category_name, _fallback_body))
    _cat_title = f"{_cat_title_body} {_cat_n}款 {BUILD_YEAR}"

    # FAQ（GEO 核心）：纯文本，页面与 FAQPage schema 共用
    # 三要素定制：category_intros.json 可提供 faq（[问题, 答案] 列表，5118 长尾热词），无则用通用模板
    _cat_faq_custom = _cat_intro_data.get('faq')
    if _cat_faq_custom and isinstance(_cat_faq_custom, list):
        _cat_faq = [tuple(item) for item in _cat_faq_custom if len(item) == 2]
    else:
        _cat_faq = [
            (f"{category_name}工具哪个好用？",
             f"本页收录的 {_cat_n} 款{category_name}工具按用户评分排序，综合评分靠前的是{_top3_txt}。"
             f"具体选哪款取决于你的使用场景和预算，建议先看排在前面的几款的详情页，"
             f"对比功能覆盖、价格模式与上手难度后再决定。"),
            (f"有免费的{category_name}工具吗？",
             f"有。{category_name}分类下同时收录免费与付费工具，常见形式是提供免费额度后再按需订阅。"
             f"每款工具的详情页都标注了价格模式（免费/免费试用/付费），可据此筛选。"),
            (f"怎么挑选适合自己的{category_name}工具？",
             f"三步走：先明确核心需求（要解决什么具体问题），再看工具是否覆盖该场景；"
             f"然后对比价格模式，优先选有免费额度的先试用；最后看实际体验，"
             f"包括中文支持、响应速度和导出格式是否满足要求。"),
            (f"这里收录了多少款{category_name}工具？多久更新？",
             f"当前共收录 {_cat_n} 款{category_name}工具，最后更新于 {_today_iso}。"
             f"工具库每日更新，新工具上线后会同步补充到对应分类。"),
        ]
    _faq_html = ''.join(
        f'<details style="border:1px solid rgba(127,127,127,0.16);border-radius:10px;'
        f'margin-bottom:8px;background:rgba(127,127,127,0.03);">'
        f'<summary style="cursor:pointer;padding:12px 16px;font-weight:600;font-size:14.5px;">'
        f'{escape_html(_q)}</summary>'
        f'<div style="padding:0 16px 14px;font-size:14px;line-height:1.85;color:#475569;">'
        f'<p style="margin:0;">{escape_html(_a)}</p></div></details>\n'
        for _q, _a in _cat_faq
    )
    _faq_section_html = (
        f'<section class="cat-faq" style="margin-top:28px;">'
        f'<h2 style="font-size:20px;font-weight:700;margin:0 0 12px;">'
        f'关于{escape_html(category_name)}工具的常见问题</h2>\n{_faq_html}</section>'
    )

    # 横向互链：主分类之间此前零互链，链接权重只能"子页→枢纽"单向流动
    _related_html = ''
    if all_categories:
        _others = [(c, len(ts)) for c, ts in all_categories.items()
                   if c != category_name and ts]
        _others.sort(key=lambda x: x[1], reverse=True)
        _picked = _others[:8]
        if _picked:
            _pills = ''.join(
                f'<a href="/category/{get_category_slug(_c)}/" '
                f'style="display:inline-block;margin:3px 6px 3px 0;padding:5px 13px;'
                f'background:rgba(58,91,217,0.08);border:1px solid rgba(58,91,217,0.18);'
                f'border-radius:20px;color:#3a5bd9;text-decoration:none;font-size:13px;">'
                f'{escape_html(_c)} <span style="opacity:.6;">{_n}</span></a>'
                for _c, _n in _picked
            )
            _related_html = (
                f'<section class="related-cats" style="margin-top:26px;">'
                f'<h2 style="font-size:18px;font-weight:700;margin:0 0 10px;">浏览其他AI工具分类</h2>'
                f'<div>{_pills}</div>'
                f'<p style="margin-top:10px;font-size:13.5px;">'
                f'<a href="/category/" style="color:#00A64F;">查看全部AI工具分类 →</a></p>'
                f'</section>'
            )

    # 结构化数据：用 json.dumps 生成，避免 f-string 大括号转义出错
    _cat_breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "全部AI工具", "item": f"{_SITE}/tools/"},
            {"@type": "ListItem", "position": 3, "name": category_name,
             "item": f"{_SITE}/category/{category_slug}/"},
        ],
    }
    _cat_collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": _cat_title,
        "description": f"AI工具宝箱收录的 {_cat_n} 款{category_name}工具合集，"
                       f"按评分与热度排序，含免费与付费方案对比。",
        "url": f"{_SITE}/category/{category_slug}/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".category-intro", ".cat-faq h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"{category_name}工具榜单",
            "numberOfItems": _cat_n,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": _item_elems,
        },
    }
    _cat_faq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": _q,
             "acceptedAnswer": {"@type": "Answer", "text": _a}}
            for _q, _a in _cat_faq
        ],
    }
    _cat_bc_json = json.dumps(_cat_breadcrumb_sd, ensure_ascii=False)
    _cat_cp_json = json.dumps(_cat_collection_sd, ensure_ascii=False)
    _cat_fq_json = json.dumps(_cat_faq_sd, ensure_ascii=False)

    # 三要素定制：category_intros.json 可提供 keywords（5118 相关词），无则用内置模板
    _cat_kw_custom = _cat_intro_data.get('keywords')
    if _cat_kw_custom and isinstance(_cat_kw_custom, list):
        _cat_meta_kw = ','.join(_cat_kw_custom)
    else:
        _cat_meta_kw = (f'{category_name},{category_name}工具,{category_name}软件,免费{category_name},'
                        f'AI工具,{category_name}推荐{BUILD_YEAR},AI导航')

    # 2026-08-13（阶段2.3）：分类页描述过短（Bing 阈值约 110 字符）时用分类导言真实内容补足
    _cat_meta = (f'{BUILD_YEAR}年最新{category_name}工具合集，收录{len(tools_in_category)}款免费及付费'
                 f'{category_name}软件。包含ChatGPT、Claude等主流AI工具，按评分和热度排名，'
                 f'附使用教程、价格与免费额度及对比评测，数据每日更新，帮你找到最适合的{category_name}工具。')
    if len(_cat_meta) < 115 and _cat_intro_html:
        _cat_plain = re.sub(r'<[^>]+>', '', _cat_intro_html)
        _cat_plain = re.sub(r'\s+', '', _cat_plain).strip(' ：:。.，,；;')
        if _cat_plain:
            _cat_meta = (_cat_meta + '。' + _cat_plain)[:160]

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_cat_title)}</title>
    <meta name="description" content="{escape_html(_cat_meta)}">
    <meta name="keywords" content="{escape_html(_cat_meta_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/category/{category_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_cat_title)}">
    <meta property="og:description" content="{escape_html(_cat_meta)}">
    <meta property="og:url" content="https://www.aitoollab.cn/category/{category_slug}/">
    <meta property="og:image" content="https://www.aitoollab.cn/images/og/category-{category_slug}-og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_cat_title)}">
    <meta name="twitter:description" content="{escape_html(_cat_meta)}">
    <meta name="twitter:image" content="https://www.aitoollab.cn/images/og/category-{category_slug}-og.png">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_cat_bc_json}</script>
    <script type="application/ld+json">{_cat_cp_json}</script>
    <script type="application/ld+json">{_cat_fq_json}</script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/tools/">全部AI工具</a> &gt; <span>{escape_html(category_name)}</span>
    </nav>

    <main class="container">
        <section class="section">
            <div class="section-header">
                <h1>{escape_html(_cat_h1)}</h1>
            </div>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                <strong>{escape_html(category_name)}工具是什么？</strong> {escape_html(category_name)}工具指借助大模型与生成式AI完成各类任务的软件服务，本站按用户评分与热度收录 <strong>{_cat_n}</strong> 款，综合评分靠前的有 <strong>{_top3_txt}</strong>，多数提供免费额度，可对比功能与价格后选用。
            </div>
            <div class="category-intro">
{_cat_intro_html}
            </div>
            {_subcat_nav_html}
            <div class="tools-grid">
{tools_html}
            </div>
{_faq_section_html}
{_related_html}
            <p style="margin-top:18px;font-size:12.5px;color:#94a3b8;">本页最后更新：{_today_iso} · 工具库每日更新</p>
        </section>
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_subcategory_page(parent_slug, parent_name, subcat_slug, subcat_data, tools_in_subcat, parent_count=0):
    """生成子类目独立页（独立SEO入口，扁平URL：/category/{subcat_slug}/）"""
    subcat_name = subcat_data.get('name', '')
    _h1 = subcat_name if subcat_name.endswith('工具') else subcat_name + '工具'

    _intro = subcat_data.get('intro', '')
    _how = subcat_data.get('how_to_choose', '')
    _intro_html = (_intro + ('\n' + _how if _how else '')) or \
        f'<p>{BUILD_YEAR}年最新的 <strong>{escape_html(subcat_name)}工具</strong> 合集，共收录 <strong>{len(tools_in_subcat)}</strong> 款，按评分与热度排序，帮你快速决策。</p>'

    # 子类页顶部导航：返回类目根 + 按场景切换（修复"跳转后丢失场景筛选/无法返回根"问题）
    _subcat_nav_html = ''
    _subdef = get_subcat_def()
    if parent_slug in _subdef:
        _sibs = _subdef[parent_slug].get('subcats', {})
        if _sibs:
            _pills = ''
            for _s, _sd in _sibs.items():
                _nm = escape_html(_sd.get('name', ''))
                if _s == subcat_slug:
                    _pills += (f'<a href="/category/{_s}/" class="subcat-link" '
                               f'style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;'
                               f'background:#00A64F;border:1px solid #00A64F;border-radius:20px;'
                               f'color:#fff;text-decoration:none;font-size:13px;font-weight:600;">{_nm} ✓</a>')
                else:
                    _pills += (f'<a href="/category/{_s}/" class="subcat-link" '
                               f'style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;'
                               f'background:#eef2fb;border:1px solid #dde4f3;border-radius:20px;'
                               f'color:#3a5bd9;text-decoration:none;font-size:13px;">{_nm}</a>')
            _back = (f'<a href="/category/{parent_slug}/" class="subcat-back" '
                     f'style="display:inline-block;margin-bottom:8px;font-weight:600;color:#00A64F;'
                     f'text-decoration:none;font-size:14px;">'
                     f'← 返回{parent_name}' + (f'（共{parent_count}款）' if parent_count else '') + '</a>')
            _subcat_nav_html = (
                '<div class="subcat-nav" style="margin:14px 0 4px;padding:12px 16px;'
                'background:#f6f8fc;border:1px solid #e6ebf3;border-radius:10px;'
                'font-size:14px;color:#556;">' + _back +
                '<div style="margin-top:8px;">按场景筛选：' + _pills + '</div></div>'
            )

    tools_html = ''.join(make_tool_card_html(t, i) for i, t in enumerate(tools_in_subcat))

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）：与主分类页同口径
    # 原状：空壳 CollectionPage（无 mainEntity）、无 FAQPage、无 speakable、
    #       无时效信号、缺 Twitter 卡。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'
    _sub_n = len(tools_in_subcat)

    # ── 子类目标题（5118 Batch3-5 核实：通用大词竞争激烈，走"长尾优先 + 主词保护"策略）──
    # 三个大词子类目（logo设计/视频剪辑软件/UI设计 指数 464/729/351，正面竞争打不过剪映/PR/设计公司）：
    # 标题保留主词建立相关性（保护主关键词），同时用竞争小的 AI 长尾（免费在线生成/免费/AI剪辑/工具）吃量。
    # 其余子类目走通用模板（无括号无品牌后缀）。
    _SUB_TITLE_OVERRIDE = {
        # ── 3 个金矿（通用大词，长尾优先+主词保护；5118 Batch5）──
        "ai-brand-design": (
            f"AI logo设计工具推荐 免费在线生成 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI logo设计工具合集：收录{_sub_n}款AI logo生成器与免费在线logo设计软件，"
            f"支持AI一键生成品牌logo，按评分与热度排序，帮你快速完成logo设计。"
        ),
        "ai-video-editing": (
            f"AI视频剪辑软件推荐 免费 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI视频剪辑软件合集：收录{_sub_n}款免费AI剪辑工具，"
            f"支持AI视频剪辑、自动字幕、一键成片，替代传统视频剪辑软件，按评分与热度排序。"
        ),
        "ai-ui-design": (
            f"AI UI设计工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI UI设计工具合集：收录{_sub_n}款AI界面设计软件，"
            f"支持UI设计、原型设计、在线协作，帮你快速完成App与网页界面设计，按评分与热度排序。"
        ),
        # ── 4 个命名对齐（真实说法指数 > 站内命名；5118 Batch3/4/5）──
        "ai-customer-service": (
            f"AI智能客服工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI智能客服工具合集：收录{_sub_n}款AI客服机器人、在线客服系统与电商客服软件，"
            f"支持智能应答、自动回复，按评分与热度排序，帮你搭建高效客服体系。"
        ),
        "ai-robot": (
            f"AI聊天机器人工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI聊天机器人工具合集：收录{_sub_n}款聊天机器人、外呼/电话/语音机器人软件，"
            f"支持多轮对话与自动化外呼，按评分与热度排序，适用于客服与营销场景。"
        ),
        "ai-image-editing": (
            f"AI修图工具推荐 免费在线 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI修图工具合集：收录{_sub_n}款免费在线AI图片处理软件，"
            f"支持一键修图、老照片修复、人像美化、图片编辑，按评分与热度排序，帮你快速完成图片处理。"
        ),
        "ai-security": (
            f"AI检测工具推荐 AIGC检测 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI检测工具合集：收录{_sub_n}款AIGC检测、AI率检测软件，"
            f"支持论文查重、内容真伪识别与免费AIGC检测，按评分与热度排序，帮你判断内容是否由AI生成。"
        ),
        # ── 6 个中机会（真实长尾词有量；5118 Batch5）──
        "ai-seo": (
            f"AI SEO工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI SEO工具合集：收录{_sub_n}款AI搜索引擎优化软件，"
            f"支持关键词分析、排名查询、SEO综合查询与百度SEO优化，按评分与热度排序，帮你提升网站流量。"
        ),
        "ai-grammar": (
            f"AI语法检查工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI语法检查工具合集：收录{_sub_n}款英语语法检查、AI润色与写作校对软件，"
            f"支持在线检查语法错误与润色改写，按评分与热度排序，帮你写出地道的英文。"
        ),
        "ai-marketing-copy": (
            f"AI文案工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI文案工具合集：收录{_sub_n}款AI文案生成器与营销文案软件，"
            f"支持小红书文案、广告文案、标题生成，按评分与热度排序，帮你快速产出爆款文案。"
        ),
        "ai-content-writing": (
            f"AI写作助手工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI写作助手合集：收录{_sub_n}款智能写作工具，"
            f"支持文章生成、续写、改写与润色，按评分与热度排序，帮你高效完成内容创作，从短文案到长文输出都适用。"
        ),
        "ai-finance": (
            f"AI炒股工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI炒股与金融工具合集：收录{_sub_n}款AI理财、量化分析与智能投顾软件，"
            f"支持行情分析、AI选股，按评分与热度排序，助你理性投资。"
        ),
        "ai-recruitment": (
            f"AI面试工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI面试工具合集：收录{_sub_n}款AI面试官、模拟面试与智能招聘软件，"
            f"支持AI面试题库、人才筛选，按评分与热度排序，帮你高效完成招聘。"
        ),
        # ── 6 个有量子类目（标题织入真实词；5118 Batch4/5）──
        "ai-legal": (
            f"法律AI工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年法律AI工具合集：收录{_sub_n}款AI法律助手、法律大模型与法律文书软件，"
            f"支持合同审查、法律咨询，按评分与热度排序，助你快速处理法律事务。"
        ),
        "ai-medical": (
            f"AI医疗工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI医疗工具合集：收录{_sub_n}款医疗AI与医学大模型软件，"
            f"支持辅助诊断、健康咨询，按评分与热度排序，助你了解医疗AI应用，从辅助诊断到健康咨询全面覆盖。"
        ),
        "ai-education": (
            f"AI教育工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI教育工具合集：收录{_sub_n}款AI学习与智能教育软件，"
            f"支持AI教学、学习辅导、教育机器人，按评分与热度排序，帮你提升学习效率。"
        ),
        "ai-video-generation": (
            f"AI视频生成工具推荐 免费 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI视频生成工具合集：收录{_sub_n}款免费文生视频与AI视频生成软件，"
            f"支持文本生成视频、数字人播报，按评分与热度排序，帮你快速制作视频。"
        ),
        "ai-digital-human": (
            f"AI数字人工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI数字人工具合集：收录{_sub_n}款虚拟数字人制作软件，"
            f"支持数字人直播、带货、客服与播报，按评分与热度排序，帮你打造专属数字分身。"
        ),
        "ai-graphic-design": (
            f"AI平面设计工具推荐 {_sub_n}款 {BUILD_YEAR}",
            f"{BUILD_YEAR}年AI平面设计工具合集：收录{_sub_n}款AI设计软件与在线海报工具，"
            f"支持海报设计、平面排版、电商素材，按评分与热度排序，帮你快速完成视觉设计。"
        ),
    }
    # geo-answer 实体词：优先用定制主词（与标题一致），无定制时用站内名
    # 例：标题"AI修图工具推荐" → geo-answer 应为"AI修图工具是什么？"而非"AI图像处理工具是什么？"
    _SUB_GEO_NAME = {
        "ai-brand-design": "AI logo设计",
        "ai-video-editing": "AI视频剪辑",
        "ai-ui-design": "AI UI设计",
        "ai-customer-service": "AI智能客服",
        "ai-robot": "AI聊天机器人",
        "ai-image-editing": "AI修图",
        "ai-security": "AI检测",
        "ai-seo": "AI SEO",
        "ai-grammar": "AI语法检查",
        "ai-marketing-copy": "AI文案",
        "ai-content-writing": "AI写作助手",
        "ai-finance": "AI炒股",
        "ai-recruitment": "AI面试",
        "ai-legal": "法律AI",
        "ai-medical": "AI医疗",
        "ai-education": "AI教育",
        "ai-video-generation": "AI视频生成",
        "ai-digital-human": "AI数字人",
        "ai-graphic-design": "AI平面设计",
    }
    _sub_geo_name = _SUB_GEO_NAME.get(subcat_slug, escape_html(subcat_name))

    _sub_override = _SUB_TITLE_OVERRIDE.get(subcat_slug)
    if _sub_override:
        _sub_title, _sub_desc = _sub_override
    else:
        _sub_title = f"{_sub_n}款{escape_html(subcat_name)}工具推荐 {BUILD_YEAR}"
        _sub_desc = (f"{BUILD_YEAR}年最新{escape_html(subcat_name)}工具合集，"
                     f"收录{_sub_n}款免费及付费{escape_html(subcat_name)}软件。"
                     f"按评分和热度排名，附使用教程和对比评测，"
                     f"帮你找到最适合的{escape_html(subcat_name)}工具。")
    # 2026-08-06：子类目描述统一补全（部分 override 模板偏短，消除 Bing 过短警告）
    if len(_sub_desc) < 110:
        _sub_desc = _sub_desc.rstrip('。') + ("。附价格、免费额度与真实测评，覆盖主流及国产AI工具，"
                                              "帮你快速对比选型，找到最合适的工具。")

    try:
        _sranked = sorted(tools_in_subcat,
                          key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0),
                          reverse=True)
    except Exception:
        _sranked = list(tools_in_subcat)

    _sub_items = []
    for _i, _t in enumerate(_sranked[:20]):
        _tslug = _t.get('slug', '')
        _el = {
            "@type": "ListItem",
            "position": _i + 1,
            "name": _t.get('name', ''),
            "url": f"{_SITE}/tools/{_tslug}/" if _tslug else f"{_SITE}/category/{subcat_slug}/",
        }
        _td = (_t.get('description') or '').strip()
        if _td:
            _el["description"] = _td[:120]
        _sub_items.append(_el)

    _sub_top3 = [t.get('name', '') for t in _sranked[:3] if t.get('name')]
    _sub_top3_txt = '、'.join(_sub_top3) if _sub_top3 else '多款主流工具'

    _sub_faq = [
        (f"{subcat_name}工具哪个好用？",
         f"本页收录 {_sub_n} 款{subcat_name}工具，按用户评分排序，靠前的是{_sub_top3_txt}。"
         f"建议结合具体使用场景和预算，对比前几款的功能覆盖与价格模式后再决定。"),
        (f"{subcat_name}和{parent_name}有什么区别？",
         f"{subcat_name}是{parent_name}下的细分场景。{parent_name}覆盖面更广"
         f"（共 {parent_count} 款工具），而{subcat_name}只聚焦这一具体用途，"
         f"筛选结果更精准。如果需求比较宽泛，可以回到{parent_name}分类浏览全部工具。"),
        (f"这里收录了多少款{subcat_name}工具？多久更新？",
         f"当前共 {_sub_n} 款，最后更新于 {_today_iso}。工具库每日更新，"
         f"新工具上线后会同步归入对应细分场景。"),
    ]
    _sub_faq_html = ''.join(
        f'<details style="border:1px solid rgba(127,127,127,0.16);border-radius:10px;'
        f'margin-bottom:8px;background:rgba(127,127,127,0.03);">'
        f'<summary style="cursor:pointer;padding:12px 16px;font-weight:600;font-size:14.5px;">'
        f'{escape_html(_q)}</summary>'
        f'<div style="padding:0 16px 14px;font-size:14px;line-height:1.85;color:#475569;">'
        f'<p style="margin:0;">{escape_html(_a)}</p></div></details>\n'
        for _q, _a in _sub_faq
    )
    _sub_faq_section = (
        f'<section class="cat-faq" style="margin-top:28px;">'
        f'<h2 style="font-size:20px;font-weight:700;margin:0 0 12px;">'
        f'关于{escape_html(subcat_name)}工具的常见问题</h2>\n{_sub_faq_html}</section>'
    )

    _sub_bc_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具分类", "item": f"{_SITE}/category/"},
            {"@type": "ListItem", "position": 3, "name": parent_name,
             "item": f"{_SITE}/category/{parent_slug}/"},
            {"@type": "ListItem", "position": 4, "name": subcat_name,
             "item": f"{_SITE}/category/{subcat_slug}/"},
        ],
    }
    _sub_cp_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{_sub_n}款{subcat_name}工具推荐{BUILD_YEAR}",
        "description": f"AI工具宝箱收录的 {_sub_n} 款{subcat_name}工具合集，"
                       f"隶属{parent_name}分类，按评分与热度排序。",
        "url": f"{_SITE}/category/{subcat_slug}/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".category-intro", ".cat-faq h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"{subcat_name}工具榜单",
            "numberOfItems": _sub_n,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": _sub_items,
        },
    }
    _sub_fq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": _q,
             "acceptedAnswer": {"@type": "Answer", "text": _a}}
            for _q, _a in _sub_faq
        ],
    }
    _sub_bc_json = json.dumps(_sub_bc_sd, ensure_ascii=False)
    _sub_cp_json = json.dumps(_sub_cp_sd, ensure_ascii=False)
    _sub_fq_json = json.dumps(_sub_fq_sd, ensure_ascii=False)

    # 三要素定制：subcategories.json 子类目可提供 keywords，无则用内置模板
    _sub_kw_custom = subcat_data.get('keywords')
    if _sub_kw_custom and isinstance(_sub_kw_custom, list):
        _sub_meta_kw = ','.join(_sub_kw_custom)
    else:
        _sub_meta_kw = (f'{subcat_name},{subcat_name}工具,{subcat_name}软件,免费{subcat_name},'
                        f'AI工具,{subcat_name}推荐{BUILD_YEAR},AI导航')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_sub_title)}</title>
    <meta name="description" content="{escape_html(_sub_desc)}">
    <meta name="keywords" content="{escape_html(_sub_meta_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/category/{subcat_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_sub_title)}">
    <meta property="og:description" content="{escape_html(_sub_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/category/{subcat_slug}/">
    <meta property="og:image" content="https://www.aitoollab.cn/images/og/category-{subcat_slug}-og.png">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_sub_title)}">
    <meta name="twitter:description" content="{escape_html(_sub_desc)}">
    <meta name="twitter:image" content="https://www.aitoollab.cn/images/og/category-{subcat_slug}-og.png">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_sub_bc_json}</script>
    <script type="application/ld+json">{_sub_cp_json}</script>
    <script type="application/ld+json">{_sub_fq_json}</script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/category/{parent_slug}/">{escape_html(parent_name)}</a> &gt; <span>{escape_html(subcat_name)}</span>
    </nav>

    <main class="container">
        <section class="section">
            <div class="section-header">
                <h1>{escape_html(_h1)}</h1>
            </div>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                <strong>{_sub_geo_name}工具是什么？</strong> {_sub_geo_name}工具指借助大模型与生成式AI完成对应场景任务的软件服务，本站按用户评分与热度收录 <strong>{_sub_n}</strong> 款，综合评分靠前的有 <strong>{_sub_top3_txt}</strong>，多数提供免费额度，可对比功能与价格后选用。
            </div>
            <div class="category-intro">
{_intro_html}
            </div>
            {_subcat_nav_html}
            <div class="tools-grid">
{tools_html}
            </div>
{_sub_faq_section}
            <p style="margin-top:20px;font-size:13.5px;">
                <a href="/category/{parent_slug}/" style="color:#00A64F;">← 返回{escape_html(parent_name)}全部工具</a>
                &nbsp;·&nbsp;
                <a href="/category/" style="color:#00A64F;">查看全部AI工具分类 →</a>
            </p>
            <p style="margin-top:12px;font-size:12.5px;color:#94a3b8;">本页最后更新：{_today_iso} · 工具库每日更新</p>
        </section>
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

# ═══════════════════════════════════════════════════════════════════════════
# 文章 meta description 产出规范（权威定义 / 2026-07-24 定稿）
# 依据：Google Search Central《如何撰写元描述》官方文档 + 像素宽度实测
# 原则：meta description 不是排名因素（Google 官方确认）；Google 全文读取但不保证采用；
#        SERP 按设备像素宽度截断（桌面约 920px → 中文约 70–100 字可见，移动约 40–55 字）。
# 关键事实：
#   - 不堆砌关键词：Google 明确"由长串关键字组成的描述不太可能被显示为摘要"
#   - 每页需独特、准确概括该网页
#   - Google 无长度硬上限，但超出可见窗口的内容用户看不到、也不加分
# 产出标准（写入 articles.json 时遵循）：
#   1. 首句（前 ~70–80 字）必须含【钩子 + 核心价值】，独立成句能勾人 —— 用户只看到这一截
#   2. 全文自然写完，不强行压缩、不凑字数
#   3. 仅当全文超过约 150 中文字时，回头精简后半段冗余/铺垫（首句钩子不动）
#   4. 不堆砌关键词、不重复、准确概括该页内容
#   5. 每篇文章 description 唯一
# 注：本 helper 只在字段全空时兜底（正文首段），不截断/改写已有描述（尊重不覆盖原则）。
# ═══════════════════════════════════════════════════════════════════════════
def _get_article_description(article):
    """文章 meta description 兜底链（Fix 1）。
    优先级: description → summary → excerpt → 正文首段(去HTML标签截前100字)。
    仅填补空白字段，不截断/改写已有描述（尊重不覆盖原则）。

    2026-08-06 增强（响应 Bing Webmaster「Meta 描述过短」警告）：
    当已有描述不足 90 字时，追加正文首段真实内容，补足至 120~160 字；
    仍不覆盖已有钩子（保留首句），只是补全信息量。
    """
    import re as _re
    raw = ''
    for _f in ('description', 'summary', 'excerpt'):
        _v = (article.get(_f) or '').strip()
        if _v:
            raw = _v
            break
    if not raw:
        _content = article.get('content', '') or ''
        _plain = _re.sub(r'<[^>]+>', '', _content)
        _plain = _re.sub(r'\s+', '', _plain)
        raw = _plain[:100]
    # 描述过短 → 追加正文首段真实内容补足（保留原钩子）
    # 2026-08-13（阶段2.3）：阈值 90 → 115，覆盖 90~114 字的漏网描述
    if len(raw) < 115:
        _content = article.get('content', '') or ''
        _plain = _re.sub(r'<[^>]+>', '', _content)
        _plain = _re.sub(r'^#{1,6}[^\n]*$', '', _plain, flags=_re.M)  # 去掉 markdown 标题行
        _plain = _re.sub(r'[*_`>|#]', '', _plain)
        _plain = _re.sub(r'\s+', '', _plain).strip('：:。.，,；;')
        if _plain and _plain not in raw:
            _sep = '' if raw.endswith(('。', '！', '？')) else '。'
            raw = (raw + _sep + _plain)[:160]
        elif _plain:
            raw = _plain[:160]
    return raw

def build_article_page(article, all_articles, all_tools=None):
    """生成单个文章页的完整HTML"""
    slug = article['slug']

    # ── 相关工具（通过关键词匹配：标题/描述中提到哪些工具就推哪些）────
    related_tools_html = ''
    related_tools_top_html = ''
    if all_tools:
        article_title = article.get('title', '').lower()
        article_desc = article.get('excerpt', article.get('description', '')).lower()
        article_content = (article.get('content') or article.get('body', '')).lower()
        # 找工具名在文章中出现的工具（只匹配已发布工具，避免未发布工具 404）
        # 2026-08-14：匹配按相关度分三级——标题提到 > 摘要提到 > 正文提到，
        # 保证"最贴切"的工具排最前（正文工具卡只展示前 4 个）。
        # 忽略空格再比对：标题"即梦 AI"也能命中工具名"即梦AI"。
        _norm = lambda s: re.sub(r"\s+", "", s)
        article_title_n = _norm(article_title)
        article_desc_n = _norm(article_desc)
        article_content_n = _norm(article_content)
        matched_tools = []
        for _t in all_tools:
            if not _t.get('published', True):
                continue
            if _norm(_t.get('name', '').lower()) in article_title_n:
                matched_tools.append(_t)
        for _t in all_tools:
            if not _t.get('published', True) or _t in matched_tools:
                continue
            if _norm(_t.get('name', '').lower()) in article_desc_n:
                matched_tools.append(_t)
        for _t in all_tools:
            if not _t.get('published', True) or _t in matched_tools:
                continue
            if _norm(_t.get('name', '').lower()) in article_content_n:
                matched_tools.append(_t)
        # 不够5个则按分类补充（只补充已发布工具）
        if len(matched_tools) < 5:
            article_category = article.get('category', '')
            same_cat_tools = [t for t in all_tools
                             if t.get('category') == article_category
                             and t not in matched_tools
                             and t.get('published', True)]
            for t in same_cat_tools:
                if len(matched_tools) >= 5:
                    break
                matched_tools.append(t)
        # 再不够，取热门工具（只取已发布工具）
        if len(matched_tools) < 5:
            for t in sorted([x for x in all_tools if x.get('published', True)],
                            key=lambda x: x.get('visits', '0'), reverse=True):
                if len(matched_tools) >= 5:
                    break
                if t not in matched_tools:
                    matched_tools.append(t)

        if matched_tools:
            # 2026-08-15：文章页正文内工具卡从"方形居中卡"改为"紧凑横排行条"——
            # 每行 [小图标] 名称 + 分类·免费标签，桌面两列网格/移动端单列，
            # 信息密度高、无大块空白（原 related-card 方形卡 padding:18px 居中留白多）。
            def _rel_tool_row(t, with_free_tag=False):
                _is_free = '免费' in t.get('price', '') or t.get('price', '') == ''
                _tag = '<span class="rel-tag free">免费</span>' if (with_free_tag and _is_free) else ''
                return f'''<a href="/tools/{t['slug']}/" class="rel-tool-row">
                    {tool_icon_html(t, size='sm')}
                    <span class="rel-tool-name">{escape_html(t['name'])}</span>
                    <span class="rel-tool-cat">{escape_html(t.get('category', ''))}{_tag}</span>
                </a>
'''
            cards = ''.join(_rel_tool_row(t) for t in matched_tools[:4])
            # 2026-08-17：朗读守卫——卡在 data-tts 容器内，必须带 tts-skip，
            # 否则 TTS 会从"🔧 相关工具"开始读（check_tts_skip.py 部署门禁强制）
            related_tools_html = f'''<div class="related-tools tts-skip">
            <h3>🔧 相关工具</h3>
            <div class="rel-tool-row-grid">{cards}</div>
        </div>'''
            # 2026-08-18：正文上方工具卡保留，但去掉标题文字"🔧 本文提到的工具"，避免 TTS 朗读也跳过它
            top_cards = ''.join(_rel_tool_row(t, with_free_tag=True) for t in matched_tools[:4])
            related_tools_top_html = f'''<div class="related-tools article-top-tools tts-skip" style="margin:22px 0 26px;">
                <div class="rel-tool-row-grid">{top_cards}</div>
            </div>'''

    # ── 相关文章（v6.9：相关度打分 = 同内容类型 + 标题/标签词重叠 + 时效；2026-08-08 类型替代旧类目）──
    def _rel_score(cand):
        _s = 0
        if article_content_type(cand) == article_content_type(article):
            _s += 60
        _str_tags = lambda tags: [t for t in (tags or []) if isinstance(t, str)]
        _cur = article.get('title', '') + ' ' + ' '.join(_str_tags(article.get('tags')))
        _cand = cand.get('title', '') + ' ' + ' '.join(_str_tags(cand.get('tags')))
        _tok = lambda t: set(re.findall(r'[\u4e00-\u9fff]{4,}|[A-Za-z][A-Za-z0-9.\-]{3,}', t))
        _s += min(len(_tok(_cur) & _tok(_cand)), 8) * 4
        return _s

    def _rel_date(a):
        try:
            return parse_article_date(a.get('date', ''))
        except Exception:
            return ''

    related_html = ''
    _related_pool = [a for a in all_articles if a['slug'] != slug]
    _related_pool.sort(key=lambda a: (_rel_score(a), _rel_date(a)), reverse=True)
    top_related = _related_pool[:4]
    if top_related:
        cards = ''
        for a in top_related:
            cards += f'''<a href="/articles/{a['slug']}/" class="related-card">
                <div style="font-weight:600;margin-bottom:4px;">{escape_html(a['title'])}</div>
                <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
            </a>\n'''
        related_html = f'''<div class="related-tools">
            <h3>📖 相关文章</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # ── 文章页侧边栏 HTML ──
    article_sidebar_tools_html = ''
    if all_tools and matched_tools:
        items = ''
        for t in matched_tools[:5]:
            is_free = '免费' in t.get('price', '') or t.get('price', '') == ''
            tag_html = ' <span class="rel-tag free">免费</span>' if is_free else ''
            items += f'''<li class="rel-tool-item">
                {tool_icon_html(t, size='sm')}
                <a href="/tools/{t['slug']}/">{t['name']}</a>{tag_html}
            </li>'''
        if items:
            article_sidebar_tools_html = f'''<div class="sidebar-card twocol-only">
                <h4>🔧 文中提到的工具</h4>
                {items}
            </div>'''

    article_sidebar_related_html = ''
    if top_related:
        items = ''
        for a in top_related[:4]:
            items += f"<li><a href='/articles/{a['slug']}/'>{escape_html(a['title'][:35])}</a></li>"
        article_sidebar_related_html = f'''<div class="sidebar-card twocol-only">
            <h4>📖 相关文章</h4>
            <ul>{items}</ul>
        </div>'''

    # OG Image（自动生成缺失的OG图片）
    og_image = ensure_og_image(slug, data_obj=article, is_article=True)

    # 信息图（文章内嵌）
    infographic_path = os.path.join(BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(article['title'])} - 数据对比信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(article['title'])} · 核心数据一览</figcaption>
        </figure>'''

    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    article_date = article.get('dateFull') or article.get('date') or today_iso
    # 将中文日期（如"2026年4月4日"）转为ISO格式（2026-04-04）
    if article_date and re.match(r'^\d{4}年\d{1,2}月\d{1,2}日$', article_date):
        m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', article_date)
        article_date = f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
    article_date_modified = article.get('dateModified', article_date)
    article_category = article.get('category', '文章')
    article_category_slug = get_category_slug(article_category)

    breadcrumb_article_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoollab.cn/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": article_category,
                "item": f"https://www.aitoollab.cn/category/{article_category_slug}/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article['title'],
                "item": f"https://www.aitoollab.cn/articles/{slug}/"
            }
        ]
    }
    breadcrumb_article_json = json.dumps(breadcrumb_article_data, ensure_ascii=False, indent=2)

    # 计算 wordCount（中文字符+英文单词）
    _content_for_wc = (article.get('content') or article.get('body', ''))
    import re as _re_wc
    _chinese_chars = len(_re_wc.findall(r'[\u4e00-\u9fff]', _content_for_wc))
    _english_words = len(_re_wc.findall(r'[a-zA-Z]+', _content_for_wc))
    word_count = _chinese_chars + _english_words

    # 构建增强版 Article Schema
    _article_image_url = og_image if og_image else "https://www.aitoollab.cn/images/logo.png"
    article_schema_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article['title'],
        "description": _get_article_description(article),
        "datePublished": article_date,
        "dateModified": article_date_modified,
        "inLanguage": "zh-CN",
        "author": {
            "@type": "Organization",
            "name": "AI工具宝箱编辑组",
            "url": "https://www.aitoollab.cn/author/",
            "description": "专注 AI 工具实测与对比研究的独立编辑团队，持续追踪并实测主流 AI 工具",
            "knowsAbout": ["AI工具评测", "AI模型对比", "AEO内容优化", "GEO生成式引擎优化", "AI编程工具", "AI对话模型"]
        },
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoollab.cn/images/logo.png",
                "width": 200,
                "height": 60
            },
            "foundingDate": "2026-03-21",
            "slogan": "实测数据驱动 AI 工具决策",
            "publishingPrinciples": "https://www.aitoollab.cn/about.html",
            "sameAs": ["https://github.com/yiweichen10/ai-toolbox"]
        },
        "image": {
            "@type": "ImageObject",
            "url": _article_image_url,
            "width": 1200,
            "height": 630
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://www.aitoollab.cn/articles/{slug}/"
        },
        "abstract": _get_article_description(article),
        "wordCount": word_count,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".article-body h2", ".article-body h3"]
        },
        "about": {
            "@type": "Thing",
            "name": article.get('category', 'AI工具'),
            "description": _get_article_description(article)[:120]
        }
    }

    # 文章页 FAQ Schema（多策略提取Q&A，覆盖各种FAQ写作格式）
    faq_article_schema = ''
    _article_faq_list = []

    # 策略1: Q/A标记匹配（支持 **Q1：**/Q：/### Q1： 等，A前缀可选）
    _faq_raw = _re_wc.findall(
        r'(?:^|\n)[*#]*\s*\*{0,2}[Qq]\d*[：:]\s*([^\n]+?)\s*\*{0,2}\n(?:\*{0,2}[Aa]\d*[：:]\s*)?(.+?)(?=\n[*#]*\s*\*{0,2}[Qq]\d*[：:]|\n## |\Z)',
        _content_for_wc, re.DOTALL
    )

    # 策略2: FAQ段中 **加粗问题？** 后跟答案（无Q前缀）
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'\*\*([^*\n]{6,100}[？?])\*\*\s*\n\s*(.+?)(?=\n\*\*[^*\n]{6,100}[？?]\*\*|\n## |\Z)',
                _faq_section, re.DOTALL
            )

    # 策略3: FAQ段中 ### 问题？ 后跟答案（无Q前缀）
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'###\s*([^\n]{6,100}[？?])\s*\n\s*(.+?)(?=\n###\s*[^\n]{6,100}[？?]|\n## |\Z)',
                _faq_section, re.DOTALL
            )

    # 策略4: FAQ段中 HTML格式 <h3>问题</h3><p>答案</p>
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'<h[34][^>]*>\s*(?:[Qq]\d*[：:]\s*)?([^<]+?)\s*</h[34]>\s*<p>(.+?)</p>',
                _faq_section, re.DOTALL
            )

    # 策略5: FAQ段中 HTML格式 <strong>Q：问题</strong><br>A：答案
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'<strong>\s*[Qq]\d*[：:]\s*([^<]+?)\s*</strong>\s*(?:<br\s*/?>)?\s*[Aa]\d*[：:]\s*(.+?)(?=<strong>\s*[Qq]\d*[：:]|</p>|\Z)',
                _faq_section, re.DOTALL
            )

    if _faq_raw:
        for _q, _a in _faq_raw:
            _q = _q.strip()
            _a = _a.strip()
            # 清理Markdown和HTML格式符号
            _q_clean = _re_wc.sub(r'\*\*', '', _q).strip()
            _q_clean = _re_wc.sub(r'<[^>]+>', '', _q_clean).strip()
            _a_clean = _re_wc.sub(r'\*\*', '', _a).strip()
            _a_clean = _re_wc.sub(r'<[^>]+>', '', _a_clean).strip()
            if _q_clean and _a_clean:
                _article_faq_list.append({
                    "@type": "Question",
                    "name": _q_clean,
                    "acceptedAnswer": {"@type": "Answer", "text": _a_clean}
                })

    # 方式2：如果没提取到，使用 article.faq 字段
    if not _article_faq_list and article.get('faq'):
        for f_item in article['faq']:
            _q = f_item.get('question') or f_item.get('q') or ''
            _a = f_item.get('answer') or f_item.get('a') or ''
            if _q.strip() and _a.strip():
                _article_faq_list.append({
                    "@type": "Question",
                    "name": _q,
                    "acceptedAnswer": {"@type": "Answer", "text": _a}
                })
    if _article_faq_list:
        faq_article_schema = f'\n    <script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":_article_faq_list}, ensure_ascii=False)}</script>'

        # GEO 增强: 注入 Dataset 和 citations

    # ── 文章页可见 FAQ 区块（2026-08-19）：faq 字段 → 模板 faq-section 渲染，兼容 q/a 与 question/answer ──
    # 正文已自带「常见问题」小节的旧文章不重复渲染（避免双 FAQ）；无 faq 字段的文章不渲染。
    article_faq_section_html = ''
    _article_body_raw = article.get('content') or article.get('body', '')
    if article.get('faq') and '常见问题' not in _article_body_raw:
        _visible_faq_items = []
        for _f_item in article['faq']:
            _fq = (_f_item.get('question') or _f_item.get('q') or '').strip()
            _fa = (_f_item.get('answer') or _f_item.get('a') or '').strip()
            if _fq and _fa:
                _visible_faq_items.append((_fq, _fa))
        if _visible_faq_items:
            _faq_items_html = ''.join(
                f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>'
                for q, a in _visible_faq_items
            )
            article_faq_section_html = (
                f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{_faq_items_html}</div>'
            )

    _text_lower = article.get('content', '').lower()
    
    import re as _re_cit
    if _re_cit.search(r'\[\d+\]', _text_lower) or '引用' in _text_lower:
        article_schema_data['citation'] = article_schema_data.get('citation', [])
        article_schema_data['citation'].append({
            "@type": "CreativeWork",
            "name": "参考与实测来源"
        })

    if '<table>' in _text_lower or '评测' in _text_lower or '对比' in _text_lower:
        if '@graph' not in article_schema_data:
            _self_copy = article_schema_data.copy()
            _self_copy.pop('@graph', None)
            article_schema_data.clear()
            article_schema_data['@context'] = "https://schema.org"
            article_schema_data['@graph'] = [_self_copy]
        
        article_schema_data['@graph'].append({
            "@type": "Dataset",
            "name": f"{escape_html(article['title'])} 评测数据集",
            "description": f"本文中包含的AI工具客观评测及对比数据。{escape_html(_get_article_description(article))}",
            "url": f"https://www.aitoollab.cn/articles/{slug}/",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {
                "@type": "Organization",
                "name": "AI工具宝箱编辑组"
            }
        })
        
    structured_data = json.dumps(article_schema_data, ensure_ascii=False, indent=2)

    # D型文章（操作指南类）自动生成 HowTo Schema
    howto_schema_json = ''
    d_type_keywords = ['指南', '教程', '使用方法', '怎么用', '如何使用', '步骤', '操作', '入门', '上手', '玩法', '如何注册', '如何用']
    is_d_type = any(kw in article.get('title', '') for kw in d_type_keywords)
    if is_d_type:
        content_raw = article.get('content') or article.get('body', '')
        # 提取步骤：支持三种格式
        # 1. Markdown h2: ## 标题
        h2_steps = re.findall(r'^## (.+)$', content_raw, re.MULTILINE)
        # 2. HTML h2: <h2...>标题</h2>
        if not h2_steps:
            h2_steps = re.findall(r'<h2[^>]*>(.*?)</h2>', content_raw, re.IGNORECASE)
            # 去掉HTML标签
            h2_steps = [re.sub(r'<[^>]+>', '', h).strip() for h in h2_steps]
        # 3. 正文中的"第X步"或"步骤X"
        if not h2_steps:
            h2_steps = re.findall(r'第[一二三四五六七八九十\d]+步[：:]\s*(.+?)(?:[。\n]|$)', content_raw)
            if not h2_steps:
                h2_steps = re.findall(r'(第[一二三四五六七八九十\d]+步[：:][^\n。]{2,30})', content_raw)
        # 过滤：只保留包含步骤/操作语义的标题
        step_keywords = ['第', '步', '如何', '怎么', '注册', '安装', '配置', '创建', '部署', '使用', '设置', '登录', '上手', '入门', '操作', '技巧', '方法', '开始', '流程']
        filtered_steps = [h for h in h2_steps if any(sk in h for sk in step_keywords)]
        # 如果过滤后太少（<2步），则用所有非FAQ/总结/避坑的标题
        if len(filtered_steps) < 2:
            skip_keywords = ['FAQ', '总结', '为什么', '常见', '对比', 'vs', '避坑', '前言', '背景']
            filtered_steps = [h for h in h2_steps if not any(sk in h for sk in skip_keywords)]
        if len(filtered_steps) >= 2:
            howto_steps = []
            for i, step_title in enumerate(filtered_steps[:8], 1):  # 最多8步
                howto_steps.append({
                    "@type": "HowToStep",
                    "position": i,
                    "name": step_title,
                    "text": f"按照指南完成：{step_title}"
                })
            howto_schema = {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": article['title'],
                "description": _get_article_description(article),
                "totalTime": "PT30M",
                "step": howto_steps
            }
            howto_schema_json = json.dumps(howto_schema, ensure_ascii=False, indent=2)

    # 渲染文章内容，剥离开头重复的H1标题（模板已有<h1>）
    content_md = article.get('content') or article.get('body', '')
    content_md = re.sub(r'^# .+\n?', '', content_md)
    content_html = markdown_to_html(content_md)
    content_html = inject_internal_links(content_html, article.get('slug', ''))
    # [#404修复] 坏链清理：未发布/不存在工具的链接降级为纯文本
    content_html = clean_broken_tool_links(content_html)
    # [#1] 正文标题降级一级，避免与模板<h1>冲突产生多个H1
    content_html = shift_headings(content_html, up=1)
    # [#10] 信息图标记驱动插入：正文有"信息图"引导语(blockquote)则插其后，否则兜底底部
    if has_infographic:
        _m = re.search(r'<blockquote>[\s\S]*?信息图[\s\S]*?</blockquote>', content_html, re.S)
        if _m:
            content_html = content_html[:_m.end()] + '\n' + infographic_html + content_html[_m.end():]
        else:
            content_html = content_html + '\n' + infographic_html

    # ═══════════════════════════════════════════════════════
    # 自动补全 TOC 锚点：如果 h2/h3 缺 id 或 TOC 项缺 <a href>，自动生成
    # （正文标题经 shift_headings 后为 h3，P0-4 起同时支持 h2/h3）
    # ═══════════════════════════════════════════════════════
    h_tags = re.findall(r'<h([23])(?P<attrs>[^>]*)>(?P<text>.+?)</h\1>', content_html)
    # 过滤掉 TOC 内部的标题（目录/本文导航 等，不需要 id）
    body_hs = [(lvl, attrs, text) for lvl, attrs, text in h_tags
               if not any(skip in text for skip in ['目录', '本文导航', '📑'])]

    # Step 1: 给没有 id 的 body 标题自动生成 id
    needs_fix = [(lvl, attrs, text) for lvl, attrs, text in body_hs if 'id=' not in attrs]
    if needs_fix:
        for i, (lvl, attrs, text) in enumerate(needs_fix):
            # 生成稳定的 id：用标题文本做 slug
            section_id = 'section-' + re.sub(r'[^\w\u4e00-\u9fff]+', '-', text.strip()).strip('-').lower()
            # 如果 id 重复，加序号
            existing_ids = set(re.findall(r'id="([^"]+)"', content_html))
            counter = 1
            base_id = section_id
            while section_id in existing_ids:
                section_id = f'{base_id}-{counter}'
                counter += 1
            old_h = f'<h{lvl}{attrs}>{text}</h{lvl}>'
            new_h = f'<h{lvl}{attrs} id="{section_id}">{text}</h{lvl}>'
            content_html = content_html.replace(old_h, new_h, 1)

    # Step 2: 给没有 <a href> 链接的 TOC <li> 项添加锚点
    def _auto_link_toc(content, toc_match_start, toc_match_end):
        """给 TOC 中无链接的 li 项自动添加 <a href>"""
        toc_block = content[toc_match_start:toc_match_end]
        li_pattern = re.compile(r'<li>\s*(.+?)\s*</li>', re.DOTALL)
        items = li_pattern.findall(toc_block)
        has_links = any('<a ' in item for item in items)
        if has_links:
            return content  # 已有链接，跳过

        # 提取所有 h2 的 id 用于匹配
        h2_id_text = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.+?)</h2>', content)
        if len(h2_id_text) != len(items):
            return content  # 数量对不上，不自动匹配

        for (item_text, (h2_id, _)) in zip(items, h2_id_text):
            old = f'<li>{item_text}</li>'
            new = f'<li><a href="#{h2_id}">{item_text.strip()}</a></li>'
            content = content.replace(old, new, 1)
        return content

    # 查找 table-of-contents div
    toc_div_match = re.search(r'<div class="table-of-contents">.*?</div>', content_html, re.DOTALL)
    toc_html = ''
    if toc_div_match:
        content_html = _auto_link_toc(content_html, toc_div_match.start(), toc_div_match.end())
    else:
        # 查找 "本文导航" 后面的 ol
        nav_match = re.search(r'<h2[^>]*>本文导航</h2>\s*<ol>.*?</ol>', content_html, re.DOTALL)
        if nav_match:
            content_html = _auto_link_toc(content_html, nav_match.start(), nav_match.end())
        else:
            # P0-4（2026-08-09）：正文未自带目录时，自动生成"本文目录"（≥3 节才显示）。
            # 正文标题经 shift_headings 后为 h3（h2 少见），两者都支持。
            _toc_headings = (re.findall(r'<h3[^>]*id="([^"]+)"[^>]*>(.+?)</h3>', content_html)
                             or re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.+?)</h2>', content_html))
            _toc_items = []
            for _hid, _htext in _toc_headings:
                _t = re.sub(r'<[^>]+>', '', _htext).strip()
                if not _t or any(_sk in _t for _sk in ['目录', '本文导航', '常见问题', 'FAQ', '总结', '声明', '来源', '相关工具', '相关文章', '广告']):
                    continue
                _toc_items.append((_hid, _t))
            if len(_toc_items) >= 3:
                _lis = ''.join(f'<li><a href="#{_hid}">{escape_html(_t)}</a></li>' for _hid, _t in _toc_items)
                toc_html = f'''<nav class="article-toc" aria-label="本文目录">
        <div class="article-toc-title">📑 本文目录</div>
        <ol>{_lis}</ol>
    </nav>'''

    # P0-4（2026-08-09）：上一篇 / 下一篇（all_articles 已按日期降序：i-1 更新、i+1 更旧）
    prev_next_html = ''
    if all_articles:
        for _i, _a in enumerate(all_articles):
            if _a.get('slug') == slug:
                _newer = all_articles[_i - 1] if _i > 0 else None
                _older = all_articles[_i + 1] if _i + 1 < len(all_articles) else None
                _pn = ''
                if _older:
                    _pn += f'<a class="apn-prev" href="/articles/{_older["slug"]}/">← 上一篇：{escape_html(_older.get("title", ""))[:28]}</a>'
                else:
                    _pn += '<span></span>'
                if _newer:
                    _pn += f'<a class="apn-next" href="/articles/{_newer["slug"]}/">下一篇：{escape_html(_newer.get("title", ""))[:28]} →</a>'
                else:
                    _pn += '<span></span>'
                prev_next_html = f'<div class="article-prev-next">{_pn}</div>'
                break

    # 文章页 keywords：优先用显式字段，否则从 tags + category 生成
    _article_keywords = article.get('keywords', '')
    if not _article_keywords:
        _tags = article.get('tags') or []
        _kw_parts = list(_tags[:8])
        _kw_parts.append(article.get('category', ''))
        _kw_parts.append('AI工具')
        _kw_parts.append('AI工具宝箱')
        _article_keywords = ', '.join([k for k in _kw_parts if k])

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(article.get('seo_title', '').strip() or article['title'])}</title>
    <meta name="description" content="{escape_html(_get_article_description(article))}">
    <meta name="keywords" content="{escape_html(_article_keywords)}">
    <link rel="canonical" href="https://www.aitoollab.cn/articles/{slug}/">
    <link rel="alternate" type="text/markdown" href="https://www.aitoollab.cn/articles/{slug}/{slug}.md">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(article.get('seo_title', '').strip() or article['title'])}">
    <meta property="og:description" content="{escape_html(_get_article_description(article))}">''' + (f'\n    <meta property="og:image" content="{og_image}">\n    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">\n' if og_image else '') + f'''    <meta property="og:url" content="https://www.aitoollab.cn/articles/{slug}/">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta property="article:published_time" content="{article_date}">
    <meta property="article:modified_time" content="{article_date_modified}">
    <meta property="article:author" content="AI工具宝箱编辑组">
    <meta property="article:section" content="{escape_html(article_category)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(article.get('seo_title', '').strip() or article['title'])}">
    <meta name="twitter:description" content="{escape_html(_get_article_description(article))}">''' + (f'\n    <meta name="twitter:image" content="{og_image}">\n' if og_image else '') + f'''    <style>{CRITICAL_CSS}</style>
    {ARTICLE_EXTRA_CSS}
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_article_json}</script>
    <script type="application/ld+json">{structured_data}</script>''' + (f'\n    <script type="application/ld+json">{howto_schema_json}</script>' if howto_schema_json else '') + f'''{faq_article_schema}
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 已收录 {TOOL_COUNT}+ 工具</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>{escape_html(article.get('category', '文章'))}</span> &gt; <span>{escape_html(article['title'])[:20]}...</span>
    </nav>

    <main class="article-container-wide">
        <div class="content-main">
        <article class="article-body" data-tts>
            <h1 class="article-title">{escape_html(article['title'])}</h1>
            <!-- 2026-08-22 作者卡：对标知乎作者区（头像+昵称+简介+听全文），SEO红线：itemprop=author/Organization 与 time 保留、无 h2/h3、tts-skip -->
            <div class="article-authorbar tts-skip" aria-label="作者信息">
                <div class="author-avatar" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="3" stroke="#fff" stroke-width="1.6"/><path d="M8 8h4v4H8zM13 8h3v3h-3zM8 13h3v3H8zM13 13h3v3h-3z" fill="#fff"/></svg>
                </div>
                <div class="author-info">
                    <div class="author-name">
                        <span itemprop="author" itemscope itemtype="https://schema.org/Organization"><a href="/author/" itemprop="url"><span itemprop="name">AI工具宝箱编辑组</span></a></span>
                        <span class="author-badge">官方评测</span>
                        <span class="author-cat-date"><span class="author-cat">AI资讯</span> <time datetime="{article_date}" itemprop="datePublished">{article_date}</time></span>
                        <span class="author-read">阅读 {max(3, len(article.get('content','')) // 400)} 分钟</span>
                    </div>
                    <div class="author-desc-row">
                        <div class="author-desc">AI 工具实测与对比 · 已收录 580+ 款工具</div>
                        <div class="author-tts-slot" aria-hidden="true"></div>
                    </div>
                    <div class="author-meta-mobile" aria-hidden="true">
                        <span class="author-cat">AI资讯</span> <time datetime="{article_date}">{article_date}</time>
                    </div>
                </div>
            </div>
            <div class="tldr-box" style="background:linear-gradient(135deg,#fff8e6,#ffefb8);border-left:4px solid #f5a623;padding:16px 20px;margin-bottom:24px;border-radius:0 8px 8px 0;font-size:14.5px;line-height:1.7;">
                <strong style="color:#c77d00;font-size:15px;">⚡ TL;DR</strong><br>
                <span style="color:#555;">{escape_html(article.get('excerpt') or article.get('description') or article.get('summary', ''))}</span>
            </div>
            {related_tools_top_html}
            {toc_html}{content_html}
            {article_faq_section_html}
            <div style="margin-top:40px;padding:20px;background:#f8f9fa;border-radius:8px;border-left:4px solid #10a37f;">
                <p style="margin:0 0 8px 0;font-size:14px;color:#555;">
                    <strong>关于作者：</strong>本文由 <a href="/author/" style="color:#10a37f;text-decoration:none;">AI工具宝箱编辑组</a> 撰写，团队持续追踪并实测主流 AI 工具，月均订阅支出 $200+，所有评测基于真实长期使用。
                </p>
                <p style="margin:0;font-size:13px;color:#888;">
                    <strong>数据声明：</strong>本文所有数据均标注来源，可溯源核查。发现错误欢迎通过 <a href="/contact.html" style="color:#4285F4;text-decoration:none;">联系页面</a> 反馈，48 小时内核查修正。
                </p>
            </div>
        </article>

            {prev_next_html}

            <div class="content-related">
                {related_tools_html}
                {related_html}
            </div>

            <div class="mobile-ad-inline">📱 继续阅读 · 猜你喜欢</div>
        </div><!-- /.content-main -->

        <div class="page-sidebar-wrap">
        <aside class="page-sidebar">
            <div class="ad-slot ad-slot-large"></div>
            {article_sidebar_tools_html}
            {article_sidebar_related_html}
        </aside>
        </div>
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def _pagination_html(page_num, total_pages, url_template):
    """生成带数字页码的分页导航（P1-4，2026-08-09）。
    url_template 用 {n} 占位页码，如 '/articles/page/{n}/'。"""
    if total_pages <= 1:
        return '<div class="pagination"><span class="page-info">1 / 1</span></div>'
    def _u(n):
        return url_template.format(n=n)
    html = '<div class="pagination">'
    if page_num > 1:
        html += f'<a href="{_u(page_num - 1)}" class="prev">&larr; 上一页</a>\n'
    window = set(range(max(1, page_num - 2), min(total_pages, page_num + 2) + 1))
    window |= {1, total_pages}
    last = 0
    for n in sorted(window):
        if n - last > 1:
            html += '<span class="page-ellipsis">…</span>\n'
        if n == page_num:
            html += f'<span class="page-num current">{n}</span>\n'
        else:
            html += f'<a class="page-num" href="{_u(n)}">{n}</a>\n'
        last = n
    if page_num < total_pages:
        html += f'<a href="{_u(page_num + 1)}" class="next">下一页 &rarr;</a>\n'
    html += '</div>'
    return html

def build_article_list_pages(articles):
    """生成文章分页列表页（/articles/page/1, page/2...）
    每页 10 篇，并加入 rel=next/prev + canonical"""
    
    ITEMS_PER_PAGE = 10
    total_pages = max(1, (len(articles) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    for page_num in range(1, total_pages + 1):
        start_idx = (page_num - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, len(articles))
        page_articles = articles[start_idx:end_idx]
        
        # 生成当前页文章 HTML
        articles_html = ''
        for i, a in enumerate(page_articles):
            articles_html += f'''                        <article class="article-card" style="animation-delay: {round(i * 0.05, 2)}s;">
                            <h3><a href="/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
                            <div class="article-meta">
                                <span class="date">{a.get('dateFull', a.get('date', ''))}</span>
                                <span class="category">{escape_html(a.get('category', ''))}</span>
                            </div>
                            <p class="summary">{escape_html(a.get('description', '')[:150])}</p>
                        </article>\n'''
        
        # 生成分页导航 HTML（P1-4：带数字页码）
        pagination_html = _pagination_html(page_num, total_pages, '/articles/page/{n}/')
        
        # 生成链接标签（rel next/prev/canonical）
        # 分页 canonical 全部指向第1页 /articles/，避免重复内容
        if page_num == 1:
            link_tags = f'    <link rel="canonical" href="https://www.aitoollab.cn/articles/">\n'
        else:
            link_tags = f'    <link rel="canonical" href="https://www.aitoollab.cn/articles/">\n'
        if page_num > 1:
            link_tags += f'    <link rel="prev" href="https://www.aitoollab.cn/articles/page/{page_num - 1}/">\n'
        if page_num < total_pages:
            link_tags += f'    <link rel="next" href="https://www.aitoollab.cn/articles/page/{page_num + 1}/">\n'

        # robots标签：第2页及以后 noindex,follow
        robots_tag = ''
        if page_num > 1:
            robots_tag = '    <meta name="robots" content="noindex, follow">\n'

        # 构建列表页结构化数据
        _list_og_image = "https://www.aitoollab.cn/images/logo.png"

        # 日期ISO格式化辅助函数
        def _date_to_iso(d):
            """将'2026年5月6日'转为'2026-05-06'"""
            import re as _re_d
            m = _re_d.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
            if m:
                return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
            return str(d)

        # 1) Blog Schema（含author + ISO日期）
        _blog_schema = {
            "@context": "https://schema.org",
            "@type": "Blog",
            "name": "AI工具宝箱 - 最新文章",
            "description": f"AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。",
            "url": f"https://www.aitoollab.cn/articles/page/{page_num}/",
            "author": {"@type": "Person", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/about"},
            "publisher": {
                "@type": "Organization",
                "name": "AI工具宝箱",
                "logo": {"@type": "ImageObject", "url": "https://www.aitoollab.cn/images/logo.png", "width": 200, "height": 60}
            },
            "blogPost": [
                {
                    "@type": "BlogPosting",
                    "headline": a.get('title', ''),
                    "url": f"https://www.aitoollab.cn/articles/{a['slug']}/",
                    "datePublished": _date_to_iso(a.get('dateFull', a.get('date', '')))
                } for a in page_articles
            ]
        }

        # 2) ItemList Schema
        _itemlist_schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"最新文章 - 第{page_num}页",
            "description": "AI工具文章列表",
            "numberOfItems": len(page_articles),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": a.get('title', ''), "url": f"https://www.aitoollab.cn/articles/{a['slug']}/"} for i, a in enumerate(page_articles)
            ]
        }

        # 3) WebPage Schema（含 speakable + abstract）
        _webpage_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": f"AI工具宝箱 - 最新文章 第{page_num}页",
            "description": f"AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。",
            "url": f"https://www.aitoollab.cn/articles/page/{page_num}/",
            "abstract": f"AI工具宝箱文章专栏收录原创AI工具深度评测与对比分析，内容涵盖AI写作、AI绘画、AI编程、AI视频等{CAT_COUNT}大分类。所有评测均基于编辑组实际测试，含真实性能数据、价格对比和适用场景建议，每周持续更新，累计{ART_COUNT}篇。",
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [".articles-page-intro", ".articles-list .article-card:first-child h3", ".articles-list .article-card:first-child .summary"]
            },
            "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": "https://www.aitoollab.cn/"}
        }

        # 4) BreadcrumbList Schema
        _breadcrumb_json = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
                {"@type": "ListItem", "position": 2, "name": "文章列表", "item": "https://www.aitoollab.cn/articles/"}
            ]
        }, ensure_ascii=False)

        _list_schema_json = (json.dumps(_blog_schema, ensure_ascii=False) +
            '</script>\n    <script type="application/ld+json">' +
            json.dumps(_itemlist_schema, ensure_ascii=False) +
            '</script>\n    <script type="application/ld+json">' +
            json.dumps(_webpage_schema, ensure_ascii=False))

        # 生成页面 HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具宝箱 - 最新文章 第{page_num}页</title>
    <meta name="description" content="AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。">
    <meta name="keywords" content="AI工具,AI文章,AI评测,AI教程">
    {robots_tag}{link_tags}    <meta property="og:type" content="blog">
    <meta property="og:title" content="AI工具宝箱 - 最新文章">
    <meta property="og:description" content="AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，数据每日更新，帮你快速找到值得读的AI内容。">
    <meta property="og:url" content="https://www.aitoollab.cn/articles/page/{page_num}/">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:image" content="{_list_og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="AI工具宝箱 - 最新文章">
    <meta name="twitter:description" content="AI工具宝箱最新文章列表：AI工具实测、使用教程、行业快讯与深度对比评测，数据每日更新，帮你快速找到值得读的AI内容。">
    <meta name="twitter:image" content="{_list_og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">
{_list_schema_json}
    </script>
    <script type="application/ld+json">
{_breadcrumb_json}
    </script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 最新资讯</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/articles/page/1/">文章列表</a> &gt; <span>第 {page_num} 页</span>
    </nav>

    <main class="article-container">
        <div class="articles-page-intro">
            <h1 style="margin-bottom:8px;">📝 最新文章</h1>
            <a class="articles-rss-btn" href="/rss.xml" target="_blank" rel="noopener">📡 RSS 订阅</a>
            <p style="font-size:14px;color:#64748b;margin:0;">原创AI工具深度评测与对比，每周更新，累计61篇。</p>
        </div>
        <div class="articles-list">
{articles_html}
        </div>
        
        {pagination_html}
    </main>

    <footer class="footer">
        <p>&#xA9; {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''

        # 创建目录并保存文件
        dir_path = os.path.join(BASE_DIR, 'articles', 'page', str(page_num))
        os.makedirs(dir_path, exist_ok=True)
        _emit(os.path.join(dir_path, 'index.html'), html)
        try:
            import re as _re
            md_text = f"# {target_article.get('title', '')}\n\n" + target_article.get('content', '')
            md_text = _re.sub(r'<[^>]+>', ' ', md_text)
            with open(os.path.join(dir_path, f"{slug}.md"), 'w', encoding='utf-8') as f:
                f.write(md_text)
        except:
            pass

        # 第1页同时输出到 /articles/index.html（文章总入口页）
        if page_num == 1:
            # 修改 canonical 和面包屑指向 /articles/
            entry_html = html.replace(
                'href="https://www.aitoollab.cn/articles/page/1/"',
                'href="https://www.aitoollab.cn/articles/"'
            ).replace(
                'href="/articles/page/1/"',
                'href="/articles/"'
            ).replace(
                '第 1 页',
                '文章总览'
            )
            _emit(os.path.join(BASE_DIR, 'articles', 'index.html'), entry_html)
            print(f'[OK] articles/index.html (文章总入口页)')
        print(f'[OK] articles/page/{page_num}/index.html')
    
    return total_pages

def build_article_category_pages(articles):
    """生成文章内容分类页（2026-08-08，ROADMAP-TODO 第一阶段）：
    /articles/reviews/（AI工具评测）、/articles/tutorials/（AI实战教程）、
    /articles/analysis/（AI行业分析）。
    每页 10 篇、按日期倒序；复用文章列表页样式；第 2 页起 noindex,follow。"""
    ITEMS_PER_PAGE = 10

    def _pdate(d):
        from datetime import datetime
        d = (d or '').strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        try:
            return datetime.strptime('2026/' + d, '%Y/%m/%d')
        except Exception:
            pass
        try:
            return datetime.strptime('2026年' + d, '%Y年%m月%d日')
        except Exception:
            pass
        return datetime.min

    def _iso(d):
        m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
        if m:
            return '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))
        m2 = re.match(r'^(\d{4}-\d{2}-\d{2})', str(d))
        return m2.group(1) if m2 else _dt_build.now().strftime('%Y-%m-%d')

    built = 0
    for cp in ARTICLE_CATEGORY_PAGES:
        cslug = cp['slug']
        ctype = cp['ctype']
        items = [a for a in articles if article_content_type(a) == ctype]
        items.sort(key=lambda a: _pdate(a.get('date', '')), reverse=True)
        total_pages = max(1, (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        _base_url = 'https://www.aitoollab.cn/articles/%s/' % cslug
        _og_image = 'https://www.aitoollab.cn/images/logo.png'

        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, len(items))
            page_items = items[start_idx:end_idx]

            articles_html = ''
            for i, a in enumerate(page_items):
                articles_html += f'''                        <article class="article-card" style="animation-delay: {round(i * 0.05, 2)}s;">
                            <h3><a href="/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
                            <div class="article-meta">
                                <span class="date">{a.get('dateFull', a.get('date', ''))}</span>
                                <span class="category">{escape_html(a.get('category', ''))}</span>
                            </div>
                            <p class="summary">{escape_html(a.get('description', '')[:150])}</p>
                        </article>\n'''

            pagination_html = _pagination_html(page_num, total_pages, f'/articles/{cslug}/page/{{n}}/')

            # canonical 全部指向第 1 页；第 2 页起 noindex + rel next/prev
            link_tags = f'    <link rel="canonical" href="{_base_url}">\n'
            robots_tag = ''
            if page_num > 1:
                robots_tag = '    <meta name="robots" content="noindex, follow">\n'
                link_tags += f'    <link rel="prev" href="{_base_url}page/{page_num - 1}/">\n'
            if page_num < total_pages:
                link_tags += f'    <link rel="next" href="{_base_url}page/{page_num + 1}/">\n'

            _blog_schema = {
                "@context": "https://schema.org",
                "@type": "Blog",
                "name": cp['h1'] + ' - AI工具宝箱',
                "description": cp['description'],
                "url": _base_url + ('page/%d/' % page_num) if page_num > 1 else _base_url,
                "author": {"@type": "Person", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/about"},
                "publisher": {"@type": "Organization", "name": "AI工具宝箱",
                              "logo": {"@type": "ImageObject", "url": _og_image, "width": 200, "height": 60}},
                "blogPost": [
                    {"@type": "BlogPosting", "headline": a.get('title', ''),
                     "url": 'https://www.aitoollab.cn/articles/%s/' % a['slug'],
                     "datePublished": _iso(a.get('dateFull', a.get('date', ''))),
                     "description": (a.get('description') or '')[:200]}
                    for a in page_items
                ],
            }
            _itemlist_schema = {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "name": '%s - 第%d页' % (cp['h1'], page_num),
                "numberOfItems": len(page_items),
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": a.get('title', ''),
                     "url": 'https://www.aitoollab.cn/articles/%s/' % a['slug'],
                     "description": (a.get('description') or '')[:200]}
                    for i, a in enumerate(page_items)
                ],
            }
            _webpage_schema = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": '%s - 第%d页' % (cp['h1'], page_num),
                "description": cp['description'],
                "url": (_base_url + 'page/%d/' % page_num) if page_num > 1 else _base_url,
                "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": "https://www.aitoollab.cn/"},
                "speakable": {
                    "@type": "SpeakableSpecification",
                    "cssSelector": [
                        ".articles-page-intro",
                        ".articles-list .article-card:first-child h3",
                        ".articles-list .article-card:first-child .summary",
                    ],
                },
            }
            _breadcrumb_json = json.dumps({
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
                    {"@type": "ListItem", "position": 2, "name": "文章列表", "item": "https://www.aitoollab.cn/articles/"},
                    {"@type": "ListItem", "position": 3, "name": cp['breadcrumb'], "item": _base_url},
                ],
            }, ensure_ascii=False)

            _list_schema_json = (json.dumps(_blog_schema, ensure_ascii=False) +
                                 '</script>\n    <script type="application/ld+json">' +
                                 json.dumps(_itemlist_schema, ensure_ascii=False) +
                                 '</script>\n    <script type="application/ld+json">' +
                                 json.dumps(_webpage_schema, ensure_ascii=False))

            _page_url = ('%spage/%d/' % (_base_url, page_num)) if page_num > 1 else _base_url
            # 分类栏目互链（SEO/GEO：栏目枢纽页互相指向，2026-08-08）
            _hub_links = ''.join(
                '<a href="/articles/%s/">%s</a>' % (_h['slug'], _h['h1'])
                for _h in ARTICLE_CATEGORY_PAGES if _h['slug'] != cslug)
            _hub_html = ('<div class="articles-cat-hub"><span>更多栏目</span>%s</div>' % _hub_links) if _hub_links else ''
            html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cp['page_title']}{'' if page_num == 1 else ' 第%d页' % page_num}</title>
    <meta name="description" content="{escape_html(cp['description'])}">
    <meta name="keywords" content="{escape_html(cp['keywords'])}">
    {robots_tag}{link_tags}    <meta property="og:type" content="blog">
    <meta property="og:title" content="{cp['h1']} - AI工具宝箱">
    <meta property="og:description" content="{escape_html(cp['description'])}">
    <meta property="og:url" content="{_page_url}">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:image" content="{_og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{cp['h1']} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(cp['description'])}">
    <meta name="twitter:image" content="{_og_image}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <script type="application/ld+json">
{_list_schema_json}
    </script>
    <script type="application/ld+json">
{_breadcrumb_json}
    </script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 最新资讯</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/articles/">文章列表</a> &gt; <span>{cp['breadcrumb']}</span>
    </nav>

    <main class="article-container">
        <div class="articles-page-intro">
            <h1 style="margin-bottom:8px;">{cp['h1']}</h1>
            <a class="articles-rss-btn" href="/rss.xml" target="_blank" rel="noopener">📡 RSS 订阅</a>
            <p style="font-size:14px;color:#64748b;margin:0;">{cp['intro']} 共 {len(items)} 篇。</p>
        </div>
        {_hub_html}
        <div class="articles-list">
{articles_html}
        </div>

        {pagination_html}
    </main>

    <footer class="footer">
        <p>&#xA9; {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + ICP_BEIAN + '''</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''

            if page_num == 1:
                dir_path = os.path.join(BASE_DIR, 'articles', cslug)
                os.makedirs(dir_path, exist_ok=True)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{cslug}/index.html ({len(items)} 篇, {total_pages} 页)')
            else:
                dir_path = os.path.join(BASE_DIR, 'articles', cslug, 'page', str(page_num))
                os.makedirs(dir_path, exist_ok=True)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{cslug}/page/{page_num}/index.html')
        built += 1
    return built

def replace_between_tags(html, start_tag, new_content):
    """通过 div 嵌套深度精确替换标签间内容，避免正则贪婪匹配破坏HTML结构"""
    start_idx = html.find(start_tag)
    if start_idx == -1:
        print(f'[WARN] 未找到标记: {start_tag}')
        return html

    content_start = start_idx + len(start_tag)
    depth = 1
    pos = content_start

    while pos < len(html) and depth > 0:
        next_open = html.find('<div', pos)
        next_close = html.find('</div>', pos)

        if next_close == -1:
            print(f'[WARN] 未找到闭合标签: {start_tag}')
            return html

        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return html[:content_start] + '\n' + new_content + '\n                    </div>' + html[next_close + 6:]
            pos = next_close + 6

    return html

def generate_rss(articles):
    # 生成全站快讯 RSS（/rss.xml），取最新 50 篇文章
    import email.utils
    if not articles:
        return
    items = []
    for a in articles[:50]:
        slug = a.get('slug', '')
        if not slug:
            continue
        title = escape_html(a.get('title', ''))
        link = f'https://www.aitoollab.cn/articles/{slug}/'
        desc = escape_html((a.get('description') or '')[:200])
        d = str(a.get('date', ''))
        try:
            if len(d) == 10 and d[4] == '-' and d[7] == '-':
                pub = email.utils.format_datetime(_dt_build.strptime(d, '%Y-%m-%d'))
            else:
                pub = email.utils.formatdate(usegmt=True)
        except Exception:
            pub = email.utils.formatdate(usegmt=True)
        items.append(
            f'<item><title>{title}</title><link>{link}</link>'
            f'<guid isPermaLink="false">aitoollab-{slug}</guid>'
            f'<pubDate>{pub}</pubDate><description>{desc}</description></item>'
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n<channel>\n'
        '<title>AI工具宝箱 - 快讯与评测</title>\n'
        '<link>https://www.aitoollab.cn/</link>\n'
        '<description>AI工具宝箱：AI 工具实测评测、对比分析与行业快讯</description>\n'
        '<language>zh-cn</language>\n'
        + '\n'.join(items) + '\n</channel>\n</rss>\n'
    )
    with open(os.path.join(BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(rss)
    print(f'[OK] rss.xml ({len(items)} items)')

def build_tools_index_page(tools):
    """生成 /tools/ 全部AI工具大全页（SEO+GEO：全量静态内链 + ItemList/FAQ/speakable 结构化数据）。"""
    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    site = 'https://www.aitoollab.cn'
    n = len(tools)

    # 分类顺序与首页 CATEGORY_ORDER 保持一致，缺失分类排后面
    cat_order = ['AI对话', 'AI写作', 'AI绘画', 'AI编程', 'AI视频', 'AI音频', 'AI办公', 'AI设计',
                 'AI搜索', 'AI翻译', 'AI自动化', 'AI效率', 'AI智能体', 'AI开发', 'AI行业应用',
                 'AI学习', 'AI检测', 'AI提示词']
    by_cat = {}
    for t in tools:
        by_cat.setdefault(t.get('category') or '其他', []).append(t)
    ordered = [c for c in cat_order if c in by_cat] + [c for c in by_cat if c not in cat_order]
    free_n = sum(1 for t in tools if get_price_info(t)[0] == 'free')
    top_cats = '、'.join(ordered[:6])

    _title = f'全部AI工具大全（{n}款）- 免费AI工具导航 | AI工具宝箱'
    _meta_desc = (f'AI工具宝箱收录全部 {n} 款 AI 工具（{BUILD_YEAR}年每日更新），覆盖 AI对话、AI编程、'
                  f'AI视频、AI绘画、AI办公等 {len(ordered)} 大分类，{free_n} 款免费可用，'
                  f'含评分、价格、访问热度与实测评测，助你快速找到合适的 AI 工具。')
    _keywords = (f'AI工具大全,全部AI工具,免费AI工具,AI工具导航,AI工具合集,'
                 f'AI工具列表,AI软件大全,{BUILD_YEAR}')

    # ── 2026 热门工具（综合榜 × 人气飙升榜，slug 缺失自动跳过）──
    hot_slugs = ['deepseek', 'chatgpt', 'kimi', 'qwen-chat', 'doubao', 'jimeng-ai',
                 'kling-ai', 'trae', 'glm-5-2', 'tongyi-wanxiang', 'hailuo-ai',
                 'gemini-deep-research-agent']
    _slug_map = {t.get('slug'): t for t in tools}
    hot_tools = [t for s in hot_slugs if (t := _slug_map.get(s))]

    # ── 分类一句话描述（含长尾变体）──
    cat_intros = {
        'AI对话': 'AI对话 · 聊天机器人 · 对话助手',
        'AI写作': 'AI写作 · 文案生成 · 写作助手',
        'AI绘画': 'AI绘画 · AI画图 · 文生图',
        'AI编程': 'AI编程 · AI写代码 · 编程助手',
        'AI视频': 'AI视频生成 · 文生视频 · 数字人',
        'AI音频': 'AI配音 · 语音合成 · 音乐生成',
        'AI办公': 'AI办公 · AI做PPT · 会议纪要',
        'AI设计': 'AI设计 · AI Logo · 图像处理',
        'AI搜索': 'AI搜索 · 对话式搜索 · 知识问答',
        'AI翻译': 'AI翻译 · 实时翻译 · 文档翻译',
        'AI自动化': 'AI工作流 · RPA · 自动化',
        'AI效率': 'AI效率 · 生产力 · 提效工具',
        'AI智能体': 'AI智能体 · Agent · 智能体平台',
        'AI开发': 'AI开发 · 大模型API · 开发者工具',
        'AI行业应用': '行业AI · 垂直场景 · 企业AI',
        'AI学习': 'AI学习 · 在线课程 · 教育AI',
        'AI检测': 'AI检测 · 降AI率 · 原创检测',
        'AI提示词': 'AI提示词 · Prompt · 提示词库',
    }

    # ── 本周新增（live_data 自动更新，读不到则显示“每日”）──
    week_new = '每日'
    try:
        _live_stats = json.load(open(os.path.join(DATA_DIR, 'live_data.json'), encoding='utf-8'))
        _wn = (_live_stats.get('stats') or {}).get('this_week_new')
        if _wn:
            week_new = str(_wn)
    except Exception:
        pass

    def _row(t):
        """紧凑行式工具条目（分类区与热门区共用）。"""
        slug = t.get('slug', '')
        if not slug:
            return ''
        name = escape_html(t.get('name', ''))
        desc = escape_html((t.get('description') or '').strip())
        if len(desc) > 56:
            desc = desc[:56].rstrip() + '…'
        rn = extract_rating_num(t.get('rating', ''))
        price_cls, price_text = get_price_info(t)
        visits = escape_html(str(t.get('visits', '')))
        icon_html = tool_icon_html(t, size='sm')
        rating_html = f'<span class="rating-inline">★{rn}</span>' if rn else ''
        return f'''                        <a class="tools-index-row" href="/tools/{slug}/">
                            <span class="tools-index-icon">{icon_html}</span>
                            <span class="tools-index-main">
                                <span class="tools-index-name">{name} {rating_html}</span>
                                <span class="tools-index-desc">{desc}</span>
                            </span>
                            <span class="tools-index-meta">
                                <span class="price-pill {price_cls}">{price_text}</span>
                                <span class="tool-like" role="button" tabindex="0" data-slug="{slug}" aria-label="给 {name} 点赞" title="好用，点个赞">👍<b class="tool-like-count">0</b></span>
                                <span class="visits">{visits}</span>
                            </span>
                        </a>\n'''

    # ── 分类区块（紧凑行式，静态内链到每个工具页）──
    sections = ''
    for cat in ordered:
        cat_tools = by_cat[cat]
        cslug = get_category_slug(cat)
        cvar = get_category_color_var(cat)
        free_in_cat = sum(1 for t in cat_tools if get_price_info(t)[0] == 'free')
        rows = ''.join(_row(t) for t in cat_tools)
        _intro = cat_intros.get(cat, '')
        sections += f'''        <section class="home-section cat-section" id="cat-{cslug}" style="--cat-color:{cvar};">
            <div class="section-header">
                <div class="section-header-left">
                    <span class="cat-dot" style="background:{cvar};"></span>
                    <h2>{escape_html(cat)}<span class="cat-badge">{len(cat_tools)} 款</span></h2>
                </div>
                <a class="cat-more-link" href="/category/{cslug}/">查看分类页</a>
            </div>
            <p class="tools-index-cat-desc">{_intro} —— {len(cat_tools)} 款，其中 {free_in_cat} 款免费可用</p>
            <div class="tools-index-grid">
{rows}            </div>
        </section>\n'''

    # ── 分类快捷导航 ──
    chips = ''
    for c in ordered:
        chips += (f'<a class="tools-index-chip" href="#cat-{get_category_slug(c)}">'
                  f'<span class="tools-index-chip-dot" style="background:{get_category_color_var(c)};"></span>'
                  f'{escape_html(c)}<b>{len(by_cat[c])}</b></a>')

    # ── 2026 热门工具区（承接品牌/新品词）──
    hot_rows = ''.join(_row(t) for t in hot_tools)
    hot_section = ''
    if hot_rows:
        hot_section = f'''        <section class="home-section cat-section" id="hot" style="--cat-color:var(--primary);">
            <div class="section-header">
                <div class="section-header-left">
                    <span class="cat-dot" style="background:var(--primary);"></span>
                    <h2>{BUILD_YEAR} 热门 AI 工具<span class="cat-badge">HOT</span></h2>
                </div>
                <a class="cat-more-link" href="/ranking/">查看排行榜</a>
            </div>
            <div class="tools-index-grid">
{hot_rows}            </div>
        </section>\n'''

    # ── GEO 摘要（speakable）──
    geo_answer = (f'<strong>本站共收录 {n} 款 AI 工具</strong>（截至 {today_iso}），覆盖 {len(ordered)} 大分类'
                  f'（{top_cats}等），其中 {free_n} 款提供免费使用。{BUILD_YEAR} 年热度靠前的 '
                  f'DeepSeek V4、ChatGPT 5.6、Kimi 3、GPT Live、Qwen 3.8 Max、Gemini 等均已收录，'
                  f'每款工具标注评分、价格与访问热度，点击工具名称即可进入详情页查看评测与使用建议。')

    # ── FAQ ──
    faqs = [
        ('这里收录了多少款 AI 工具？多久更新一次？',
         f'当前共收录 {n} 款 AI 工具，覆盖 {len(ordered)} 个分类，最后更新于 {today_iso}。'
         f'工具库每日更新，新工具上线后会同步补充到对应分类与首页。'),
        ('最近最火的 AI 工具有哪些？',
         f'根据站内热度与搜索趋势，{BUILD_YEAR} 年 7-8 月关注度靠前的有 DeepSeek V4、ChatGPT 5.6、'
         f'Kimi 3、GPT Live、Qwen 3.8 Max、Gemini 等。本页顶部“{BUILD_YEAR} 热门 AI 工具”区可一键直达对应详情页。'),
        ('有哪些免费好用的 AI 工具？',
         f'本站收录的 {n} 款工具中，{free_n} 款提供免费使用（含“免费额度”模式）。'
         f'点击页首“只看免费”筛选即可快速浏览，或前往免费工具排行榜查看推荐。'),
        ('国内可以直接用的 AI 工具有哪些？',
         '文心一言、豆包、Kimi、DeepSeek、通义千问、腾讯混元等国产 AI 工具均可直接使用，'
         '每款工具的详情页都标注了中文可用性与访问方式。'),
        ('什么是 MCP？哪些 AI 工具支持 MCP？',
         'MCP（Model Context Protocol，模型上下文协议）是让 AI 模型连接外部工具与数据的开放标准。'
         '本站收录了 Chrome DevTools MCP、浏览器 MCP 等开发者工具，可在 AI 开发分类下找到。'),
        ('如何快速找到适合自己的 AI 工具？',
         '先按顶部分类导航定位场景（AI对话、AI编程、AI视频等），再结合评分、价格与访问热度筛选；'
         '每款工具的详情页都包含功能说明、价格模式与编辑评测，可据此对比。'),
        ('这些 AI 工具都是免费的吗？',
         f'不全是。当前 {free_n} 款提供免费使用，其余为付费或“免费额度+订阅”模式；'
         f'每款工具卡片与详情页都标注了价格模式（免费/免费试用/付费）。'),
        ('AI工具宝箱收录工具的标准是什么？',
         '优先收录真实可用、对中文用户友好、有稳定更新与良好口碑的 AI 工具；'
         '所有工具均由编辑团队筛选与评测，收录数据每日校准。'),
    ]
    faq_html = ''
    faq_schema = []
    for q, a in faqs:
        faq_html += f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{escape_html(a)}</div></div>\n'
        faq_schema.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})

    # ── ItemList 结构化数据（全量 name+url，头部按评分/热度带 description）──
    def _score(t):
        try:
            r = float(extract_rating_num(t.get('rating', '')) or 0)
        except Exception:
            r = 0.0
        v = str(t.get('visits', ''))
        try:
            vv = float(v.replace('万', '')) * 10000 if '万' in v else float(v or 0)
        except Exception:
            vv = 0.0
        return (r, vv)
    top25 = {t.get('slug') for t in sorted(tools, key=_score, reverse=True)[:25]}
    item_elems = []
    for i, t in enumerate(tools, 1):
        it = {"@type": "ListItem", "position": i,
              "name": t.get('name', ''),
              "url": f"{site}/tools/{t.get('slug', '')}/"}
        if t.get('slug') in top25 and t.get('description'):
            it['description'] = t['description'][:160]
        item_elems.append(it)

    breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{site}/"},
            {"@type": "ListItem", "position": 2, "name": "全部AI工具", "item": f"{site}/tools/"},
        ],
    }
    collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": _title,
        "description": _meta_desc,
        "url": f"{site}/tools/",
        "inLanguage": "zh-CN",
        "datePublished": today_iso,
        "dateModified": today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{site}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{site}/"},
        "speakable": {"@type": "SpeakableSpecification",
                      "cssSelector": [".geo-answer", ".tools-index-sub"]},
        "mainEntity": {
            "@type": "ItemList",
            "name": "全部AI工具榜单",
            "numberOfItems": n,
            "itemListElement": item_elems,
        },
    }
    faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
    website_sd = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "AI工具宝箱",
        "alternateName": "aitoollab.cn",
        "url": f"{site}/",
        "inLanguage": "zh-CN",
        "description": "收录全部 AI 工具的中文导航与评测平台",
    }
    json_ld = '\n'.join(
        f'    <script type="application/ld+json">{json.dumps(sd, ensure_ascii=False)}</script>'
        for sd in (breadcrumb_sd, collection_sd, faq_sd, website_sd)
    )

    page_css = """
.tools-index-hero .section-header h1{font-size:32px;font-weight:800;letter-spacing:-0.5px;}
.tools-index-sub{font-size:15px;color:var(--text-muted);margin:-6px 0 14px;}
.tools-index-hero,.cat-section,.faq-section{scroll-margin-top:220px !important;}
.geo-stats{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 6px;}
.geo-stat{flex:1;min-width:118px;background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:14px 18px;text-align:center;}
.geo-stat b{display:block;font-size:24px;font-weight:800;color:var(--primary);line-height:1.2;}
.geo-stat span{font-size:12.5px;color:var(--text-muted);}
.tools-index-chips{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:8px;position:sticky;top:185px;z-index:150;background:var(--body-bg);padding:4px 2px 10px;margin:4px -2px 24px;scrollbar-width:none;-webkit-overflow-scrolling:touch;}
@media (max-width:768px){.tools-index-chips{top:158px}}
.tools-index-chips::-webkit-scrollbar{display:none;}
.tools-index-chip{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;font-size:13.5px;font-weight:600;color:var(--text-main);background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-pill);text-decoration:none;transition:var(--transition);flex:0 0 auto;}
.tools-index-chip:hover{border-color:var(--primary);color:var(--primary);box-shadow:var(--shadow-xs);}
.tools-index-chip b{font-size:11px;font-weight:700;background:rgba(0,166,79,0.08);color:var(--primary);padding:1px 7px;border-radius:8px;}
.tools-index-chip-dot{width:8px;height:8px;border-radius:50%;}
.cat-more-link{font-size:13px;font-weight:600;color:var(--primary);text-decoration:none;white-space:nowrap;}
.cat-more-link:hover{text-decoration:underline;}
.tools-index-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
.tools-index-row{display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-md);text-decoration:none;color:inherit;transition:var(--transition);}
.tools-index-row:hover{border-color:var(--primary);box-shadow:var(--shadow-sm);transform:translateY(-1px);}
.tools-index-icon{flex-shrink:0;display:flex;align-items:center;}
.tools-index-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;}
.tools-index-name{font-size:14px;font-weight:700;color:var(--text-main);display:flex;align-items:center;gap:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tools-index-name .rating-inline{margin-left:0;}
.tools-index-desc{font-size:12.5px;color:var(--text-muted);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.tools-index-meta{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.tools-index-meta .visits{flex:none;font-size:12px;color:var(--gray-400,#94a3b8);text-align:right;}
.tools-index-cat-desc{font-size:13px;color:var(--text-muted);margin:-6px 0 14px;}
.tools-filter{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 4px;}
.tools-filter-btn{font-size:13.5px;font-weight:600;padding:8px 18px;border-radius:var(--radius-pill);border:1px solid var(--border-light);background:var(--surface);color:var(--text-muted);cursor:pointer;transition:var(--transition);}
.tools-filter-btn.active{background:var(--primary);border-color:var(--primary);color:#fff;}
.tools-filter-btn:hover{border-color:var(--primary);color:var(--primary);}
.tools-filter-btn.active:hover{color:#fff;}
@media (min-width:1280px){.tools-index-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media (max-width:960px){
  .tools-index-grid{grid-template-columns:1fr;}
  .tools-index-chips{top:98px;padding:6px 2px 10px;margin:4px -2px 22px;}
  .tools-index-hero .section-header h1{font-size:24px;}
}
@media (max-width:640px){.tools-index-meta .visits{display:none;}}
""" + TOOL_LIKE_CSS

    filter_js = """
<script>
(function(){
  var btns = document.querySelectorAll('.tools-filter-btn');
  function apply(mode){
    var rows = document.querySelectorAll('.tools-index-row');
    for (var i = 0; i < rows.length; i++){
      var isFree = rows[i].querySelector('.price-pill.free') !== null;
      rows[i].style.display = (mode === 'free' && !isFree) ? 'none' : '';
    }
    for (var j = 0; j < btns.length; j++){
      var on = btns[j].getAttribute('data-filter') === mode;
      btns[j].classList.toggle('active', on);
      btns[j].setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }
  for (var k = 0; k < btns.length; k++){
    btns[k].addEventListener('click', function(){ apply(this.getAttribute('data-filter')); });
  }
})();
</script>
"""

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_title}</title>
    <meta name="description" content="{_meta_desc}">
    <meta name="keywords" content="{_keywords}">
    <link rel="canonical" href="{site}/tools/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{_title}">
    <meta property="og:description" content="{_meta_desc}">
    <meta property="og:url" content="{site}/tools/">
    <meta property="og:image" content="{site}/images/og/aitoolbox-og.png">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{_title}">
    <meta name="twitter:description" content="{_meta_desc}">
    <meta name="twitter:image" content="{site}/images/og/aitoolbox-og.png">
    <style>{CRITICAL_CSS}</style>
    <style>{page_css}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
<link rel="stylesheet" href="/css/ai-widget.css?v={WIDGET_CSS_VERSION}">
{json_ld}
{BAIDU_TONGJI}
</head>
<body data-page-type="tools">
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>全部AI工具</span>
    </nav>

    <main class="container">
        <section class="section tools-index-hero">
            <div class="section-header">
                <h1>全部AI工具大全</h1>
            </div>
            <p class="tools-index-sub">{n} 款 AI 工具合集 · {len(ordered)} 大分类导航 · {free_n} 款免费可用 · 每日更新推荐</p>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                {geo_answer}
            </div>
            <div class="tools-filter" role="group" aria-label="价格筛选">
                <button type="button" class="tools-filter-btn active" data-filter="all" aria-pressed="true">全部工具</button>
                <button type="button" class="tools-filter-btn" data-filter="free" aria-pressed="false">只看免费</button>
            </div>
            <div class="geo-stats">
                <div class="geo-stat"><b>{n}</b><span>款收录工具</span></div>
                <div class="geo-stat"><b>{len(ordered)}</b><span>大分类</span></div>
                <div class="geo-stat"><b>{free_n}</b><span>款免费可用</span></div>
                <div class="geo-stat"><b>{week_new}</b><span>本周新增</span></div>
            </div>
        </section>

        <nav class="tools-index-chips" aria-label="分类快捷导航">{chips}</nav>

        {hot_section}

        {sections}

        <section class="home-section faq-section" id="faq">
            <div class="section-header">
                <div class="section-header-left"><h2>常见问题</h2></div>
            </div>
            {faq_html}
        </section>

        <div class="ads-slot ads-slot-content-bottom"></div>
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p>
    </footer>
    {BACK_TO_TOP_BLOCK}
    {filter_js}
    <script src="/js/ai-likes.js?v={LIKES_JS_VERSION}" defer></script>
    <script src="/js/ai-assistant.js?v={WIDGET_JS_VERSION}" defer></script>
    <script src="/ads/loader.js" defer></script>
</body>
</html>'''
    return _collapse_blank_lines(html)

def build_index_page(tools, articles):
    # 生成静态首页
    index_html_template = os.path.join(BASE_DIR, 'index.html')
    with open(index_html_template, 'r', encoding='utf-8') as f:
        html = f.read()

    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')

    # 同步 CSS 缓存版本号（index.html 作为模板时保留旧版本，需强制刷新）
    html = re.sub(r'style\.(?:min\.)?css\?v=[^"\'\)]+', f'style.min.css?v={CSS_VERSION}', html)
    # 同步 main.js 缓存版本号（内容哈希，自动生成）
    html = re.sub(r'/js/main\.js\?v=[^"\'\)]+', f'/js/main.js?v={JS_VERSION}', html)
    # 同步挂件脚本缓存版本号（ai-likes.js / ai-assistant.js，nginx 对 /js/ 缓存 30 天）
    html = re.sub(r'/js/ai-likes\.js(?:\?v=[^"\'\)]+)?', f'/js/ai-likes.js?v={LIKES_JS_VERSION}', html)
    html = re.sub(r'/js/ai-assistant\.js(?:\?v=[^"\'\)]+)?', f'/js/ai-assistant.js?v={WIDGET_JS_VERSION}', html)
    # P1-5 首页注入 AI 助手挂件（样式 + 脚本，幂等）
    if 'ai-widget.css' not in html:
        html = html.replace(
            '</head>',
            f'<link rel="stylesheet" href="/css/ai-widget.css?v={WIDGET_CSS_VERSION}">\n</head>',
            1,
        )
    if '/js/ai-assistant.js?v=' not in html:
        html = html.replace(
            '</body>',
            f'<script src="/js/ai-assistant.js?v={WIDGET_JS_VERSION}" defer></script>\n</body>',
            1,
        )

    # v6.9：移除旧版「内容Tab板块」里的 AI实战 页（已由独立 PRACTICE 区块替代，避免重复注入）
    # 幂等：已清理过的模板不再命中。导航按钮 + 实战面板（含其标记块）一并移除。
    html = re.sub(r'\s*<button class="tab-card" data-tab="practice">[\s\S]*?</button>', '', html, count=1)
    html = re.sub(r'\s*<!-- AI实战Tab[\s\S]*?<!-- PRACTICE_ITEMS_END -->\s*</div>', '', html, count=1)

    # ── 分类入口：左侧 sidebar / 移动端 cat-btn 恢复为纯导航 <button> ──
    # 上一版曾把"更多 ›"塞进侧边栏，会遮挡类目名；现改为：sidebar 仅做页内滚动导航，
    # "更多 ›"真实栏目页链接改由右侧类目区块标题（main.js 动态生成的 .cat-more-link）提供。
    # 此处把上一版写入的 <a class="..." href="/category/..."> 规范回 <button>（幂等：已是 button 则不动）。
    def _revert_cat_entry(m):
        cls = m.group(1)            # sidebar-cat / cat-btn
        extra = m.group(2) or ''    # 可能含 ' active'
        cat = m.group(3)
        style = m.group(4)
        label = m.group(5)
        if cat == 'all':
            return m.group(0)
        active = ' active' if 'active' in extra else ''
        style_attr = f' style="{style}"' if style else ''
        return f'<button class="{cls}{active}" data-category="{cat}"{style_attr}>{label}</button>'

    html = re.sub(
        r'<a class="(sidebar-cat|cat-btn)([^"]*)" href="/category/[^"]*/" data-category="([^"]+)"'
        r'(?: style="([^"]*)")?>\s*<span class="sc-label">(.*?)</span>'
        r'\s*<span class="sc-more">[^<]*</span>\s*</a>',
        _revert_cat_entry, html, flags=re.S)

    # 清理上一版遗留的废弃 cat-more-style（侧边栏 sc-more 样式，已不再使用，幂等）
    html = re.sub(r'<style id="cat-more-style">.*?</style>\s*', '', html, flags=re.S)

    # ── 注入右侧类目区块"查看更多"链接样式（首页专用，幂等，避免重复注入）──
    if 'id="home-cat-more-style"' not in html:
        cat_more_css = '''
<style id="home-cat-more-style">
.cat-more-link {
  display: inline-block;
  font-size: 13px; font-weight: 600; color: var(--primary);
  text-decoration: none; white-space: nowrap; flex: none; align-self: center;
  padding: 5px 14px; border-radius: 999px;
  background: rgba(var(--primary-rgb, 99, 102, 241), 0.10);
  border: 1px solid rgba(var(--primary-rgb, 99, 102, 241), 0.22);
  transition: background .15s ease, color .15s ease, border-color .15s ease;
}
.cat-more-link:hover {
  background: rgba(var(--primary-rgb, 99, 102, 241), 0.18);
  border-color: rgba(var(--primary-rgb, 99, 102, 241), 0.35);
  text-decoration: none;
}
.cat-more-link::after { content: ' ›'; font-weight: 700; margin-left: 2px; }
@media (max-width: 640px) {
  .cat-more-link { font-size: 12px; padding: 4px 10px; }
}
</style>
'''
        html = html.replace('</head>', cat_more_css + '\n</head>', 1)

    # ── 注入「热门榜 TOP30」紧凑小网格样式（首页专用，幂等）──
    hot_mini_css = '''
<style id="home-hot-mini-style">
#hotGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px 10px;
}
.hot-mini {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px; border-radius: 12px; text-decoration: none; color: inherit;
  background: rgba(127,127,127,0.06);
  border: 1px solid rgba(127,127,127,0.12);
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.hot-mini:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.10);
  background: rgba(127,127,127,0.10);
}
.hot-mini-logo {
  width: 30px; height: 30px; border-radius: 8px; object-fit: contain;
  background: rgba(255,255,255,0.65); padding: 2px;
}
.hot-mini-logo-fallback {
  width: 30px; height: 30px; border-radius: 8px; flex: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; color: #fff; line-height: 1;
}
.hot-mini-name {
  font-size: 12.5px; font-weight: 600; text-align: center; line-height: 1.2;
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hot-mini-meta { font-size: 11px; color: var(--text-muted, #64748b); }
@media (max-width: 640px) {
  #hotGrid { grid-template-columns: repeat(auto-fill, minmax(98px, 1fr)); gap: 10px 8px; }
  .hot-mini-name { font-size: 12px; }
}
</style>
'''
    # 幂等但允许更新：先移除旧块再注入最新样式（index.html 模板已含旧块会导致幂等跳过）
    html = re.sub(r'<style id="home-hot-mini-style">.*?</style>\s*', '', html, flags=re.S)
    html = html.replace('</head>', hot_mini_css + '\n</head>', 1)

    # ── 工具卡片HTML（委托共享函数）──
    def make_card_html(t, i):
        return make_tool_card_html(t, i)

    # ── 第二区块：热门榜 TOP30 紧凑小网格（按访问量降序，评分作展示）──
    def _parse_visits(v):
        if not v:
            return 0
        s = str(v).strip()
        try:
            if '亿' in s:
                return float(s.replace('亿', '')) * 1e8
            if '万' in s:
                return float(s.replace('万', '')) * 1e4
            return float(s)
        except Exception:
            return 0
    def _parse_rating(r):
        if not r:
            return 0.0
        m = re.search(r'[\d.]+', str(r))
        return float(m.group()) if m else 0.0
    hot_sorted = sorted(
        [t for t in tools if t.get('published', True)],
        key=lambda t: _parse_visits(t.get('visits')),
        reverse=True
    )[:12]
    hot_html = ''
    for t in hot_sorted:
        slug = t.get('slug', '')
        name = (t.get('name') or '').strip()
        name_esc = name.replace('"', '&quot;')
        rating_num = _parse_rating(t.get('rating'))
        visits = (t.get('visits') or '').strip()
        ext, icon = resolve_icon(slug)
        if icon:
            logo_html = ('<img class="hot-mini-logo" src="%s" alt="%s" loading="lazy" '
                         'width="30" height="30" onerror="this.style.visibility=\'hidden\'">' % (icon, name_esc))
        else:
            emoji = escape_html(t.get('emoji') or (name[:1] if name else '?'))
            color = t.get('color', '#4f46e5')
            logo_html = '<div class="hot-mini-logo-fallback" style="background:%s">%s</div>' % (color, emoji)
        hot_html += (
            '<a class="hot-mini" href="/tools/%s/" title="%s">'
            '%s'
            '<span class="hot-mini-name">%s</span>'
            '<span class="hot-mini-meta">★ %.1f · %s</span>'
            '</a>' % (slug, name_esc, logo_html, name, rating_num, visits)
        )
    html = replace_between_tags(html, '<div class="tools-grid" id="hotGrid">', hot_html)
    # 区块标题同步更新为「热门榜 TOP30」
    html = html.replace('热门榜 TOP30<span>HOT 30</span>',
                        '热门榜 TOP12<span>HOT 12</span>')
    html = html.replace('&#x1F525; 热门推荐<span>HOT PICKS</span>',
                        '热门榜 TOP12<span>HOT 12</span>')
    html = html.replace('热门推荐<span>HOT PICKS</span>',
                        '热门榜 TOP12<span>HOT 12</span>')

    def _tool_show_date(t):
        """版块展示用日期: published_date > created_date"""
        return str(t.get('published_date') or t.get('created_date') or '')[:10]

    # ── 第二点五区块：最新发布（按 published_date 降序，created_date 兜底，最多3个）──
    # v6-2 调整: 最近更新区块改为展示「每日新发布」的最新3款工具
    hot_slugs = set(t['slug'] for t in hot_sorted)
    recent_tools = sorted(
        [t for t in tools if _tool_show_date(t)],
        key=lambda t: _tool_show_date(t),
        reverse=True
    )
    # 去重：排除已出现在热门中的工具
    recent_tools = [t for t in recent_tools if t['slug'] not in hot_slugs][:3]
    recent_html = ''
    if recent_tools:
        for t in recent_tools:
            _slug = t.get('slug', '')
            _name = escape_html(t.get('name', ''))
            _cat = escape_html(t.get('category', ''))
            _desc = escape_html((t.get('description') or '')[:70])
            _price = escape_html(str(t.get('price', '免费')))
            _d = _tool_show_date(t)
            try:
                _dp = _d.split('-')
                _date_disp = f'{int(_dp[1]):02d}/{int(_dp[2]):02d}' if len(_dp) == 3 else _d
            except Exception:
                _date_disp = _d
            _, _icon = resolve_icon(_slug)
            if _icon:
                _icon_html = f'<img class="release-logo" src="{_icon}" alt="{_name}" loading="lazy" width="44" height="44">'
            else:
                _icon_html = f'<div class="release-logo release-logo-fallback">{escape_html(t.get("emoji") or _name[:1])}</div>'
            recent_html += (
                f'<a class="release-item" href="/tools/{_slug}/">'
                f'{_icon_html}'
                f'<div class="release-body">'
                f'<div class="release-head"><span class="release-name">{_name}</span><span class="release-date">{_date_disp}</span></div>'
                f'<p class="release-desc">{_desc}</p>'
                f'<div class="release-meta"><span>{_cat}</span><span>{_price}</span></div>'
                f'</div>'
                f'</a>'
            )
    else:
        recent_html = '<p style="color:var(--text-light);padding:20px 0;">暂无最新发布 ~</p>\n'

    html = replace_between_tags(html, '<div class="tools-grid" id="recentGrid">', recent_html)
    # 如果最近更新为空，隐藏recentSection
    if not recent_tools:
        html = html.replace('<section class="home-section recent-section" id="recentSection">',
                            '<section class="home-section recent-section" id="recentSection" style="display:none;">')

    # ── 第三区块：全部工具（首屏8个静态，剩余懒加载） ──
    all_tools_html = ''
    for i, t in enumerate(tools[:8]):
        all_tools_html += make_card_html(t, i)
    html = replace_between_tags(html, '<div class="tools-grid" id="toolsGrid">', all_tools_html)

    # ── AI前沿Tab新闻卡片：从articles.json动态获取最新5篇 ──
    def parse_article_date(d):
        """统一解析多种日期格式，缺省年份补2026"""
        from datetime import datetime
        d = d.strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(d, fmt)
            except:
                continue
        # 只有月/日格式，补2026年（避免Python 3.15 breaking change）
        try:
            dt = datetime.strptime('2026/' + d, '%Y/%m/%d')
            return dt
        except:
            pass
        try:
            dt = datetime.strptime('2026年' + d, '%Y年%m月%d日')
            return dt
        except:
            pass
        return datetime.min
    sorted_articles = sorted(articles, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)
    
    # ── 广告/推广列表（穿插在新闻之间，凤凰网风格）──
    NEWS_ADS = [
        {"title": "2026年免费AI工具大盘点：这12款国产工具零成本上手", "url": "/articles/ai-free-tools-china-2026/"},
        {"title": "Cursor vs Copilot vs Windsurf 2026终极对比：我三家都用了一年", "url": "/articles/cursor-vs-copilot-vs-windsurf-2026/"},
        {"title": "AI数据分析工具实测：我用同一份数据测了5款，免费的通义千问比ChatGPT还快", "url": "/articles/ai-data-analysis-tools-real-test-202606/"},
        {"title": "AI写作工具推荐：从日报周报到万字长文，这6款覆盖你所有场景", "url": "/articles/ai-writing-tools-2026-guide/"},
    ]
    
    news_html = ''
    # 标签统一走 content_type（与「AI实战教程/深度评测」区块同源）。
    # 2026-08-14 修复：旧 tag_names 按 category 映射且漏了「AI工具教程」等分类，
    # 导致教程文章在 AI前沿 里被 fallback 误标成「AI资讯」，与 AI实战教程 区块的「教程」自相矛盾。
    _ct_tag = {'AI教程': '教程', 'AI评测': 'AI评测', 'AI资讯': 'AI资讯', '行业分析': 'AI洞察'}
    for idx, a in enumerate(sorted_articles[:5]):
        d = a.get('date', '')
        # 统一显示为 MM/DD
        display_date = d
        if '-' in d and len(d) == 10:
            parts = d.split('-')
            display_date = f'{int(parts[1]):02d}/{int(parts[2]):02d}'
        elif '/' in d:
            parts = d.split('/')
            if len(parts) == 3:
                display_date = f'{int(parts[0]):02d}/{int(parts[1]):02d}'
        tag = _ct_tag.get(article_content_type(a), 'AI资讯')
        news_html += f'''                                <a class="news-card-item" href="/articles/{a['slug']}/">
                                    <span class="news-card-date">{display_date}</span>
                                    <span class="news-card-title">{escape_html(a['title'])}</span>
                                    <span class="news-card-tag">{tag}</span>
                                </a>
'''
        # 在第2篇新闻后插入1条推广（当前隐藏待启用）
        if idx == 1:
            ad = NEWS_ADS[0]
            news_html += f'''                                <a class="news-card-item news-card-ad" href="{ad['url']}" style="display:none">
                                    <span class="news-card-date">推广</span>
                                    <span class="news-card-title">{ad['title']}</span>
                                    <span class="news-card-tag ad-tag">推荐</span>
                                </a>
'''
    # 替换新闻卡片（保留"更多文章"链接）
    news_re = re.compile(r'<!-- NEWS_CARDS_START -->[\s\S]*?<!-- NEWS_CARDS_END -->')
    html = news_re.sub(f'<!-- NEWS_CARDS_START -->\n{news_html}                                <!-- NEWS_CARDS_END -->', html)

    # ── AI辞典Tab词典卡片：按发布时间倒序取已发布最新8条（2026-08-20 动态化）──
    # 原逻辑 dict_terms[:8] 取数组头 8 条永远固定；现改为 published_date 倒序，
    # 每日发布自动化写入新词条的 published_date 后，首页板块自动轮换。
    # 无日期的基础词条（最早批次）沉底不占首页位，靠 /dict/ 索引页全量入口兜底。
    dict_html = ''
    dict_terms = []
    dict_data_path = os.path.join(DATA_DIR, 'dict_terms.json')
    if os.path.exists(dict_data_path):
        with open(dict_data_path, 'r', encoding='utf-8') as f:
            all_dict = json.load(f)
            dict_terms = [t for t in all_dict if t.get('published', True)]
    dict_terms.sort(key=lambda t: t.get('published_date') or '2000-01-01', reverse=True)
    for idx, term in enumerate(dict_terms[:8]):
        new_badge = '<span class="badge-new">NEW</span>' if idx < 2 else ''
        _pd = (term.get('published_date') or '').strip()
        _pd_display = ''
        if len(_pd) == 10:
            _pp = _pd.split('-')
            try:
                _pd_display = f'{int(_pp[1]):02d}/{int(_pp[2]):02d}'
            except Exception:
                _pd_display = ''
        dict_html += f'''                                <a class="dict-card-item" href="/dict/{term['slug']}/">
                                    <div class="dict-card-icon">{term['emoji']}</div>
                                    <div class="dict-card-body">
                                        <h4>{escape_html(term['term'])} {new_badge}</h4>
                                        <p>{escape_html(term['brief'])}</p>
                                        <span class="dict-card-date">{_pd_display}</span>
                                    </div>
                                </a>
'''
    dict_re = re.compile(r'<!-- DICT_CARDS_START -->[\s\S]*?<!-- DICT_CARDS_END -->')
    html = dict_re.sub(f'<!-- DICT_CARDS_START -->\n{dict_html}                                <!-- DICT_CARDS_END -->', html)

    # ── 编辑实测 · 今日推荐（v6；2026-08-12 修复：日期与内容必须同源）──
    def _fmt_md(d):
        try:
            p = d.split('-')
            if len(p) == 3:
                return f'{int(p[1]):02d}/{int(p[2]):02d}'
        except Exception:
            pass
        return d
    _picks_path = os.path.join(DATA_DIR, 'homepage_picks.json')
    _picks_date = datetime.now().strftime('%Y-%m-%d')

    def _load_picks_file():
        try:
            return json.load(open(_picks_path, encoding='utf-8')) if os.path.exists(_picks_path) else {}
        except Exception:
            return {}

    def _pick_text_corrupt(p):
        # 编码损坏检测：CJK 被 ASCII 化后会出现连续问号（如 PowerShell 管道写坏）或替换符
        for _s in (p.get('reason'), p.get('tag')):
            if isinstance(_s, str) and ('\ufffd' in _s or re.search(r'\?{3,}', _s) is not None):
                return True
        return False

    _pd = _load_picks_file()
    _picks_broken = any(_pick_text_corrupt(p) for p in _pd.get('picks', []))
    # 自动模式：推荐过期或文案编码损坏时，先刷新当日推荐再构建
    # （根因：deploy.sh 曾把候选池生成放在构建之后；其他自动化只跑 build.py 不生成候选池；
    #   2026-08-13 增补：数据被 ASCII 化产生问号时强制重建，避免坏文案上线）
    if _pd.get('auto') and (str(_pd.get('date', '')) != _picks_date or _picks_broken):
        _sub_env = os.environ.copy()
        _sub_env.setdefault('PYTHONIOENCODING', 'utf-8')
        _sub_env.setdefault('PYTHONUTF8', '1')
        _picks_run = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, 'scripts', 'generate_picks_candidates.py')],
            capture_output=True, text=True, encoding='utf-8', env=_sub_env)
        if _picks_run.returncode == 0:
            print(f'[picks] 已刷新为 {_picks_date} 推荐（过期或文案损坏自动重建）')
            _pd = _load_picks_file()
            _picks_broken = any(_pick_text_corrupt(p) for p in _pd.get('picks', []))
        else:
            print(f'[picks] 自动刷新今日推荐失败(exit {_picks_run.returncode})，沿用现有推荐：')
            print((_picks_run.stderr or _picks_run.stdout or '')[-300:])
    _picks = []
    _picks_date = str(_pd.get('date', _picks_date))
    _tool_map = {t['slug']: t for t in tools}
    for _p in _pd.get('picks', []):
        if _pick_text_corrupt(_p):
            print(f"[picks] 跳过编码损坏的推荐条目: {_p.get('slug')}")
            continue
        _t = _tool_map.get(_p.get('slug'))
        if _t:
            _picks.append((_t, str(_p.get('reason', '')), str(_p.get('tag', '编辑实测'))))
    # 兜底：损坏条目被跳过或推荐不足 3 个时，用热门榜补足，保证推荐区不空（2026-08-13）
    if len(_picks) < 3:
        _seen = {_t.get('slug') for _t, _, _ in _picks}
        for _t in hot_sorted:
            if _t.get('slug') in _seen:
                continue
            _picks.append((_t, '热门实测 · 数据驱动选型', '编辑实测'))
            _seen.add(_t.get('slug'))
            if len(_picks) >= 3:
                break
    picks_html = ''
    for _i, (_t, _reason, _tag) in enumerate(_picks):
        _slug = _t.get('slug', '')
        _name = escape_html(_t.get('name', ''))
        _cat = escape_html(_t.get('category', ''))
        _price = escape_html(str(_t.get('price', '免费')))
        _, _icon = resolve_icon(_slug)
        if _icon:
            _icon_html = f'<img src="{_icon}" class="pick-logo" alt="{_name}" loading="lazy" width="48" height="48">'
        else:
            _icon_html = f'<div class="pick-logo pick-logo-fallback">{escape_html(_t.get("emoji") or _name[:1])}</div>'
        picks_html += (
            f'<a class="pick-card" href="/tools/{_slug}/" data-slug="{_slug}">\n'
            f'      {_icon_html}\n'
            f'      <div class="pick-body">\n'
            f'        <div class="pick-head"><span class="pick-name">{_name}</span><span class="pick-tag">{escape_html(_tag)}</span></div>\n'
            f'        <p class="pick-reason">{escape_html(_reason)}</p>\n'
            f'        <div class="pick-meta"><span>{_cat}</span><span>{_price}</span></div>\n'
            f'      </div>\n'
            f'    </a>\n'
        )
    picks_re = re.compile(r'<!-- PICKS_START -->[\s\S]*?<!-- PICKS_END -->')
    html = picks_re.sub(f'<!-- PICKS_START -->\n{picks_html}<!-- PICKS_END -->', html)
    html = re.sub(r'(<span class="picks-date" id="picksDate">)[^<]*(</span>)',
                  r'\g<1>' + _fmt_md(_picks_date) + ' 精选' + r'\g<2>', html)

    # ── 编辑实测 · 深度评测（v6；2026-08-08 改用 content_type 字段）──
    _reviews = [a for a in articles if article_content_type(a) == 'AI评测']
    _reviews = sorted(_reviews, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)[:6]
    reviews_html = ''
    for _a in _reviews:
        # 标签与入选标准一致：统一用 content_type（之前误用 category 映射，导致评测区贴出"AI资讯/教程"）
        _rtag = 'AI评测'
        reviews_html += (
            f'<a class="review-item" href="/articles/{_a["slug"]}/">\n'
            f'        <span class="review-date">{_fmt_md(_a.get("date", ""))}</span>\n'
            f'        <span class="review-title">{escape_html(_a["title"])}</span>\n'
            f'        <span class="review-tag">{_rtag}</span>\n'
            f'    </a>\n'
        )
    reviews_re = re.compile(r'<!-- REVIEWS_START -->[\s\S]*?<!-- REVIEWS_END -->')
    html = reviews_re.sub(f'<!-- REVIEWS_START -->\n{reviews_html}<!-- REVIEWS_END -->', html)

    # ── AI实战教程（v6.9：独立区块，填充真实教程；无内容则整块隐藏；2026-08-08 改用 content_type）──
    _tutorials = [a for a in articles if article_content_type(a) == 'AI教程']
    _tutorials = sorted(_tutorials, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)[:6]
    if _tutorials:
        practice_html = ''
        for _a in _tutorials:
            practice_html += (
                f'<a class="practice-item" href="/articles/{_a["slug"]}/">\n'
                f'            <span class="practice-item-title">{escape_html(_a["title"])}</span>\n'
                f'            <span class="practice-item-tag">教程</span>\n'
                f'        </a>\n'
            )
        practice_re = re.compile(r'<!-- PRACTICE_ITEMS_START -->[\s\S]*?<!-- PRACTICE_ITEMS_END -->')
        html = practice_re.sub(f'<!-- PRACTICE_ITEMS_START -->\n{practice_html}<!-- PRACTICE_ITEMS_END -->', html)
        # 模板默认隐藏独立区块，有教程内容才展示
        html = html.replace('<section class="home-section practice-section" id="practiceSection" style="display:none;">',
                            '<section class="home-section practice-section" id="practiceSection">', 1)
    else:
        html = html.replace('<section class="home-section practice-section" id="practiceSection">',
                            '<section class="home-section practice-section" id="practiceSection" style="display:none;">', 1)

    # ── 首页价值条统计数字（v6）──
    _review_cnt = sum(1 for a in articles if article_content_type(a) == 'AI评测')
    _cmp_dir = os.path.join(BASE_DIR, 'compare')
    try:
        _compare_cnt = len([_d for _d in os.listdir(_cmp_dir)
                            if os.path.isdir(os.path.join(_cmp_dir, _d)) and _d != '_template'])
    except Exception:
        _compare_cnt = 0
    html = re.sub(r'(<b id="statTools">)[^<]*(</b>)', r'\g<1>' + str(len(tools)) + r'\g<2>', html)
    html = re.sub(r'(<b id="statReviews">)[^<]*(</b>)', r'\g<1>' + str(_review_cnt) + r'\g<2>', html)
    html = re.sub(r'(<b id="statCompares">)[^<]*(</b>)', r'\g<1>' + str(_compare_cnt) + r'\g<2>', html)

    # 工具数量显示 — 用re.sub替换（模板中可能已有内容如"共 100+ 款"）
    html = re.sub(r'<span class="tool-count" id="toolCount">.*?</span>', f'<span class="tool-count" id="toolCount">共 {len(tools)} 款</span>', html)

    # 轻量化工具数据（首页JS只需展示字段）
    # 这些字段的完整内容在各自独立的工具详情页（静态HTML）中，不影响SEO
    LIGHTWEIGHT_KEYS = {'name', 'slug', 'emoji', 'color', 'description', 'category', 'subcategory',
                        'tags', 'rating', 'visits', 'badge', 'url', 'price', 'platform', 'created_date'}
    def tool_icon_path(slug):
        """首页JS懒加载图标路径：复用 resolve_icon() 统一解析。"""
        _, web_path = resolve_icon(slug)
        return web_path
    def make_lightweight(tool_list):
        out = []
        for t in tool_list:
            d = {k: v for k, v in t.items() if k in LIGHTWEIGHT_KEYS}
            d['icon'] = tool_icon_path(t.get('slug', ''))
            out.append(d)
        return out

    # P0-2（2026-08-09）：紧凑序列化（无缩进）+ 移除 __REMAINING_TOOLS__。
    # __REMAINING_TOOLS__ 与 __ALL_TOOLS__ 高度重叠（tools[8:] 是其子集），
    # 且全站 JS 无任何消费方，删除后 tools-data.js 体积再减半。
    all_tools_json = json.dumps(make_lightweight(tools), ensure_ascii=False, separators=(',', ':'))
        
    articles_html = ''
    for a in articles[:6]:
        # 统一日期显示格式为 MM/DD
        d = a.get('date', '')
        if '-' in d and len(d) == 10:
            parts = d.split('-')
            display_date = f'{int(parts[1]):02d}/{int(parts[2]):02d}'
        else:
            display_date = d
        articles_html += f'''                        <li>
                            <span class="date">{display_date}</span>
                            <a class="title" href="/articles/{a['slug']}/">{escape_html(a['title'])}</a>
                        </li>\n'''
    
    # ── 注入新类目 sidebar / 移动端按钮（幂等，2026-08-05）──
    # 首页模板自举自上一版 index.html（build_index_page 读 index.html 作模板），
    # 新类目按钮不会自动出现，需每次构建时补齐；已存在则跳过。
    _new_cat_btns = [
        # 2026-08-06: 去掉 emoji（节省 sidebar 空间），分类名直接作为按钮文本
        ("AI学习", "", "var(--cat-learn)"),
        ("AI检测", "", "var(--cat-detect)"),
        ("AI提示词", "", "var(--cat-prompt)"),
    ]
    _missing_side = [b for b in _new_cat_btns if f'class="sidebar-cat" data-category="{b[0]}"' not in html]
    if _missing_side:
        _side_ins = ''.join(
            f'<button class="sidebar-cat" data-category="{n}" style="--dot: {c}">{e} {n}</button>'
            for n, e, c in _missing_side)
        html = re.sub(r'<button class="sidebar-cat" data-category="AI提示词"',
                      _side_ins + r'<button class="sidebar-cat" data-category="AI提示词"',
                      html, count=1)
    _missing_mob = [b for b in _new_cat_btns if f'class="cat-btn" data-category="{b[0]}"' not in html]
    if _missing_mob:
        _mob_ins = ''.join(
            f'<button class="cat-btn" data-category="{n}">{e} {n}</button>'
            for n, e, c in _missing_mob)
        html = re.sub(r'<button class="cat-btn" data-category="AI提示词"',
                      _mob_ins + r'<button class="cat-btn" data-category="AI提示词"',
                      html, count=1)

    # 动态生成热门分类列表
    category_counts = get_category_stats(tools)
    categories_html = ''
    # 按照 index.html 中的顺序
    ordered_categories = ["AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频", "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率", "AI智能体", "AI开发", "AI行业应用", "AI学习", "AI检测", "AI提示词"]
    for category in ordered_categories:
        count = category_counts.get(category, 0)
        # 假设分类页面路径为 /category/slug/index.html
        category_slug = get_category_slug(category)
        categories_html += f'''                        <li><a href="/category/{category_slug}/">{category} ({count})</a></li>\n'''

    # 更新页脚链接
    footer_links_html = '''            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/favorites.html">我的收藏</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
            <a href="mailto:AIToolLabTeam@gmail.com">投稿合作</a>'''

    # 替换工具数量（动态计算）
    all_tools_count = 0
    all_tools_data = load_tools()
    all_tools_count = len(all_tools_data)
    if all_tools_count > 100:
        count_text = f'已收录 {all_tools_count // 100 * 100}+ 工具'
    else:
        count_text = f'已收录 {all_tools_count} 款工具'
    html = re.sub(r'每日更新 · 已收录 \d+\+ (?:款 )?工具', f'每日更新 · {count_text}', html)
    html = re.sub(r'每日更新 · 收录工具 持续更新', f'每日更新 · {count_text}', html)

    # 动态替换 stats 区域数据（精选工具数量 + 分类数量）
    cat_stats = get_category_stats(tools)
    cat_count = len(cat_stats)
    if all_tools_count > 100:
        tool_stat_text = f'{all_tools_count // 100 * 100}+'
    else:
        tool_stat_text = str(all_tools_count)
    html = re.sub(r'<div class="num">20\+</div>', f'<div class="num">{tool_stat_text}</div>', html)
    html = re.sub(r'<div class="label">精选工具</div>', '<div class="label">精选工具</div>', html)
    html = re.sub(r'<div class="num">12</div>(?=\s*<div class="label">工具分类</div>)', f'<div class="num">{cat_count}</div>', html)

    # 替换内容
    html = re.sub(r'(<ul id="articleList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + articles_html + '                    </ul>', html)
    html = re.sub(r'(<ul id="categoryList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + categories_html + '                    </ul>', html)
    html = re.sub(r'(<div class="footer-links">)[\s\S]*?(</div>)', lambda m: m.group(1) + '\n' + footer_links_html + '\n        </div>', html)
    
    # 生成外部工具数据文件（避免首页内联 4.7MB JSON）
    tools_data_js_path = os.path.join(BASE_DIR, 'js', 'tools-data.js')
    os.makedirs(os.path.dirname(tools_data_js_path), exist_ok=True)
    _subdef = get_subcat_def()
    _subcat_json = json.dumps(_subdef, ensure_ascii=False, separators=(',', ':'))
    _cat_slug_json = json.dumps(CATEGORY_SLUG_MAP, ensure_ascii=False, separators=(',', ':'))
    with open(tools_data_js_path, 'w', encoding='utf-8') as f:
        f.write(f'window.__ALL_TOOLS__ = {all_tools_json};\n')
        f.write(f'window.__SUBCATEGORIES__ = {_subcat_json};\n')
        f.write(f'window.__CATEGORY_SLUG_MAP__ = {_cat_slug_json};\n')
    print(f'[OK] js/tools-data.js ({os.path.getsize(tools_data_js_path)//1024}KB)')

    # 移除旧的内联 __ALL_TOOLS__ / __REMAINING_TOOLS__ 脚本（避免重复；REMAINING 段自 P0-2 起不再生成，兼容清理旧模板）
    html = re.sub(r'<script>\s*window\.__ALL_TOOLS__\s*=\s*\[[\s\S]*?\];\s*\n?(?:\s*window\.__REMAINING_TOOLS__\s*=\s*\[[\s\S]*?\];?\s*)?</script>', '', html)

    # 移除旧的 tools-data.js 引用（避免重复注入）— 支持带defer和不带defer的
    html = re.sub(r'<script\s+src="/js/tools-data\.js(\?[^"]*)?"\s*(defer)?\s*></script>\s*', '', html)
    # 移除旧的 favorites.js 引用（避免重复注入；历史构建曾累积 80+ 条）
    html = re.sub(r'<script\s+src="/js/favorites\.js(\?[^"]*)?"\s*(defer)?\s*></script>\s*', '', html)
    # 同时清理 tools-data.js 上方的引导注释（避免 4166 只清 <script> 留下注释造成累积）
    html = re.sub(r'<!--\s*JS defer 加载[^\n]*tools-data\.js[^\n]*-->\s*\n?', '', html)

    # 移除所有已有的百度统计代码片段（无论占位符还是真实代码），避免重复叠加
    html = re.sub(r'<script>\s*var _hmt\s*=\s*_hmt\s*\|\|\s*\[\];\s*\(function\(\)\s*\{[\s\S]*?hm\.src\s*=\s*"[^"]*";[\s\S]*?\}\)\(\);?\s*</script>', '', html)
    html = re.sub(r'<!--\s*BAIDU_TONGJI_PLACEHOLDER\s*-->', '', html)
    # 同时清理"百度统计（异步加载...）"引导注释（避免 4169 只清 <script> 留下注释造成累积）
    html = re.sub(r'<!--\s*百度统计（异步加载[^\n]*-->\s*\n?', '', html)

    # 清理历史烤入的 AdSense enable_page_level_ads 手动 push（旧构建产物残留）。
    # 该 push 会与 AdSense 后台 Auto ads 自动注入冲突，触发
    # "Only one 'enable_page_level_ads' allowed per page" 报错。现在 Auto ads 改由后台控制，
    # 代码不再手动 push，故构建时强制剥离残留的手动 push 脚本。
    html = re.sub(
        r'<script>\s*\(adsbygoogle\s*=\s*window\.adsbygoogle\s*\|\|\s*\[\]\)\.push\(\{\s*'
        r'google_ad_client:\s*"[^"]*",\s*enable_page_level_ads:\s*true\s*\}\);\s*</script>\s*',
        '', html)

    # 收集所有动态head注入内容（带注释，确保注释与代码对齐）
    dynamic_head = ''
    dynamic_head += '<!-- JS defer 加载：tools-data.js，不阻塞渲染 -->\n'
    dynamic_head += f'<script src="/js/tools-data.js?v={int(time.time())}" defer></script>\n'
    dynamic_head += f'<script src="/js/favorites.js?v={int(time.time())}" defer></script>\n'
    dynamic_head += '\n'

    # 注入 Google AdSense 库脚本 + Auto ads 初始化（静态不变量写入模板，不由 inject_ads.py 每次动态注入）
    # 2026-07-31 修复：adsbygoogle.js 国内被墙 → google.com/recaptcha iframe 超时 20s+ 拖垮加载。
    # enabled=false 时从模板中剥离历史注入的脚本（站点验证仅需 meta 标签，不影响 AdSense 验证）。
    html = re.sub(
        r'\s*<script[^>]*src="https://pagead2\.googlesyndication\.com/'
        r'pagead/js/adsbygoogle\.js[^"]*"[^>]*></script>\s*',
        '\n', html, flags=re.IGNORECASE)
    if 'adsbygoogle.js' not in html:
        _ads_cfg = {}
        try:
            ap = os.path.join(BASE_DIR, 'ads', 'config.json')
            if os.path.isfile(ap):
                _ads_cfg = json.load(open(ap, encoding='utf-8'))
        except Exception:
            pass
        _adsense = _ads_cfg.get('adsense', {})
        if _adsense.get('enabled'):
            _pid = _adsense.get('publisherId', '')
            if _pid:
                # 仅加载 AdSense 库脚本。Auto ads（页级自动广告）由 AdSense 后台开启控制，
                # 此处【不再】手动 push enable_page_level_ads——否则会与后台自动注入冲突，
                # 在控制台报 "Only one 'enable_page_level_ads' allowed per page" 错误。
                dynamic_head += f'    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={_pid}" crossorigin="anonymous"></script>\n'

    dynamic_head += '<!-- 百度统计（异步加载，不阻塞渲染） -->\n'

    # 注入 OG 标签（如果缺失 og:url）
    if 'og:url' not in html:
        dynamic_head += '<meta property="og:url" content="https://www.aitoollab.cn/">\n'

    # 注入百度统计代码
    dynamic_head += f'{BAIDU_TONGJI}\n'

    # 注入 Bing Webmaster 验证标签（如果缺失）
    BING_VERIFY = '    <meta name="msvalidate.01" content="D2B58E242903570E029A957ECDFF1E05" />'
    if 'msvalidate.01' not in html:
        dynamic_head += f'{BING_VERIFY}\n'

    # 统一替换 BUILD_DYNAMIC_HEAD 占位符（首页模板专用）
    if '<!-- BUILD_DYNAMIC_HEAD -->' in html:
        html = html.replace('<!-- BUILD_DYNAMIC_HEAD -->', dynamic_head)
    else:
        # 非首页模板，fallback到</head>
        html = html.replace('</head>', dynamic_head + '</head>')

    # 确保返回顶部按钮存在（兜底注入）
    if 'id="backToTop"' not in html:
        BACK_TO_TOP_HTML = '''
    <button id="backToTop" aria-label="返回顶部">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </button>'''
        html = html.replace('</body>', BACK_TO_TOP_HTML + '\n</body>')

    # BUG1修复：不再注入内联backToTop脚本，main.js已包含完整逻辑
    # 清理可能存在的内联返回顶部脚本（防止重复）
    html = re.sub(r'<script>\s*// 返回顶部按钮[\s\S]*?</script>\s*', '', html)
    html = re.sub(r'<script>\s*\(function\(\)\{\s*var b=document\.getElementById\("backToTop"\)[\s\S]*?\}\)\(\);\s*</script>\s*', '', html)

    # 首页按分类浏览钻取区已移除：改为左侧导航子类目树

    # 替换导航为最新版本（确保含AI词典等新增入口）
    old_nav_start = '    <nav class="global-nav" aria-label="全局导航">'
    old_nav_end = '    </nav>'
    start_idx = html.find(old_nav_start)
    end_idx = html.find(old_nav_end, start_idx) + len(old_nav_end) if start_idx >= 0 else -1
    if start_idx >= 0 and end_idx > start_idx:
        html = html[:start_idx] + GLOBAL_NAV + html[end_idx:]

    return html

from urllib.parse import quote as url_quote

def load_news_archive():
    import glob
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

def build_news_page(all_tools=None):
    if all_tools is None:
        all_tools = load_tools()
    daily, dates = load_news_archive()
    if not dates:
        print('[NEWS] 无快讯数据，跳过')
        return

    today = dates[0]
    today_news = daily[today]
    NEWS_DIR = os.path.join(BASE_DIR, 'news')
    SITE = 'https://www.aitoollab.cn'

    HEADER = '<header class="header"><div class="header-inner"><a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a></div></header>'
    FOOTER = f'<footer class="footer"><p>&copy; {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p></footer>'

    CAT_LABEL = {'models':'模型发布','products':'产品发布','industry':'行业动态','opinion':'观点','paper':'论文研究'}
    CAT_COLOR = {'models':'#6366f1','products':'#00A64F','industry':'#f59e0b','opinion':'#ec4899','paper':'#3b82f6'}

    def _card(item, first=False):
        cat = item.get('category','')
        cl = CAT_LABEL.get(cat,cat)
        cc = CAT_COLOR.get(cat,'#64748b')
        title = escape_html(item.get('title',''))
        summary = escape_html(item.get('summary',''))
        src = escape_html(item.get('source',''))
        src_url = item.get('source_url','')
        ts = item.get('published_at','')[:16].replace('T',' ')
        b = ' style="border-left:3px solid #00A64F"' if first else ''
        return f'''            <article class="news-card"{b}>
                <div class="news-card-body">
                    <h2 class="news-card-title">{title}</h2>
                    <p class="news-card-summary">{summary}</p>
                    <div class="news-card-meta">
                        <span class="news-cat-tag" style="background:{cc}15;color:{cc}">{cl}</span>
                        {"<span class='news-sep'>·</span>" if src_url or src else ""}
                        {f'<a href="{src_url}" target="_blank" rel="noopener" class="news-source-link">{src}</a>' if src_url else f'<span class="news-source">{src}</span>'}
                        {f"<span class='news-sep'>·</span>" if ts else ""}
                        {f'<time class="news-time">{ts}</time>' if ts else ""}
                    </div>
                </div>
            </article>'''

    SHARE_CSS = '.news-share{display:flex;gap:8px;align-items:center}.news-share-btn{display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;font-size:13px;color:#475569;cursor:pointer;text-decoration:none;transition:all .15s;font-family:inherit}.news-share-btn:hover{background:#e6f4ed;border-color:#00A64F;color:#00A64F}.news-share label{font-size:13px;color:#94a3b8;margin-right:4px}.news-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e293b;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;z-index:999;opacity:0;transition:opacity .2s}.news-toast.show{opacity:1}[data-theme="dark"] .news-share-btn{background:#1e293b;border-color:#334155;color:#94a3b8}[data-theme="dark"] .news-share-btn:hover{background:rgba(0,166,79,0.12);border-color:#00A64F;color:#00A64F}'
    SHARE_JS = 'function copyLink(){navigator.clipboard.writeText(location.href).then(function(){var t=document.getElementById("newsToast");t.classList.add("show");setTimeout(function(){t.classList.remove("show")},1800)})}'
    FILTER_JS = f"""(function(){{
    var p=document.querySelectorAll('.news-filter-pill');
    var c=document.querySelectorAll('.news-item');
    var cats={json.dumps(CAT_LABEL)};
    p.forEach(function(b){{b.addEventListener('click',function(e){{e.preventDefault();var f=b.dataset.filter;
    p.forEach(function(x){{x.classList.remove('active')}});b.classList.add('active');
    c.forEach(function(x){{var t=(x.querySelector('.news-item-cat')||{{}}).textContent||'';
    x.style.display=(f==='all'||t===cats[f])?'':'none'}});
    document.querySelectorAll('.news-day-block').forEach(function(s){{
    var any=Array.prototype.some.call(s.querySelectorAll('.news-item'),function(x){{return x.style.display!=='none'}});
    s.style.display=any?'':'none'}})}})}})
}})()"""

    # ── /news/ ──
    pills = ''.join(f'<a href="#{k}" class="news-filter-pill{" active" if k=="all" else ""}" data-filter="{k}">{v}</a>'
                    for k,v in [('all','全部')]+[(c, CAT_LABEL[c]) for c in ['models','products','industry','opinion']])
    cards = ''.join(_card(item, i==0) for i,item in enumerate(today_news))
    archive = ''.join(f'<a href="/news/{d}/" class="news-date-link">{d[5:]}</a>' for d in dates[:14])

    # 取当天头条摘要作 meta description 钩子
    _ns = today_news[0].get('summary','') if today_news else ''
    _ns = _ns.replace('\n',' ').strip()[:150]
    if not _ns:
        _ns = 'AI行业最新动态'
    index_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI快讯 - {today} 精选 | AI行业每日动态 - AI工具宝箱</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{today}精选{len(today_news)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,AI日报,AI行业动态,{today}">
<link rel="canonical" href="{SITE}/news/"><style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript><style>{SHARE_CSS}</style></head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <span>AI快讯</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">AI快讯</h1><p class="news-page-date">{today} · {len(today_news)}条精选 · 共{len(dates)}期</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/')}&title={url_quote('AI快讯 - '+today+' 精选')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-filter-bar">{pills}</div></div>
<div class="news-cards">{cards}</div>
<div class="news-archive"><h3 class="news-archive-title">历史快讯</h3><div class="news-archive-links">{archive}</div></div>
</main>
{FOOTER}
{BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script><script>{FILTER_JS}</script>
</body></html>'''

    os.makedirs(NEWS_DIR, exist_ok=True)
    _emit(os.path.join(NEWS_DIR, 'index.html'), index_html)
    print(f'  [OK] news/index.html ({len(today_news)}条)')

    # ── /news/YYYY-MM-DD/ ──
    for d in dates:
        items = daily[d]
        cards_d = ''.join(_card(item, i==0) for i,item in enumerate(items))
        # 取当天头条摘要作 meta description 钩子
        _ns = items[0].get('summary','') if items else ''
        _ns = _ns.replace('\n',' ').strip()[:150]
        if not _ns:
            _ns = 'AI行业最新动态'
        idx = dates.index(d)
        prev = f'<a href="/news/{dates[idx+1]}/" class="news-nav-btn">← {dates[idx+1]}</a>' if idx < len(dates)-1 else ''
        nxt = f'<a href="/news/{dates[idx-1]}/" class="news-nav-btn">{dates[idx-1]} →</a>' if idx > 0 else ''
        title_d = f'{d} AI快讯 · AI行业每日动态 - AI工具宝箱'

        daily_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_d}</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{d}精选{len(items)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,{d}">
<link rel="canonical" href="{SITE}/news/{d}/"><style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript><style>{SHARE_CSS}</style></head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <a href="/news/">AI快讯</a> &raquo; <span>{d}</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">{d} AI快讯</h1><p class="news-page-date">{len(items)}条精选</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/'+d+'/')}&title={url_quote(d+' AI快讯')}" target="_blank" rel="noopener">微博</a>
</div></div>
<div class="news-nav-row">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div></div>
<div class="news-cards">{cards_d}</div>
<div class="news-nav-row news-nav-bottom">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div>
</main>
{FOOTER}
{BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script>
</body></html>'''

        dd = os.path.join(NEWS_DIR, d)
        os.makedirs(dd, exist_ok=True)
        _emit(os.path.join(dd, 'index.html'), daily_html)
        print(f'  [OK] news/{d}/index.html ({len(items)}条)')

    print(f'[OK] 快讯页完成: {len(dates)}期, {sum(len(v) for v in daily.values())}条')

# === AI-NEWS-FUNC-BEGIN ===
from urllib.parse import quote as url_quote

def load_news_archive():
    import glob
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

def build_news_page(all_tools=None):
    if all_tools is None:
        all_tools = load_tools()
    daily, dates = load_news_archive()
    if not dates:
        print('[NEWS] 无快讯数据，跳过')
        return

    today = dates[0]
    today_news = daily[today]
    NEWS_DIR = os.path.join(BASE_DIR, 'news')
    SITE = 'https://www.aitoollab.cn'

    # 快讯硬伤门禁（2026-08-15）：构建前检查当天快讯，空摘要/英文标题/空标题 打印醒目警告。
    # 只报告不阻断（快讯页生成优先于质量；"价值提炼"靠生成 prompt 治本，此处只兜底硬伤）。
    try:
        import check_news_quality as _nq
        _nfail = 0
        for _it in today_news:
            _f, _w = _nq.check_one(_it)
            if _f:
                _nfail += 1
                print(f'  [快讯门禁] ✗ {_it.get("id","")}: {"; ".join(_f)} → {( _it.get("title") or "")[:40]}')
        if _nfail:
            print(f'  [快讯门禁] ⚠️ 当天 {len(today_news)} 条中有 {_nfail} 条硬伤，请补 summary / 译标题 / 删空条目')
    except Exception:
        pass

    HEADER = '<header class="header"><div class="header-inner"><a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a></div></header>'
    FOOTER = f'<footer class="footer"><p>&copy; {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p></footer>'

    CAT_LABEL = {'models':'模型发布','products':'产品发布','industry':'行业动态','opinion':'观点','paper':'论文研究'}
    CAT_COLOR = {'models':'#6366f1','products':'#00A64F','industry':'#f59e0b','opinion':'#ec4899','paper':'#3b82f6'}
    CAT_ORDER = ['models','products','industry','opinion','paper']
    # 栏目 SEO：栏目标题 + 长尾关键词（承接检索词，沉淀权重）
    CAT_SEO = {
        'models':   {'longtail':'最新大模型发布,开源大模型,AI模型上线,大模型汇总,AI基础模型',
                     'desc':'AI工具宝箱每日聚合AI模型发布动态：最新大模型发布、开源模型、模型更新与实测解读一网打尽，覆盖DeepSeek、Qwen、Kimi、Claude、GPT等主流与国产模型，每条附官方来源可溯源，帮你紧跟AI模型进展、把握选型方向。'},
        'products': {'longtail':'最新AI产品,AI工具上线,AI应用发布,AI产品汇总,AI软件更新',
                     'desc':'AI工具宝箱每日聚合AI产品发布动态：最新AI产品、AI应用上线与功能更新一站汇总，覆盖对话、写作、绘画、视频、编程等品类，每条附官方来源可溯源并附一句话使用建议，同时给出免费额度与价格信息供快速判断，帮你及时发现值得试用与收藏的新工具。'},
        'industry': {'longtail':'AI行业新闻,AI行业动态,人工智能资讯,AI公司动态,AI融资并购',
                     'desc':'AI工具宝箱每日聚合AI行业动态：AI公司动态、融资并购、政策监管与产业趋势一站汇总，覆盖OpenAI、谷歌、字节、阿里等国内外大厂与创业公司，每条附官方来源可溯源并附编辑部点评，数据每日更新，帮你高效把握行业风向、发现机会。'},
        'opinion':  {'longtail':'AI观点,AI评论,人工智能思考,AI趋势解读,AI深度评论',
                     'desc':'AI工具宝箱每日聚合AI观点内容：大模型与AI行业趋势解读、深度评论与争议话题分析，观点多元、附事实依据，覆盖技术路线、商业模式与社会影响等维度，既有行业大咖视角也有编辑部独立解读，并附原文链接便于追溯，帮你建立更独立、更立体的判断。'},
        'paper':    {'longtail':'AI论文,最新AI研究,人工智能论文,AI论文解读,机器学习论文',
                     'desc':'AI工具宝箱每日聚合AI论文研究动态：最新AI论文、研究成果与论文解读，覆盖大模型、Agent、多模态、推理优化等方向，每条附论文来源可溯源并附核心结论速览，按研究方向归类便于查阅，帮你高效追踪学术前沿、读懂关键技术突破。'},
    }

    # ── 工具名 → slug 映射（自动内链）──
    _slug_set = set()
    name_map = []
    for _t in all_tools:
        _nm = (_t.get('name') or '').strip()
        _sl = (_t.get('slug') or '').strip()
        if not _nm or not _sl:
            continue
        if len(_nm) < 2:
            continue
        if _nm.isascii() and len(_nm) < 3:
            continue
        name_map.append((_nm, _sl))
        _slug_set.add(_sl)
    _ALIASES = {'Kimi 智能助手': 'kimi', '智谱清言': 'zhipu', '通义千问': 'qwen', '文心一言': 'wenxin'}
    for _anm, _asl in _ALIASES.items():
        if _asl in _slug_set and not any(_anm == _n for _n, _ in name_map):
            name_map.append((_anm, _asl))
    name_map.sort(key=lambda x: -len(x[0]))

    def _linkify(text):
        """在已转义的纯文本中，将工具名替换为站内链接（避免嵌套/重叠）。"""
        matches = []
        for _nm, _sl in name_map:
            _start = 0
            while True:
                _i = text.find(_nm, _start)
                if _i == -1:
                    break
                matches.append((_i, _i + len(_nm), _sl, _nm))
                _start = _i + len(_nm)
        matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
        out = []
        last = 0
        for _s, _e, _sl, _nm in matches:
            if _s < last:
                continue
            out.append(text[last:_s])
            out.append(f'<a href="/tools/{_sl}/" class="news-inlink">{_nm}</a>')
            last = _e
        out.append(text[last:])
        return ''.join(out)

    def _card(item, first=False, date_ctx=None):
        # 时间线条目（2026-08-16 第三版，对标 ai-bot.cn 移动端：大标题自然换行、无下划线、去卡片盒）
        cat = item.get('category','')
        cl = CAT_LABEL.get(cat,cat)
        cc = CAT_COLOR.get(cat,'#64748b')
        # 标题规范化：去尾部多余标点（快准狠，标题干净利落）
        title = (item.get('title') or '').strip()
        while title and title[-1] in '。！？，、；：…!?.,;: ':
            title = title[:-1].rstrip()
        title_l = _linkify(escape_html(title))
        summary = (item.get('summary') or '').strip()
        src = escape_html(item.get('source',''))
        src_url = item.get('source_url','')
        ts = item.get('published_at','')
        ts_display = ts[:16].replace('T',' ')[5:] if ts else ''  # 08-14 22:27，去年份更简
        date_link = f'<a href="/news/{date_ctx}/" class="news-date-ctx">{date_ctx}</a>' if date_ctx else ''
        sum_html = f'<p class="news-item-summary">{_linkify(escape_html(summary))}</p>' if summary else ''
        readmore = f'<a href="{src_url}" target="_blank" rel="noopener nofollow" class="news-readmore">阅读原文</a>' if src_url else ''
        return f'''            <article class="news-item">
                <i class="news-item-dot" style="background:{cc}"></i>
                <div class="news-item-meta"><span class="news-item-cat" style="color:{cc}">{cl}</span>{f'<time>{ts_display}</time>' if ts_display else ''}</div>
                <h2 class="news-item-title">{title_l}</h2>
                {sum_html}
                <div class="news-item-foot">{f'<span>来源：{src}</span>' if src else ''}{readmore}{date_link}</div>
            </article>'''

    SHARE_CSS = '.news-share{display:flex;gap:8px;align-items:center}.news-share-btn{display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;font-size:13px;color:#475569;cursor:pointer;text-decoration:none;transition:all .15s;font-family:inherit}.news-share-btn:hover{background:#e6f4ed;border-color:#00A64F;color:#00A64F}.news-share label{font-size:13px;color:#94a3b8;margin-right:4px}.news-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e293b;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;z-index:999;opacity:0;transition:opacity .2s}.news-toast.show{opacity:1}[data-theme="dark"] .news-share-btn{background:#1e293b;border-color:#334155;color:#94a3b8}[data-theme="dark"] .news-share-btn:hover{background:rgba(0,166,79,0.12);border-color:#00A64F;color:#00A64F}.news-inlink{color:#00A64F;text-decoration:none;font-weight:600}.news-inlink:hover{text-decoration:none;opacity:.8}[data-theme="dark"] .news-inlink{color:#34d399}.news-catnav{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}.news-catnav-link{display:inline-block;padding:6px 14px;border-radius:20px;background:#f1f5f9;color:#475569;font-size:13px;text-decoration:none;transition:all .15s}.news-catnav-link:hover{background:#e6f4ed;color:#00A64F}[data-theme="dark"] .news-catnav-link{background:#1e293b;color:#94a3b8}[data-theme="dark"] .news-catnav-link:hover{background:rgba(0,166,79,.12);color:#34d399}.news-date-ctx{color:#94a3b8;font-size:12px;text-decoration:none;margin-left:2px}.news-date-ctx:hover{color:#00A64F}[data-page-type="news"] .container{max-width:780px;margin:0 auto;padding:6px 20px 32px}[data-page-type="news"] .breadcrumb{max-width:780px;padding:0 20px;margin:8px auto 8px}[data-page-type="news"] .container.news-index,[data-page-type="news"] .breadcrumb.news-index{max-width:1100px}.news-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:28px;align-items:start}.news-sidebar{position:sticky;top:16px;display:flex;flex-direction:column;gap:18px}.news-side-box{background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);border-radius:12px;padding:14px 16px}.news-side-title{font-size:14px;font-weight:700;margin:0 0 10px;color:var(--text-main,#1e293b)}.news-day-list{display:flex;flex-direction:column;gap:2px;max-height:380px;overflow-y:auto}.news-day-link{display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-radius:8px;font-size:13.5px;color:var(--text-main,#1e293b);text-decoration:none;line-height:1.4}.news-day-link:hover{background:#e6f4ed;color:#00A64F}.news-day-link .n{font-size:12px;color:#94a3b8;margin-left:8px;flex-shrink:0}.news-day-block{margin-bottom:28px;scroll-margin-top:200px}.news-day-divider{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px;padding:10px 14px 10px 16px;background:linear-gradient(90deg,#f0fdf4 0%,#f0fdf400 100%);border-left:5px solid #00A64F;border-radius:0 8px 8px 0}.news-day-divider .d{font-size:20px;font-weight:800;color:var(--text-main,#1e293b);letter-spacing:.5px}.news-day-divider .wk{display:inline-block;padding:2px 10px;background:#00A64F;color:#fff;font-size:12px;font-weight:700;border-radius:12px;letter-spacing:.5px}.news-day-divider a.news-day-more{margin-left:auto;font-size:12.5px;font-weight:500;color:#00A64F;text-decoration:none;opacity:.8}.news-day-divider a.news-day-more:hover{opacity:1;text-decoration:underline}[data-theme="dark"] .news-side-box{background:#1e293b;border-color:#334155}[data-theme="dark"] .news-day-link{color:#cbd5e1}[data-theme="dark"] .news-day-link:hover{background:rgba(0,166,79,.12);color:#34d399}[data-theme="dark"] .news-day-divider{background:linear-gradient(90deg,rgba(52,211,153,.10) 0%,rgba(52,211,153,0) 100%);border-left-color:#34d399}[data-theme="dark"] .news-day-divider .d{color:#f1f5f9}[data-theme="dark"] .news-day-divider .wk{background:#34d399;color:#0f172a}@media (max-width:900px){.news-layout{grid-template-columns:1fr}.news-sidebar{display:none}.news-day-divider{padding:8px 12px}.news-day-divider .d{font-size:18px}.news-day-block{scroll-margin-top:190px}.news-day-strip{display:flex}}html{scroll-behavior:smooth}[data-page-type="news"] .news-cards{display:block;position:relative;margin:0 0 8px;padding-left:24px;border-left:2px dotted #d8e0ea}.news-item{position:relative;padding:15px 0 17px}.news-item-dot{position:absolute;left:-30px;top:22px;width:11px;height:11px;border-radius:50%;box-shadow:0 0 0 3px var(--body-bg,#fff)}.news-item-meta{display:flex;gap:10px;align-items:baseline;font-size:12.5px;color:#94a3b8;margin-bottom:3px}.news-item-cat{font-weight:600}.news-item-title{font-size:17.5px;font-weight:700;line-height:1.55;margin:0 0 8px;color:var(--text-main,#1e293b)}.news-item-summary{font-size:14px;line-height:1.85;color:var(--text-muted,#475569);margin:0 0 8px}.news-item-foot{display:flex;gap:14px;align-items:center;font-size:12.5px;color:#94a3b8}[data-page-type="news"] .news-readmore{margin-left:auto;color:#00A64F;background:none;padding:0;border-radius:0;font-size:12.5px;font-weight:600;text-decoration:none}[data-page-type="news"] .news-readmore:hover{opacity:.75}.news-day-strip{display:none;gap:8px;overflow-x:auto;padding:2px 2px 12px;margin-bottom:4px;scrollbar-width:none;-webkit-overflow-scrolling:touch}.news-day-strip::-webkit-scrollbar{display:none}.news-day-strip a{flex-shrink:0;padding:5px 13px;border-radius:16px;background:#f1f5f9;color:#475569;font-size:12.5px;text-decoration:none;white-space:nowrap}.news-day-strip a:active{background:#00A64F;color:#fff}[data-theme="dark"] [data-page-type="news"] .news-cards{border-left-color:#334155}[data-theme="dark"] .news-item-title{color:#f1f5f9}[data-theme="dark"] .news-item-summary{color:#94a3b8}[data-theme="dark"] .news-item-dot{box-shadow:0 0 0 3px #0f172a}[data-theme="dark"] [data-page-type="news"] .news-readmore{color:#34d399}[data-theme="dark"] .news-day-strip a{background:#1e293b;color:#94a3b8}@media (max-width:900px){.news-day-strip{display:flex}}'
    SHARE_JS = 'function copyLink(){navigator.clipboard.writeText(location.href).then(function(){var t=document.getElementById("newsToast");t.classList.add("show");setTimeout(function(){t.classList.remove("show")},1800)})}'
    FILTER_JS = f"""(function(){{
    var p=document.querySelectorAll('.news-filter-pill');
    var c=document.querySelectorAll('.news-item');
    var cats={json.dumps(CAT_LABEL)};
    p.forEach(function(b){{b.addEventListener('click',function(e){{e.preventDefault();var f=b.dataset.filter;
    p.forEach(function(x){{x.classList.remove('active')}});b.classList.add('active');
    c.forEach(function(x){{var t=(x.querySelector('.news-item-cat')||{{}}).textContent||'';
    x.style.display=(f==='all'||t===cats[f])?'':'none'}});
    document.querySelectorAll('.news-day-block').forEach(function(s){{
    var any=Array.prototype.some.call(s.querySelectorAll('.news-item'),function(x){{return x.style.display!=='none'}});
    s.style.display=any?'':'none'}})}})}})
}})()"""

    # ── /news/ ──
    pills = ''.join(f'<a href="#{k}" class="news-filter-pill{" active" if k=="all" else ""}" data-filter="{k}">{v}</a>'
                    for k,v in [('all','全部')]+[(c, CAT_LABEL[c]) for c in ['models','products','industry','opinion']])
    # ── /news/ 汇总页：多天连排长页 + 日期隔断 + 右侧栏（2026-08-16 对标 ai-bot.cn/daily-ai-news/）──
    INDEX_DAYS = 30  # 汇总页展示最近 30 天；更早的经日期索引进单期页
    _WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']
    def _day_label(ds):
        try:
            _dt = _dt_build.strptime(ds, '%Y-%m-%d')
            return f'{_dt.month}月{_dt.day}日', _WEEKDAYS[_dt.weekday()]
        except Exception:
            return ds, ''
    _labels = {d: _day_label(d) for d in dates}
    index_dates = [d for d in dates[:INDEX_DAYS] if daily[d]]
    day_blocks = []
    for d in index_dates:
        _items = daily[d]
        _dl, _wk = _labels[d]
        _cards_d = ''.join(_card(item, i==0) for i,item in enumerate(_items))
        day_blocks.append(f'''<section class="news-day-block" id="d-{d}">
<h2 class="news-day-divider">{_dl}<span class="wk">{_wk}</span><a href="/news/{d}/" class="news-day-more">{len(_items)}条精选 · 单期页</a></h2>
<div class="news-cards">{_cards_d}</div>
</section>''')
    feed = '\n'.join(day_blocks)
    # 右侧栏：日期索引（锚点跳转当天区块；超出 INDEX_DAYS 的链到单期页）
    _day_links = ''.join(
        f'<a href="#d-{d}" class="news-day-link"><span>{_labels[d][0]} {_labels[d][1]}</span><span class="n">{len(daily[d])}条</span></a>'
        for d in index_dates)
    _older_links = ''.join(
        f'<a href="/news/{d}/" class="news-day-link"><span>{d}</span><span class="n">{len(daily[d])}条</span></a>'
        for d in dates[INDEX_DAYS:INDEX_DAYS+14])

    # 取当天头条摘要作 meta description 钩子
    _ns = today_news[0].get('summary','') if today_news else ''
    _ns = _ns.replace('\n',' ').strip()[:150]
    if not _ns:
        _ns = 'AI行业最新动态'
    built_urls = [f'{SITE}/news/']
    cats_present = sorted({it.get('category') for d in dates for it in daily[d] if it.get('category') in CAT_LABEL},
                          key=lambda c: CAT_ORDER.index(c) if c in CAT_ORDER else 99)
    catnav = ''.join(f'<a href="/news/{c}/" class="news-catnav-link">{CAT_LABEL[c]}</a>' for c in cats_present)
    _total_shown = sum(len(daily[d]) for d in index_dates)
    # 移动端顶部日期条（侧栏在移动端隐藏，锚点导航靠它，2026-08-16 第三轮）
    _strip = ''.join(f'<a href="#d-{d}">{_labels[d][0]}</a>' for d in index_dates[:14])

    index_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI快讯 - {today} 精选 | AI行业每日动态 - AI工具宝箱</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{today}精选{len(today_news)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,AI日报,AI行业动态,{today}">
<link rel="canonical" href="{SITE}/news/"><style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb news-index"><a href="/">首页</a> &raquo; <span>AI快讯</span></nav>
<main class="container news-index">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">AI快讯</h1><p class="news-page-date">{today} 更新 · 共{len(dates)}期 · 本页最近{len(index_dates)}天{_total_shown}条</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/')}&title={url_quote('AI快讯 - '+today+' 精选')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-filter-bar">{pills}</div></div>
<div class="news-day-strip">{_strip}</div>
<div class="news-layout">
<div class="news-feed">{feed}</div>
<aside class="news-sidebar">
<div class="news-side-box"><h3 class="news-side-title">按分类浏览</h3><div class="news-catnav">{catnav}</div></div>
<div class="news-side-box"><h3 class="news-side-title">日期索引</h3><div class="news-day-list">{_day_links}{_older_links}</div></div>
</aside>
</div>
</main>
{FOOTER}
{BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script><script>{FILTER_JS}</script>
</body></html>'''

    os.makedirs(NEWS_DIR, exist_ok=True)
    with open(os.path.join(NEWS_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'  [OK] news/index.html (最近{len(index_dates)}天{_total_shown}条)')

    # ── /news/YYYY-MM-DD/ ──
    for d in dates:
        items = daily[d]
        cards_d = ''.join(_card(item, i==0) for i,item in enumerate(items))
        # 取当天头条摘要作 meta description 钩子
        _ns = items[0].get('summary','') if items else ''
        _ns = _ns.replace('\n',' ').strip()[:150]
        if not _ns:
            _ns = 'AI行业最新动态'
        idx = dates.index(d)
        prev = f'<a href="/news/{dates[idx+1]}/" class="news-nav-btn">← {dates[idx+1]}</a>' if idx < len(dates)-1 else ''
        nxt = f'<a href="/news/{dates[idx-1]}/" class="news-nav-btn">{dates[idx-1]} →</a>' if idx > 0 else ''
        title_d = f'{d} AI快讯 · AI行业每日动态 - AI工具宝箱'

        daily_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_d}</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{d}精选{len(items)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,{d}">
<link rel="canonical" href="{SITE}/news/{d}/"><style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <a href="/news/">AI快讯</a> &raquo; <span>{d}</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">{d} AI快讯</h1><p class="news-page-date">{len(items)}条精选</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/'+d+'/')}&title={url_quote(d+' AI快讯')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-nav-row">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div></div>
<div class="news-cards">{cards_d}</div>
<div class="news-nav-row news-nav-bottom">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div>
</main>
{FOOTER}
{BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script>
</body></html>'''

        dd = os.path.join(NEWS_DIR, d)
        os.makedirs(dd, exist_ok=True)
        with open(os.path.join(dd, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(daily_html)
        built_urls.append(f'{SITE}/news/{d}/')
        print(f'  [OK] news/{d}/index.html ({len(items)}条)')

    # ── /news/{cat}/ 栏目聚合页（独立URL + 长尾词，承接检索）──
    for cat in cats_present:
        cat_items = [(d, it) for d in dates for it in daily[d] if it.get('category') == cat]
        if not cat_items:
            continue
        cl = CAT_LABEL[cat]
        seo = CAT_SEO.get(cat, {})
        longtail = seo.get('longtail', cl)
        desc = seo.get('desc', f'AI工具宝箱每日聚合 {cl} 动态，持续更新。')
        cards_c = ''.join(_card(it, i == 0, date_ctx=d) for i, (d, it) in enumerate(cat_items))
        cat_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{cl} - 每日更新 | AI行业动态汇总 - AI工具宝箱</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="AI快讯,{cl},{longtail}">
<link rel="canonical" href="{SITE}/news/{cat}/"><style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <a href="/news/">AI快讯</a> &raquo; <span>{cl}</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">{cl}</h1><p class="news-page-date">{len(cat_items)}条 · 每日更新</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/'+cat+'/')}&title={url_quote(cl+' - AI快讯')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-catnav">{catnav}</div></div>
<div class="news-cards">{cards_c}</div>
<div class="news-archive"><h3 class="news-archive-title">全部快讯</h3><div class="news-archive-links"><a href="/news/" class="news-date-link">返回汇总</a></div></div>
</main>
{FOOTER}
{BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script>
</body></html>'''
        cd = os.path.join(NEWS_DIR, cat)
        os.makedirs(cd, exist_ok=True)
        with open(os.path.join(cd, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(cat_html)
        built_urls.append(f'{SITE}/news/{cat}/')
        print(f'  [OK] news/{cat}/index.html ({len(cat_items)}条)')

    print(f'[OK] 快讯页完成: {len(dates)}期, {sum(len(v) for v in daily.values())}条, {len(cats_present)}个栏目')
    return built_urls

# === AI-NEWS-FUNC-END ===

def build_dict_page(term, all_terms, index):
    """生成单个词典术语的详情页"""
    slug = term['slug']
    term_name = term['term']
    en_name = term.get('en', '')
    emoji = term.get('emoji', '📖')
    category = term.get('category', '')
    tags = term.get('tags', [])
    detail = term.get('detail', term.get('brief', ''))
    brief = term.get('brief', '')

    # 转换detail中的markdown为HTML（简单处理：**加粗**、\n换行、代码块、列表）
    def md_to_html(text):
        # 先对纯文本部分做HTML转义
        text = escape_html(text)
        # 恢复被转义的markdown标记并转为HTML
        # 代码块
        text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code>\2</code></pre>', text)
        # 行内代码 (注意：转义后 ` 变为 &#96;)
        text = re.sub(r'&#96;([^&#96;]+)&#96;', r'<code>\1</code>', text)
        # 加粗
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 标题
        lines = text.split('\n')
        result = []
        for line in lines:
            if line.startswith('### '):
                result.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                result.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('- &lt;strong&gt;') or line.startswith('- <strong>'):
                # 带加粗的列表项，保持HTML
                content = line[2:]
                result.append(f'<li>{content}</li>')
            elif line.startswith('- '):
                result.append(f'<li>{line[2:]}</li>')
            elif line.strip() == '':
                result.append('')
            elif line.startswith('|'):
                result.append(line)
            else:
                result.append(line)
        text = '\n'.join(result)
        # 包裹<li>序列
        text = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\n\1</ul>', text)
        # 段落
        text = re.sub(r'\n\n+', '</p><p>', text)
        text = '<p>' + text + '</p>'
        # 清理空段落和不正确的嵌套
        text = re.sub(r'<p>\s*</p>', '', text)
        text = re.sub(r'<p>(\s*<h[23]>)', r'\1', text)
        text = re.sub(r'(</h[23]>)\s*</p>', r'\1', text)
        text = re.sub(r'<p>(\s*<ul>)', r'\1', text)
        text = re.sub(r'(</ul>)\s*</p>', r'\1', text)
        text = re.sub(r'<p>(\s*<pre>)', r'\1', text)
        text = re.sub(r'(</pre>)\s*</p>', r'\1', text)
        return text

    # 预加工：将 **章节标题**： 模式转为 ### 章节标题，让 md_to_html 生成 <h3>
    # 避免 md_to_html 中 <ul> 闭合导致后续 <strong> 失去 <p> 包裹的问题
    detail = re.sub(r'\n\n\*\*(.+?)\*\*：', r'\n\n### \1\n\n', detail)

    detail_html = md_to_html(detail)

    # 后处理：按 <h3> 切分，每段包裹为 section 卡片
    h3_parts = re.split(r'(<h3>[^<]+</h3>)', detail_html)
    if len(h3_parts) > 1:
        intro_html = h3_parts[0]
        sections_html = []
        for i in range(1, len(h3_parts), 2):
            h3_tag = h3_parts[i]
            content = h3_parts[i + 1] if i + 1 < len(h3_parts) else ''
            title_match = re.match(r'<h3>(.+)</h3>', h3_tag)
            if title_match:
                sections_html.append(f'<section class="dict-section"><h3>{title_match.group(1)}</h3>{content}</section>')
            else:
                sections_html.append(h3_tag + content)
        detail_html = intro_html + '\n'.join(sections_html)

    tags_html = ''.join([f'<span>{escape_html(t)}</span>' for t in tags])
    category_html = f'<span class="dict-detail-category">{escape_html(category)}</span>'

    # 侧边栏：快速参考 + 词条导航
    sb_prev = ''
    sb_next = ''
    if index > 0:
        pt = all_terms[index - 1]
        sb_prev = f'<a href="/dict/{pt["slug"]}/">{pt.get("emoji","📖")} {escape_html(pt["term"])}</a>'
    if index < len(all_terms) - 1:
        nt = all_terms[index + 1]
        sb_next = f'<a href="/dict/{nt["slug"]}/">{nt.get("emoji","📖")} {escape_html(nt["term"])}</a>'
    sidebar_html = f'''<aside class="dict-detail-sidebar">
        <div class="dict-quick-facts">
            <h4>快速参考</h4>
            <div class="dict-fact-item">
                <div class="dict-fact-label">英文名</div>
                <div class="dict-fact-value">{escape_html(en_name)}</div>
            </div>
            <div class="dict-fact-item">
                <div class="dict-fact-label">分类</div>
                <div class="dict-fact-value">{escape_html(category)}</div>
            </div>
            <div class="dict-fact-item">
                <div class="dict-fact-label">标签</div>
                <div class="dict-fact-value">{', '.join(escape_html(t) for t in tags)}</div>
            </div>
        </div>
        <div class="dict-side-nav">
            <h4>浏览词条</h4>
            <div class="dict-side-nav-links">
                {sb_prev}
                <a href="/dict/">📖 返回词典首页</a>
                {sb_next}
            </div>
        </div>
    </aside>'''

    # 相关词条（同分类的其他词条，最多6个）
    same_category = [t for t in all_terms if t.get('category') == category and t['slug'] != slug][:6]
    related_html = ''
    if same_category:
        related_cards = ''.join([
            f'<a class="dict-related-card" href="/dict/{t["slug"]}/"><span class="dict-related-emoji">{t.get("emoji","📖")}</span>{escape_html(t["term"])}</a>'
            for t in same_category
        ])
        related_html = f'''        <div class="dict-related">
            <h3>同分类词条</h3>
            <div class="dict-related-grid">
                {related_cards}
            </div>
        </div>'''

    # 底部导航
    prev_link = ''
    next_link = ''
    if index > 0:
        prev_term = all_terms[index - 1]
        prev_link = f'<a href="/dict/{prev_term["slug"]}/">← {escape_html(prev_term["term"])}</a>'
    if index < len(all_terms) - 1:
        next_term = all_terms[index + 1]
        next_link = f'<a href="/dict/{next_term["slug"]}/">{escape_html(next_term["term"])} →</a>'

    title = f'{term_name} - AI词典 - AI工具宝箱'
    description = brief[:150]
    # 2026-08-06：brief 过短时，从 detail（markdown）正文提取真实内容补足，消除 Bing 过短警告
    # 2026-08-13（阶段2.3）：阈值 90 → 115，覆盖 90~114 字的词条描述
    if len(description) < 115 and detail:
        _plain = re.sub(r'<[^>]+>', '', detail)
        _plain = re.sub(r'^#{1,6}[^\n]*$', '', _plain, flags=re.M)
        _plain = re.sub(r'[*_`>|#]', '', _plain)
        _plain = re.sub(r'\s+', '', _plain).strip('：:。.，,；;')
        if _plain and _plain not in description:
            _sep = '' if description.endswith(('。', '！', '？')) else '。'
            description = (description + _sep + _plain)[:160]
        elif _plain:
            description = _plain[:160]
    # 2026-08-13（阶段2.3）：仍不足 115 字时追加词条定位说明
    if len(description) < 115:
        description += '。本词条收录于AI工具宝箱AI词典，附英文对照与关联工具，供AI初学者快速查阅。'
    canonical = f'https://www.aitoollab.cn/dict/{slug}/'
    og_image = ensure_og_image(f'dict-{slug}', {'term': term_name, 'emoji': emoji, 'brief': brief, 'category': category or 'AI词典', 'en': en_name}, is_dict=True)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <meta name="description" content="{escape_html(description)}">
    <meta name="keywords" content="{escape_html(term_name)},AI词典,AI术语,人工智能概念,{escape_html(en_name)}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(description)}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    {f'<meta property="og:image" content="{og_image}">' if og_image else ''}
    <meta name="twitter:card" content="summary_large_image">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <!-- BUILD_DYNAMIC_HEAD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "DefinedTerm",
      "name": "{escape_html(term_name)}",
      "description": "{escape_html(brief)}",
      "inDefinedTermSet": {{
        "@type": "DefinedTermSet",
        "name": "AI工具宝箱 - AI词典"
      }}
    }}
    </script>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;">
                <div class="site-logo">🛠 AI工具宝箱 <span>每日更新 · 已收录 {TOOL_COUNT} 款工具</span></div>
            </a>
        </div>
        <nav class="global-nav" aria-label="全局导航">
            <div class="global-nav-inner">
                <a href="/ranking/" class="gn-item">📊 工具排行</a>
                <a href="/quiz/" class="gn-item">🎯 AI工具选择器</a>
                <a href="/live/" class="gn-item">📈 实时面板</a>
                <a href="/compare/" class="gn-item">⚖️ 对比评测</a>
                <a href="/alternatives/" class="gn-item">🔄 替代方案</a>
                <a href="/category/" class="gn-item">📂 全部分类</a>
            </div>
        </nav>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <div class="breadcrumb-inner">
            <a href="/">首页</a>
            <span class="sep">›</span>
            <a href="/dict/">AI词典</a>
            <span class="sep">›</span>
            <span>{escape_html(term_name)}</span>
        </div>
    </nav>

    <main class="dict-detail-page">
        <header class="dict-detail-header">
            <div class="dict-detail-icon">{emoji}</div>
            <h1>{escape_html(term_name)}</h1>
            <div class="dict-detail-en">{escape_html(en_name)}</div>
            {category_html}
            <div class="dict-detail-tags">{tags_html}</div>
        </header>
        <div class="dict-detail-layout">
            <div class="dict-detail-main">
                <article>
                    <div class="dict-detail-body">
                        {detail_html}
                    </div>
                </article>
            </div>
            {sidebar_html}
        </div>
        <nav class="dict-detail-nav">
            {prev_link}
            {next_link}
        </nav>
        {related_html}
    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p>
        <div class="footer-links">
            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
        </div>
        <p>用AI提升效率，让每个人都能享受技术红利。</p>
    </footer>
    {BACK_TO_TOP_BLOCK}
</body>
</html>'''
    return html

def _build_dict_index_page(terms):
    """生成AI词典总入口页 /dict/index.html"""
    # 按分类分组
    categories = {}
    for term in terms:
        cat = term.get('category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(term)

    # 分类顺序
    cat_order = ['基础概念', '技术原理', '使用技巧', '基础设施', '前沿概念']
    ordered_cats = [c for c in cat_order if c in categories]
    for c in categories:
        if c not in ordered_cats:
            ordered_cats.append(c)

    sections_html = ''
    for cat in ordered_cats:
        cat_terms = categories[cat]
        cards = ''
        for term in cat_terms:
            cards += f'''                    <a class="dict-list-card" href="/dict/{term['slug']}/">
                        <div class="dict-list-icon">{term.get('emoji', '📖')}</div>
                        <div class="dict-list-body">
                            <h4>{escape_html(term['term'])}</h4>
                            <p>{escape_html(term.get('brief', ''))}</p>
                            <div class="dict-list-en">{escape_html(term.get('en', ''))}</div>
                        </div>
                    </a>
'''
        sections_html += f'''            <section class="dict-category-section">
                <h2 class="dict-category-title">{escape_html(cat)}</h2>
                <div class="dict-list-items">
{cards}                </div>
            </section>
'''

    title = 'AI词典 - AI术语大全 - AI工具宝箱'
    description = (f'AI工具宝箱AI词典：涵盖{len(terms)}个核心人工智能概念，从大语言模型、RAG、Agent、'
                   f'Transformer到微调、向量数据库、多模态，每个术语附通俗解释、英文对照与关联工具，'
                   f'并关联对应AI工具与常见问答，帮你零基础看懂AI技术名词，适合初学者、开发者和产品经理查阅。')
    canonical = 'https://www.aitoollab.cn/dict/'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <meta name="description" content="{escape_html(description)}">
    <meta name="keywords" content="AI词典,人工智能术语,机器学习概念,深度学习术语,大模型术语,AI基础知识">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(description)}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{canonical}">
    <style>{CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={CSS_VERSION}"></noscript>
    <!-- BUILD_DYNAMIC_HEAD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "DefinedTermSet",
      "name": "AI工具宝箱 - AI词典",
      "description": "{escape_html(description)}"
    }}
    </script>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;">
                <div class="site-logo">🛠 AI工具宝箱 <span>每日更新 · 已收录 {TOOL_COUNT} 款工具</span></div>
            </a>
        </div>
        <nav class="global-nav" aria-label="全局导航">
            <div class="global-nav-inner">
                <a href="/ranking/" class="gn-item">📊 工具排行</a>
                <a href="/quiz/" class="gn-item">🎯 AI工具选择器</a>
                <a href="/live/" class="gn-item">📈 实时面板</a>
                <a href="/compare/" class="gn-item">⚖️ 对比评测</a>
                <a href="/alternatives/" class="gn-item">🔄 替代方案</a>
                <a href="/category/" class="gn-item">📂 全部分类</a>
            </div>
        </nav>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <div class="breadcrumb-inner">
            <a href="/">首页</a>
            <span class="sep">›</span>
            <span>AI词典</span>
        </div>
    </nav>

    <main class="dict-list-page">
        <header class="dict-list-header">
            <h1>📖 AI 词典</h1>
            <p>{len(terms)} 个核心AI概念，从入门到精通，一文读懂人工智能</p>
        </header>
{sections_html}    </main>

    <footer class="footer">
        <p>© {BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {ICP_BEIAN}</p>
        <div class="footer-links">
            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
        </div>
        <p>用AI提升效率，让每个人都能享受技术红利。</p>
    </footer>
    {BACK_TO_TOP_BLOCK}
</body>
</html>'''
    return html

def generate_sitemap(tools, articles, categories, compares=None, alternatives=None, quizzes=None, rankings=None, lives=None, dict_terms=None, news_urls=None):
    """生成 sitemap.xml"""
    from datetime import datetime, timedelta
    import re as _re_sm
    today = datetime.now().strftime('%Y-%m-%d')

    def _tool_lastmod(tool):
        v = tool.get('dateModified', tool.get('date_modified', tool.get('last_updated', '')))
        if v:
            return str(v)[:10]
        if tool.get('created_date'):
            try:
                cd = datetime.strptime(str(tool['created_date'])[:10], '%Y-%m-%d')
                return cd.strftime('%Y-%m-%d')
            except Exception:
                pass
        return today

    def _article_lastmod(article):
        d = article.get('dateModified', article.get('dateFull', article.get('date', '')))
        m = _re_sm.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
        if m:
            return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        m2 = _re_sm.match(r'^(\d{4}-\d{2}-\d{2})', str(d))
        return m2.group(1) if m2 else today

    urls = []

    # 首页
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>''')

    # 全部AI工具大全页 /tools/（SEO+GEO 总入口）
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/tools/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # 注意：不在sitemap中加入文章分页URL（/articles/page/N/），避免浪费爬虫预算
    # 分页通过页面上的 rel=next/prev 让爬虫自然发现即可

    # 工具页
    for tool in tools:
        priority = '0.9' if tool.get('badge') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/tools/{tool['slug']}/</loc>
        <lastmod>{_tool_lastmod(tool)}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{priority}</priority>
        </url>''')

    # 文章页
    for article in articles:
        priority = '0.9' if '2026' in article.get('title', '') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/articles/{article['slug']}/</loc>
        <lastmod>{_article_lastmod(article)}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>{priority}</priority>
    </url>''')

    # 文章内容分类页（2026-08-08：评测/教程/分析 3 个分类枢纽页）
    for _cp in ARTICLE_CATEGORY_PAGES:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/articles/{_cp['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')
    
    # 分类枢纽页 /category/（SEO+GEO 2026-08-03：此前遗漏，导致枢纽页仅靠全局导航被发现）
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # 各栏目总入口页（2026-08-13：Bing 报"网站地图中缺少重要页面"，补齐枢纽页）
    # 2026-08-17：补上 /news/ 枢纽页（快讯为站内最大流量板块，check_closed_loop 门禁要求）
    # 2026-08-23 修复：补 /quiz/ 与 /dict/ 枢纽页——check_closed_loop 门禁
    # 要求 hubs 含这两项，但此处遗漏导致 sitemap 缺 loc，门禁 FAIL 阻断部署。
    for _hub, _prio in (("/ranking/", "0.9"), ("/compare/", "0.8"), ("/alternatives/", "0.8"),
                        ("/articles/", "0.8"), ("/author/", "0.6"), ("/live/", "0.7"),
                        ("/news/", "0.9"), ("/quiz/", "0.8"), ("/dict/", "0.8")):
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn{_hub}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{_prio}</priority>
    </url>''')

    # 分类页（categories 参数已经是经过 get_category_slug 处理的 slug 列表）
    for category_name in categories:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/{category_name}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # 子类目页（独立SEO入口）
    _subdef = get_subcat_def()
    for _parent_slug, _pdata in _subdef.items():
        for _sub_slug, _sdata in _pdata.get('subcats', {}).items():
            urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/{_sub_slug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>''')

    # 对比页 (Phase 2)
    if compares:
        for cp in compares:
            cslug = cp.get('slug', '')
            if cslug:
                prio = '0.9' if cp.get('priority') == 'high' else '0.8'
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/compare/{cslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{prio}</priority>
    </url>''')

    # 替代方案页 (Phase 3)
    if alternatives:
        for alt in alternatives:
            aslug = alt.get('slug', '')
            if aslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/alternatives/{aslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # Quiz 选择器页 (Phase 4)
    if quizzes:
        for qd in quizzes:
            qslug = qd.get('slug', '')
            if qslug:
                is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
                loc = f'/' if is_main else f'/{qslug}/'
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/quiz{loc}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.9</priority>
    </url>''')

    # Ranking 排名页 (Phase 5)
    if rankings:
        for rd in rankings:
            rslug = rd.get('slug', '')
            if rslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/ranking/{rslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # Live Dashboard 页 (Phase 5b)
    if lives:
        for lp in lives:
            lslug = lp.get('slug', '')
            if lslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/live/{lslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # AI词典页
    if dict_terms:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/dict/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')
        for term in dict_terms:
            urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/dict/{term['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>''')

    # 快讯页（每日更新，changefreq=daily）
    if news_urls:
        for nu in news_urls:
            urls.append(f'''    <url>
        <loc>{nu}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>''')

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

    return sitemap

def _urlopen_bounded(req, timeout, label="request"):
    """urlopen with a HARD wall-clock timeout that ALSO covers DNS resolution.

    urllib.request.urlopen(req, timeout=N) 的 timeout 只约束「建连/读取」阶段，
    不约束 DNS 解析(getaddrinfo)。在 VPN/沙箱网络中，若 api.indexnow.org 等
    外部域名 DNS 丢包且无 RST，getaddrinfo 会无限阻塞，N 秒形同虚设，导致
    build.py / publish 流水线卡死。用 daemon 线程 + join(timeout) 把整个
    操作(含 DNS)硬上限到 timeout+2 秒，超时即放弃，绝不阻塞构建。
    """
    import threading
    import urllib.request
    box = {}
    def _run():
        try:
            box['resp'] = urllib.request.urlopen(req, timeout=timeout)
        except Exception as e:
            box['err'] = e
    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(timeout + 2)  # 墙钟硬上限，覆盖 DNS 挂死
    if th.is_alive():
        print(f"[{label}] Timeout (incl. DNS), skipped to avoid blocking build.")
        return None
    if 'err' in box:
        raise box['err']
    return box['resp']

# 中文站 IndexNow key（与 Bing Webmaster Tools 验证文件 {KEY}.txt 一致）
# 模块级统一常量，全量推送(push_to_indexnow)与增量单URL推送(_push_single_url)共用，避免硬编码漂移
INDEXNOW_KEY = "e66c6b3965b6490abd7bee1521893b1b"

def push_to_indexnow(urls):
    """通过 IndexNow 协议向 Bing/Yandex 等搜索引擎推送新链接"""
    import urllib.request
    import urllib.error
    import json as _json

    KEY = INDEXNOW_KEY
    api_url = "https://api.indexnow.org/indexnow"

    payload = _json.dumps({
        "host": "www.aitoollab.cn",
        "key": KEY,
        "keyLocation": f"https://www.aitoollab.cn/{KEY}.txt",
        "urlList": urls[:10000]  # IndexNow 单次上限 10000 条
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        resp = _urlopen_bounded(req, 15, "IndexNow")
        if resp is None:
            return False
        with resp:
            print(f"[IndexNow] Success: HTTP {resp.status}, pushed {len(urls)} URLs")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[IndexNow] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[IndexNow] Failed: {e}")
        return False

def push_to_baidu(urls):
    """主动向百度搜索引擎推送链接

    修复1: site参数必须是纯域名(www.aitoollab.cn)，不能带 http(s)://，否则百度token校验失败、推送全部无效。
    修复2: 百度返回 success/remain 字段，当 remain==0 时说明当日配额耗尽，必须 return False 不更新缓存，
           否则未收录的URL会被误标记为已推送、永不重推。分批推送避免一次性砸光配额。
    """
    if not BAIDU_PUSH_TOKEN:
        print("[Baidu Push] 跳过: 未配置 BAIDU_PUSH_TOKEN")
        return False
    # 关键修复：剥离协议头，得到纯域名
    baidu_site = SITE_DOMAIN.replace('https://', '').replace('http://', '').rstrip('/')
    api_url = f"http://data.zz.baidu.com/urls?site={baidu_site}&token={BAIDU_PUSH_TOKEN}"

    try:
        import urllib.request
        import urllib.error
        import json as _json
        batch_size = 500
        total_success = 0
        for i in range(0, len(urls), batch_size):
            chunk = urls[i:i + batch_size]
            data = '\n'.join(chunk).encode('utf-8')
            req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'text/plain'})
            try:
                response = _urlopen_bounded(req, 15, "Baidu Push")
                if response is None:
                    return False
                with response:
                    result = response.read().decode('utf-8')
                    print(f"[Baidu Push] batch {i // batch_size + 1} Success: {result}")
                    try:
                        rj = _json.loads(result)
                        total_success += rj.get('success', len(chunk))
                        if rj.get('remain', 1) == 0 or rj.get('success', 0) == 0:
                            print("[Baidu Push] 当日配额耗尽(remain=0)，停止推送，剩余URL留待次日重试")
                            return False
                    except Exception:
                        total_success += len(chunk)
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                print(f"[Baidu Push] HTTP {e.code}: {body}")
                return False
    except Exception as e:
        print(f"[Baidu Push] Failed: {e}")
        return False
    return total_success > 0

def _push_single_url(url):
    """增量构建时推送单个新URL到百度和IndexNow"""
    import urllib.request, urllib.error

    # 百度推送（修复：site参数剥离协议头，必须为纯域名）
    if BAIDU_PUSH_TOKEN:
        baidu_site = SITE_DOMAIN.replace('https://', '').replace('http://', '').rstrip('/')
        baidu_api = f"http://data.zz.baidu.com/urls?site={baidu_site}&token={BAIDU_PUSH_TOKEN}"
    try:
        data = url.encode('utf-8')
        req = urllib.request.Request(baidu_api, data=data, headers={'Content-Type': 'text/plain'})
        resp = _urlopen_bounded(req, 10, "Baidu Push")
        if resp is not None:
            with resp:
                print(f'[Baidu Push] {resp.read().decode("utf-8", errors="replace")}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'[Baidu Push] HTTP {e.code}: {body}')
    except Exception as e:
        print(f'[Baidu Push] Failed: {e}')

    # IndexNow推送
    try:
        indexnow_url = "https://api.indexnow.org/indexnow"
        payload = json.dumps({"host": "www.aitoollab.cn", "key": INDEXNOW_KEY, "urlList": [url]}).encode('utf-8')
        req = urllib.request.Request(indexnow_url, data=payload, headers={'Content-Type': 'application/json'})
        resp = _urlopen_bounded(req, 10, "IndexNow")
        if resp is not None:
            with resp:
                print(f'[IndexNow] HTTP {resp.status}, pushed 1 URL')
    except Exception as e:
        print(f'[IndexNow] Failed: {e}')

def _load_dict_terms():
    """加载AI词典数据"""
    dict_data_path = os.path.join(DATA_DIR, 'dict_terms.json')
    if os.path.exists(dict_data_path):
        with open(dict_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ── AI 应答前缀拦截（2026-08-02）───────────────────────────────
# 背景：内容生成时若把"对 prompt 作者的应答/汇报/思考"误写入 content 开头，
#      会污染线上页面（如 deepclaude 页曾出现"好的，没问题。这是一篇符合你所有要求的介绍文章…"）。
# 策略：构建时 fail-fast —— 已发布内容命中即报错中止，脏内容绝不进线上；
#      未发布内容命中仅告警（不阻断），提醒修复。
# 一键修复脚本：scripts/clean_content_preamble.py
_AI_PREAMBLE_PATTERNS = [
    r'^好的，没问题',
    r'^好的，我(?:来|会|将|现在|们|就)',
    r'^当然可以',
    r'^这是一篇符合你',
    r'^这是一篇(?:为您|为你)',
    r'^已为您生成',
    r'^为您撰写',
    r'^根据您的要求',
    r'^让我为您',
    r'^我来为你',
    r'^您好，我(?:是|来|为)',
    r'^很高兴(?:为您|为你)',
    r'^没问题，这是',
    r'^请查收',
    r'^以下是我(?:为您|为你)',
    r'^按照您的要求',
    r'^遵照您的(?:要求|指示)',
    r'^应您的要求',
]
_AI_PREAMBLE_RE = [re.compile(p) for p in _AI_PREAMBLE_PATTERNS]

def _check_content_preamble(all_tools, articles):
    """构建前校验正文开头是否混入 AI 应答前缀。已发布命中→exit(1)，未发布命中→告警。"""
    published_hits, draft_hits = [], []
    def _test(kind, name, content, published):
        if not isinstance(content, str) or not content:
            return
        for pat, cre in zip(_AI_PREAMBLE_PATTERNS, _AI_PREAMBLE_RE):
            if cre.match(content):
                (published_hits if published else draft_hits).append(
                    (kind, name, pat, content[:50]))
                break
    for t in all_tools:
        if not isinstance(t, dict):
            continue
        _test('tool', t.get('slug', '?'), t.get('content', ''), bool(t.get('published')))
    for a in articles:
        if not isinstance(a, dict):
            continue
        _test('article', a.get('slug') or a.get('title', '?'), a.get('content', ''),
              bool(a.get('published', True)))
    if draft_hits:
        print(f'\n⚠️ [内容前缀校验] 发现 {len(draft_hits)} 个未发布内容存在 AI 应答前缀（不阻断，建议修复）：')
        for kind, name, pat, head in draft_hits:
            print(f'   - [{kind}] {name}  命中: {pat}')
    if published_hits:
        print(f'\n❌ [内容前缀校验] 检测到 {len(published_hits)} 个已发布内容混入 AI 应答前缀，构建已中止！')
        print('   请先运行修复脚本，再重新构建：')
        print('       python scripts/clean_content_preamble.py')
        print('   命中详情：')
        for kind, name, pat, head in published_hits:
            print(f'   - [{kind}] {name}  命中模式: {pat}')
            print(f'       内容头部: {head!r}')
        print()
        sys.exit(1)
    pub_count = len([t for t in all_tools if isinstance(t, dict) and t.get('published')])
    print(f'✅ 内容前缀校验通过（{pub_count} 已发布工具 + {len(articles)} 文章，'
          f'未发布告警 {len(draft_hits)}）')

def _build_tool_incremental(tool, published_tools, articles, tools_by_category):
    """工具页 slug 增量：只重建该工具页 + 受影响聚合页（分类/全部工具/首页含搜索索引/排行）。
    不调用全站后处理注入（模板已自带 logo/nav/pwa/ads 标记），保证'用哪建哪'且不污染其他页。"""
    slug = tool['slug']
    print(f'\n[增量构建] 仅构建工具: {tool.get("name")} ({slug})')
    # 交叉链接所需辅助数据
    compare_data = load_compare_data()
    all_compares = compare_data.get('compares', [])
    all_alternatives = compare_data.get('alternatives', [])
    ranking_data = load_ranking_data()
    all_rankings = ranking_data.get('rankings', [])
    # 1. 该工具页
    _emit(os.path.join(BASE_DIR, 'tools', slug, 'index.html'),
          build_tool_page(tool, published_tools, articles, all_compares, all_alternatives, all_rankings))
    print(f'[OK] tools/{slug}/index.html')
    # 2. 该分类页
    cat = tool.get('category')
    if cat and cat in tools_by_category:
        cslug = get_category_slug(cat)
        _emit(os.path.join(BASE_DIR, 'category', cslug, 'index.html'),
              build_category_page(cat, tools_by_category[cat], all_categories=tools_by_category))
        print(f'[OK] category/{cslug}/index.html')
    # 3. 全部工具大全页
    _emit(os.path.join(BASE_DIR, 'tools', 'index.html'), build_tools_index_page(published_tools))
    print(f'[OK] tools/index.html')
    # 4. 首页（同时重建搜索索引 js/tools-data.js）
    _emit(os.path.join(BASE_DIR, 'index.html'), build_index_page(published_tools, articles))
    print(f'[OK] index.html (含搜索索引)')
    # 5. 排行页（数量少，全量重建保证一致）
    for rd in all_rankings:
        rslug = rd.get('slug', 'unknown')
        _emit(os.path.join(BASE_DIR, 'ranking', rslug, 'index.html'),
              build_ranking_page(rd, published_tools, articles))
    try:
        _emit(os.path.join(BASE_DIR, 'ranking', 'index.html'), _build_ranking_index_page(all_rankings))
    except Exception as e:
        print(f'  [FAIL] ranking/index.html: {e}')
    print(f'[OK] ranking/* ({len(all_rankings)} 页)')
    # 6. sitemap 增量推送该工具 URL
    _push_single_url(f'https://www.aitoollab.cn/tools/{slug}/index.html')
    print(f'\n[完成] 增量构建: 1 工具页 + 分类页 + 聚合页')
    return True

def build_target(target, slug=None, no_push=False):
    """
    构建指定目标或全部页面。
    target: 'all' | 'articles' | 'tools' | 'live' | 'sitemap' | 'index' | 'pseo' | 'ranking'
    slug: 指定文章slug，仅构建该文章页+列表页+sitemap（增量构建模式）
    """
    # 加载数据（目录优先，回退单体）
    all_tools = load_tools()
    # 填充 slug->name 映射，供标题引擎对比意图取竞品名
    _SLUG_MAP.clear()
    _SLUG_MAP.update({t['slug']: t for t in all_tools if t.get('slug')})
    articles = load_articles()
    # AI 应答前缀拦截（fail-fast）：脏内容绝不进线上
    _check_content_preamble(all_tools, articles)
    # 按日期降序排列（最新文章在前），date格式兼容 "MM/DD" 和 "YYYY-MM-DD"
    def _article_date_key(a):
        d = a.get('date', '')
        try:
            if '-' in d and len(d) == 10:
                # YYYY-MM-DD 格式
                parts = d.split('-')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            elif '/' in d:
                # MM/DD 格式
                parts = d.split('/')
                return (2026, int(parts[0]), int(parts[1]))  # MM/DD格式默认2026年
            return (0, 0, 0)
        except:
            return (0, 0, 0)
    articles.sort(key=_article_date_key, reverse=True)
    # 新文章自动归类（2026-08-08）：缺失 content_type 时补齐并落盘，新增文章无需手工维护
    ensure_article_content_types(articles)
    # 生成全站快讯 RSS（/rss.xml）
    generate_rss(articles)

    # 过滤出已发布的工具
    published_tools = [tool for tool in all_tools if tool.get('published', False)]# === AI-NEWS-DATA-BEGIN ===
    # 快讯数据加载
    import glob as _gb_ns
    _ns_daily = {}
    for _fp in sorted(_gb_ns.glob(os.path.join(BASE_DIR, "data", "news_*.json")), reverse=True):
        try:
            _dstr = os.path.basename(_fp).replace("news_", "").replace(".json", "")
            _ns_daily[_dstr] = json.load(open(_fp, "r", encoding="utf-8"))
        except Exception:
            continue
# === AI-NEWS-DATA-END ===
    # 快讯数据加载
    import glob as _gb_ns
    _ns_daily = {}
    for _fp in sorted(_gb_ns.glob(os.path.join(BASE_DIR, "data", "news_*.json")), reverse=True):
        try:
            _dstr = os.path.basename(_fp).replace("news_", "").replace(".json", "")
            _ns_daily[_dstr] = json.load(open(_fp, "r", encoding="utf-8"))
        except Exception:
            continue

    print(f"检测到 {len(all_tools)} 个工具，其中 {len(published_tools)} 个已发布。")

    # ── 全站动态常量（P0：入口计算一次，全站各模板引用）──
    global TOOL_COUNT, CAT_COUNT, ART_COUNT
    TOOL_COUNT = len(published_tools)
    CAT_COUNT  = len({t.get('category') for t in published_tools if t.get('category')})
    ART_COUNT  = len(articles)
    print(f"动态常量：TOOL_COUNT={TOOL_COUNT}, CAT_COUNT={CAT_COUNT}, ART_COUNT={ART_COUNT}, BUILD_YEAR={BUILD_YEAR}")

    # 按分类分组工具（增量构建也需要）
    tools_by_category = {}
    for tool in published_tools:
        category = tool.get('category')
        if category:
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)

    # ═══════════════════════════════════════════════════════
    # 增量构建模式：只构建指定slug的文章
    # ═══════════════════════════════════════════════════════
    if slug:
        target_article = next((a for a in articles if a['slug'] == slug), None)
        if not target_article:
            # 工具页 slug 增量：改一个工具只重建它 + 受影响聚合页（用哪建哪）
            target_tool = next((t for t in published_tools if t['slug'] == slug), None)
            if target_tool:
                return _build_tool_incremental(target_tool, published_tools, articles, tools_by_category)
            print(f'[ERROR] 未找到文章或工具: {slug}')
            return False
        print(f'\n[增量构建] 仅构建文章: {target_article["title"]}')
        dir_path = os.path.join(BASE_DIR, 'articles', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_article_page(target_article, articles, published_tools)
        _emit(os.path.join(dir_path, 'index.html'), html)
        try:
            import re as _re
            md_text = f"# {target_article.get('title', '')}\n\n" + target_article.get('content', '')
            md_text = _re.sub(r'<[^>]+>', ' ', md_text)
            with open(os.path.join(dir_path, f"{slug}.md"), 'w', encoding='utf-8') as f:
                f.write(md_text)
        except:
            pass
        print(f'[OK] articles/{slug}/index.html')

        # 更新文章分页列表页
        total_pages = build_article_list_pages(articles)
        print(f'[OK] 文章列表页已更新 ({total_pages} 页)')
        build_article_category_pages(articles)

        # 后处理：注入全局导航
        inject_global_nav()
        inject_site_logo()
        inject_footer_links()
        inject_pwa()
        inject_favicon()
        inject_hreflang()
        inject_adsense_meta()
        inject_baidu_tongji()
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()], dict_terms=dict_terms)
        with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(sitemap)
        print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles)')

        # 推送新URL到百度和IndexNow
        _push_single_url(f'https://www.aitoollab.cn/articles/{slug}/index.html')

        print(f'\n[完成] 增量构建: 1篇文章 + 列表页 + sitemap')
        return True

    # 加载所有辅助数据（后续推送和sitemap需要）
    compare_data = load_compare_data()
    all_compares = compare_data.get('compares', [])
    all_alternatives = compare_data.get('alternatives', [])
    quiz_data = load_quiz_data()
    all_quizzes = quiz_data.get('quizzes', [])
    ranking_data = load_ranking_data()
    all_rankings = ranking_data.get('rankings', [])
    live_data = load_live_data()
    all_lives = live_data.get('live_pages', [])

    compare_count = 0
    alt_count = 0
    quiz_count = 0
    ranking_count = 0
    live_count = 0
    total_pages = 0

    # ═══════════════════════════════════════════════════════
    # 分类页（index 时生成，或 all 时生成）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'index', 'tools'):
        for category_name, tools_in_category in tools_by_category.items():
            try:
                category_slug = get_category_slug(category_name)
                dir_path = os.path.join(BASE_DIR, 'category', category_slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_category_page(category_name, tools_in_category, all_categories=tools_by_category)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] category/{category_slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单分类页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] category/{category_name}/: {e}')
                _record_build_error('category', category_name, str(e))

        # 子类目独立页（扁平URL，独立SEO入口）；按 subcategory 字段过滤
        _subdef = get_subcat_def()
        if _subdef:
            _flat_tools = [t for ts in tools_by_category.values() for t in ts]
            for _parent_slug, _pdata in _subdef.items():
                _parent_name = _pdata.get('name', _parent_slug)
                for _sub_slug, _sdata in _pdata.get('subcats', {}).items():
                    _sub_tools = [t for t in _flat_tools if t.get('subcategory') == _sub_slug]
                    if not _sub_tools:
                        continue
                    _sub_dir = os.path.join(BASE_DIR, 'category', _sub_slug)
                    os.makedirs(_sub_dir, exist_ok=True)
                    _parent_count = len([t for t in _flat_tools if t.get('category') == _parent_name])
                    _html = build_subcategory_page(_parent_slug, _parent_name, _sub_slug, _sdata, _sub_tools, parent_count=_parent_count)
                    _emit(os.path.join(_sub_dir, 'index.html'), _html)
                    print(f'[OK] category/{_sub_slug}/index.html (子类目, {len(_sub_tools)}款)')

        # 生成 category/index.html 总入口页（列出所有分类）
        try:
            cat_index_html = _build_category_index_page(tools_by_category)
            _emit(os.path.join(BASE_DIR, 'category', 'index.html'), cat_index_html)
            print('  [OK] category/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] category/index.html: {e}')

        # 生成 tools/index.html 全部AI工具大全页（SEO+GEO 总入口）
        try:
            tools_index_html = build_tools_index_page(published_tools)
            _emit(os.path.join(BASE_DIR, 'tools', 'index.html'), tools_index_html)
            print(f'  [OK] tools/index.html (全部AI工具大全, {len(published_tools)}款)')
        except Exception as e:
            print(f'  [FAIL] tools/index.html: {e}')

    # ═══════════════════════════════════════════════════════
    # 工具页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'tools'):
        for tool in published_tools:
            slug = tool['slug']
            try:
                dir_path = os.path.join(BASE_DIR, 'tools', slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_tool_page(tool, published_tools, articles, all_compares, all_alternatives, all_rankings)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] tools/{slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单工具页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] tools/{slug}/: {e}')
                _record_build_error('tool', slug, str(e))

    # ═══════════════════════════════════════════════════════
    # 文章页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'articles'):
        for article in articles:
            slug = article['slug']
            try:
                dir_path = os.path.join(BASE_DIR, 'articles', slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_article_page(article, articles, published_tools)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单文章页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] articles/{slug}/: {e}')
                _record_build_error('article', slug, str(e))

        # 文章分页列表页
        total_pages = build_article_list_pages(articles)
        build_article_category_pages(articles)

    # ═══════════════════════════════════════════════════════
    # Phase 2+3: 对比页和替代方案页（pSEO）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'pseo'):
        if all_compares:
            print(f'\n[Phase2] Generating compare pages ({len(all_compares)})...')
            for cp in all_compares:
                cslug = cp.get('slug', 'unknown')
                dir_path = os.path.join(BASE_DIR, 'compare', cslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_compare_page(cp, published_tools, articles,
                                              existing_compare_slugs={c.get('slug') for c in all_compares})
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    print(f'  [OK] compare/{cslug}/index.html')
                    compare_count += 1
                except Exception as e:
                    print(f'  [FAIL] compare/{cslug}/: {e}')

        if all_alternatives:
            print(f'\n[Phase3] Generating alternatives pages ({len(all_alternatives)})...')
            for alt in all_alternatives:
                aslug = alt.get('slug', 'unknown')
                dir_path = os.path.join(BASE_DIR, 'alternatives', aslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_alternatives_page(alt, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    print(f'  [OK] alternatives/{aslug}/index.html')
                    alt_count += 1
                except Exception as e:
                    print(f'  [FAIL] alternatives/{aslug}/: {e}')

        # 生成 compare/index.html 总入口页
        try:
            compare_index_html = _build_compare_index_page(all_compares)
            _emit(os.path.join(BASE_DIR, 'compare', 'index.html'), compare_index_html)
            print('  [OK] compare/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] compare/index.html: {e}')

        # 生成 alternatives/index.html 总入口页
        try:
            alt_index_html = _build_alternatives_index_page(all_alternatives)
            _emit(os.path.join(BASE_DIR, 'alternatives', 'index.html'), alt_index_html)
            print('  [OK] alternatives/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] alternatives/index.html: {e}')

        # Quiz
        if all_quizzes:
            print(f'\n[Phase4] Generating quiz pages ({len(all_quizzes)})...')
            for qd in all_quizzes:
                qslug = qd.get('slug', 'unknown')
                is_main = qd.get('target_url') == '/quiz/' or qslug == 'ai-tool-finder-2026'
                if is_main:
                    dir_path = os.path.join(BASE_DIR, 'quiz')
                else:
                    dir_path = os.path.join(BASE_DIR, 'quiz', qslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_quiz_page(qd, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                    print(f'  [OK] {loc}index.html')
                    quiz_count += 1
                except Exception as e:
                    loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                    print(f'  [FAIL] {loc}: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 5: Ranking Pages（独立条件，支持 --target ranking）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'ranking', 'pseo'):
        if all_rankings:
            print(f'\n[Phase5] Generating ranking pages ({len(all_rankings)})...')
            for rd in all_rankings:
                rslug = rd.get('slug', 'unknown')
                # 所有ranking统一生成到 ranking/{slug}/ 子目录
                dir_path = os.path.join(BASE_DIR, 'ranking', rslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_ranking_page(rd, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    loc = f'ranking/{rslug}/'
                    print(f'  [OK] {loc}index.html')
                    ranking_count += 1
                except Exception as e:
                    loc = f'ranking/{rslug}/'
                    print(f'  [FAIL] {loc}: {e}')

        # 生成 ranking/index.html 总入口页（跳转到综合榜 + 列出所有榜单）
        try:
            ranking_index_html = _build_ranking_index_page(all_rankings)
            _emit(os.path.join(BASE_DIR, 'ranking', 'index.html'), ranking_index_html)
            print('  [OK] ranking/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] ranking/index.html: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 5b: Live Dashboard
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'live', 'pseo'):
        if all_lives:
            print(f'\n[Phase5b] Generating live dashboard pages ({len(all_lives)})...')
            dashboard_html = None
            for lp in all_lives:
                lslug = lp.get('slug', 'unknown')
                dir_path = os.path.join(BASE_DIR, 'live', lslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_live_page(live_data, lp, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    if lslug == 'dashboard':
                        dashboard_html = html
                    print(f'  [OK] live/{lslug}/index.html')
                    live_count += 1
                except Exception as e:
                    print(f'  [FAIL] live/{lslug}/: {e}')

            if dashboard_html:
                _emit(os.path.join(BASE_DIR, 'live', 'index.html'), dashboard_html)
                print(f'  [OK] live/index.html (dashboard)')

    # ═══════════════════════════════════════════════════════
    # AI词典
    # ═══════════════════════════════════════════════════════

# === AI-NEWS-BUILD-BEGIN ===
    # ===== 快讯页 =====
    news_urls = []
    if target in ("all", "news"):
        news_urls = build_news_page(published_tools)
# === AI-NEWS-BUILD-END ===

    if target in ('all', 'dict'):
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        if dict_terms:
            print(f'\n[Dict] Generating dict pages ({len(dict_terms)} published terms)...')
            # 词典总入口页
            dict_index_html = _build_dict_index_page(dict_terms)
            dir_path = os.path.join(BASE_DIR, 'dict')
            os.makedirs(dir_path, exist_ok=True)
            _emit(os.path.join(dir_path, 'index.html'), dict_index_html)
            print(f'  [OK] dict/index.html (总入口页)')

            # 各词条详情页
            for i, term in enumerate(dict_terms):
                slug = term['slug']
                term_dir = os.path.join(BASE_DIR, 'dict', slug)
                os.makedirs(term_dir, exist_ok=True)
                html = build_dict_page(term, dict_terms, i)
                _emit(os.path.join(term_dir, 'index.html'), html)
                print(f'  [OK] dict/{slug}/index.html')

    # ═══════════════════════════════════════════════════════
    # 静态首页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'index', 'tools'):
        index_html = build_index_page(published_tools, articles)
        _emit(os.path.join(BASE_DIR, 'index.html'), index_html)
        print(f'[OK] index.html (Static Pre-rendered)')

    # 后处理：注入全局导航栏到所有HTML文件
    inject_global_nav()
    # 后处理：全站头部标识统一为新品牌图形（宝箱 + AI 星光）
    inject_site_logo()
    # 后处理：为内页 footer 补上站内链接（P0-5）
    inject_footer_links()
    # 后处理：PWA manifest（P1-5）
    inject_pwa()
    # 后处理：注入静态收藏悬浮按钮（首屏可见，不再等 JS）
    inject_fav_fab()
    # 后处理：注入favicon图标引用
    inject_favicon()
    # 后处理：注入 hreflang 标签（中英文站互链）
    inject_hreflang()
    inject_adsense_meta()
    inject_baidu_tongji()
    # 后处理：全站注入 RSS 声明
    inject_rss_link()
    # 后处理：注入独占板块导航簇（#13 板块互链）
    inject_section_hub()

    # 后处理：全站坏链兜底（2026-08-13：移出"仅推送时执行"分支，任何构建都清理死链）
    _fixed = _clean_all_broken_links()
    if _fixed:
        print(f'[坏链清理] 已修复 {_fixed} 个页面中的坏链')

    # ═══════════════════════════════════════════════════════
    # sitemap + 推送（每次都执行）
    # ═══════════════════════════════════════════════════════
    if target != 'none':  # 2026-08-13：--no-push 也生成 sitemap（本地验证不更新 sitemap 是坑），仅跳过推送
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()],
                                    all_compares, all_alternatives,
                                    all_quizzes,
                                    all_rankings,
                                    all_lives,
                                    dict_terms,
                                    news_urls=news_urls if news_urls else None)
        with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(sitemap)
        print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + {len(tools_by_category)} categories + {total_pages} article pages + {compare_count} compares + {alt_count} alternatives + {quiz_count} quizzes + {ranking_count} rankings + {live_count} live + {len(dict_terms)} dict)')

        # 收集需要推送的链接
        push_cache_file = os.path.join(BASE_DIR, '.baidu_pushed.json')
        pushed_urls = set()
        if os.path.exists(push_cache_file):
            with open(push_cache_file, 'r', encoding='utf-8') as f:
                pushed_urls = set(json.load(f))
        
        all_urls = ["https://www.aitoollab.cn/", "https://www.aitoollab.cn/tools/"]# === AI-NEWS-URL-BEGIN ===
        # 快讯URL加入推送列表
        if news_urls:
            all_urls.extend(news_urls)
# === AI-NEWS-URL-END ===
        for tool in published_tools:
            all_urls.append(f"https://www.aitoollab.cn/tools/{tool['slug']}/")
        for article in articles:
            all_urls.append(f"https://www.aitoollab.cn/articles/{article['slug']}/")
        # 文章内容分类页（2026-08-08）
        for _cp in ARTICLE_CATEGORY_PAGES:
            all_urls.append(f"https://www.aitoollab.cn/articles/{_cp['slug']}/")
        for category_name in tools_by_category.keys():
            category_slug = get_category_slug(category_name)
            all_urls.append(f"https://www.aitoollab.cn/category/{category_slug}/")
        for cp in (all_compares or []):
            cslug = cp.get('slug', '')
            if cslug:
                all_urls.append(f"https://www.aitoollab.cn/compare/{cslug}/")
        for alt in (all_alternatives or []):
            aslug = alt.get('slug', '')
            if aslug:
                all_urls.append(f"https://www.aitoollab.cn/alternatives/{aslug}/")
        for qd in (all_quizzes or []):
            qslug = qd.get('slug', '')
            if qslug:
                is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
                all_urls.append(f"https://www.aitoollab.cn/quiz{'' if is_main else '/' + qslug + '/'}")
        for rd in (all_rankings or []):
            rslug = rd.get('slug', '')
            if rslug:
                all_urls.append(f"https://www.aitoollab.cn/ranking/{rslug}/")
        for lp in (all_lives or []):
            lslug = lp.get('slug', '')
            if lslug:
                all_urls.append(f"https://www.aitoollab.cn/live/{lslug}/")

        # AI词典URL
        if dict_terms:
            all_urls.append("https://www.aitoollab.cn/dict/")
            for term in dict_terms:
                all_urls.append(f"https://www.aitoollab.cn/dict/{term['slug']}/")

        new_urls = [u for u in all_urls if u not in pushed_urls]
        
        if no_push:
            print(f"\n[--no-push] 跳过推送（sitemap 已更新，共 {len(all_urls)} 个 URL）")
        elif new_urls:
            print(f"\nPushing {len(new_urls)} new URLs to Baidu...")
            push_result = push_to_baidu(new_urls)
            if push_result:
                pushed_urls.update(new_urls)
                try:
                    with open(push_cache_file, 'w', encoding='utf-8') as f:
                        json.dump(list(pushed_urls), f)
                except OSError as e:
                    print(f'[WARN] 百度推送缓存写失败（幂等，可忽略）：{e}')
        else:
            print(f"\nNo new URLs to push. ({len(all_urls)} total, all already pushed)")

        # IndexNow 推送
        indexnow_cache_file = os.path.join(BASE_DIR, '.indexnow_pushed.json')
        indexnow_pushed = set()
        if os.path.exists(indexnow_cache_file):
            with open(indexnow_cache_file, 'r', encoding='utf-8') as f:
                indexnow_pushed = set(json.load(f))

        new_indexnow_urls = [u for u in all_urls if u not in indexnow_pushed]
        if no_push:
            pass
        elif new_indexnow_urls:
            print(f"\nPushing {len(new_indexnow_urls)} new URLs via IndexNow (Bing/Yandex)...")
            if push_to_indexnow(new_indexnow_urls):
                indexnow_pushed.update(new_indexnow_urls)
                try:
                    with open(indexnow_cache_file, 'w', encoding='utf-8') as f:
                        json.dump(list(indexnow_pushed), f)
                except OSError as e:
                    print(f'[WARN] IndexNow 缓存写失败（幂等，可忽略）：{e}')
        else:
            print(f"\nIndexNow: No new URLs to push. ({len(all_urls)} total, all already pushed)")
        
        print(f'\nDone! Target={target} | {len(published_tools)} tools + {len(articles)} articles + {quiz_count} quizzes + {ranking_count} rankings + {live_count} live')

# ═══════════════════════════════════════════════════════
# #13 独占板块互链：在快讯/词典/Live/排名/对比/替代/Quiz 等
# 独占板块页底部注入板块导航簇，形成内部链接网络（P0-13）
# ═══════════════════════════════════════════════════════

# 2026-08-24: 全站后处理注入器抽到 build_lib/injectors.py（模块2），此处重导出保持兼容
from build_lib.injectors import (
    _clean_all_broken_links, inject_site_logo, inject_favicon, inject_global_nav,
    inject_fav_fab, inject_footer_links, inject_pwa, inject_adsense_meta,
    inject_baidu_tongji, inject_rss_link, inject_hreflang,
    EXCLUSIVE_SECTIONS, build_section_hub, inject_section_hub,
)

def main():
    # Windows GBK 控制台兜底（2026-08-09 机制化修复）：Python 打印 emoji/中文
    # 不再抛 UnicodeEncodeError。历史反复踩坑，不要删除。
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    # 内部信息泄漏前置检查（2026-08-05：入库模板曾把"收录来源/ai-bot.cn（"写进对外字段，
    # 机制化拦截：构建前扫描 tools.json 对外字段，有违规即中止构建，防止内部溯源泄漏到线上）
    try:
        _leak_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_internal_leak.py')
        # 2026-08-09 修复：Windows 下子进程默认用 GBK 输出，父进程按 utf-8 解码会抛
        # UnicodeDecodeError（reader thread 崩溃），导致守卫误判/构建异常。
        _sub_env = os.environ.copy()
        _sub_env['PYTHONIOENCODING'] = 'utf-8'
        _leak_run = subprocess.run([sys.executable, _leak_script],
                                   capture_output=True, text=True, encoding='utf-8', env=_sub_env)
        # 2026-08-06 修复：区分「真实泄漏(exit 1)」与「检查器自身故障(exit 2 或崩溃)」。
        # 旧逻辑 returncode != 0 一律拦截，且只打印 stdout，导致守卫脚本 traceback(走 stderr)
        # 时拦截信息为空白、每日发布流水线被静默卡死且无法诊断。
        if _leak_run.returncode == 1:
            print('[build][拦截] 内部信息泄漏检查未通过，中止构建：')
            print(_leak_run.stdout or '')
            print(_leak_run.stderr or '')
            raise SystemExit(1)
        elif _leak_run.returncode != 0:
            print(f'[build][警告] 内部信息泄漏检查器自身异常(exit {_leak_run.returncode})，'
                  f'本次跳过检查继续构建，请尽快修复检查器：')
            print(_leak_run.stdout or '')
            print(_leak_run.stderr or '')
    except FileNotFoundError:
        pass  # 检查脚本缺失不阻塞构建
    # 构建前数据校验闸（G3，2026-08-23）：脏数据（缺必填/重复 slug/格式错误）在进渲染前拦下。
    # 与 check_internal_leak 同款子进程模式：ERROR 级（exit 1）中止构建，WARN 级不阻断。
    try:
        _val_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validate_data.py')
        if os.path.isfile(_val_script):
            _val_env = os.environ.copy()
            _val_env['PYTHONIOENCODING'] = 'utf-8'
            _val_run = subprocess.run([sys.executable, _val_script],
                                      capture_output=True, text=True, encoding='utf-8', env=_val_env)
            for _line in (_val_run.stdout or '').strip().splitlines()[-6:]:
                print('[validate]', _line)
            if _val_run.returncode == 1:
                print('[build][拦截] 数据校验未通过，中止构建（请修复 data/*.json 后重试）')
                raise SystemExit(1)
    except FileNotFoundError:
        pass  # 校验脚本缺失不阻塞构建
    parser = argparse.ArgumentParser(description='AI工具宝箱 SSG 构建脚本')
    parser.add_argument('--target', '-t',
                        choices=['all', 'articles', 'tools', 'live', 'pseo', 'ranking', 'index', 'sitemap', 'dict', 'news', 'none'],
                        default='all',
                        help='构建目标（默认 all）：all=全量, articles=仅文章, tools=仅工具, live=仅Live面板, pseo=对比/替代/Quiz/排名/Live, ranking=仅排名, index=首页+分类, sitemap=仅推送, dict=仅AI词典, none=仅构建HTML不推送')
    parser.add_argument('--slug', '-s',
                        type=str, default=None,
                        help='增量构建：仅构建指定slug的文章页+列表页+sitemap')
    parser.add_argument('--no-push',
                        action='store_true',
                        help='只构建 HTML，不推送 sitemap/IndexNow/百度（本地验证用，等价 -t none 但会正常重建页面）')
    args = parser.parse_args()
    build_target(args.target, slug=args.slug, no_push=args.no_push)

    # 2026-08-13 机制化：构建完自动补跑广告/CPS 注入（幂等，重复跑无副作用）。
    # 背景：广告加载器不在模板里，是构建后由 scripts/inject_ads.py 单独注入的；
    # 多个自动化（版本监控/词典/快讯/发文章等）只调 build.py，重建后页面会丢失 loader，
    # 一旦直接上传就把"无广告页面"推上线（2026-08-13 线上事故根因）。
    # 现在 build.py 作为唯一出口，保证任何入口（手动/自动化/deploy）构建完都自动注入。
    try:
        _inj_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inject_ads.py')
        if os.path.isfile(_inj_script):
            _inj_env = os.environ.copy()
            _inj_env['PYTHONIOENCODING'] = 'utf-8'
            _inj_env['PYTHONUTF8'] = '1'
            _inj_run = subprocess.run([sys.executable, _inj_script],
                                      capture_output=True, text=True, encoding='utf-8', env=_inj_env)
            for _line in (_inj_run.stdout or '').strip().splitlines()[-3:]:
                print('[ads]', _line)
            if _inj_run.returncode != 0:
                print('[ads][警告] inject_ads 自动注入异常(exit %d)：' % _inj_run.returncode)
                print((_inj_run.stderr or _inj_run.stdout or '')[-300:])
                # 2026-08-19 兜底：inject_ads 进程被系统终止（曾出现 0xC0000402）时，
                # 正在写入的文件可能被截断为 0 字节。崩溃后立即扫描内容页 0 字节文件，
                # 发现则明确报错并中止构建，防止 0 字节页面带病进入部署链路。
                _zero_files = []
                for _zroot, _zdirs, _zfiles in os.walk(BASE_DIR):
                    _ztop = os.path.relpath(_zroot, BASE_DIR).split(os.sep)[0] if _zroot != BASE_DIR else ''
                    if _ztop and _ztop not in ('tools', 'articles', 'category', 'compare', 'ranking', 'quiz', 'dict', 'news', 'live', 'alternatives'):
                        continue
                    for _zf in _zfiles:
                        if not _zf.endswith('.html'):
                            continue
                        _zp = os.path.join(_zroot, _zf)
                        try:
                            if os.path.getsize(_zp) == 0:
                                _zero_files.append(os.path.relpath(_zp, BASE_DIR))
                        except OSError:
                            pass
                if _zero_files:
                    print('[ads][中止] inject_ads 崩溃后检测到 %d 个 0 字节内容页，中止构建：' % len(_zero_files))
                    for _z in _zero_files[:20]:
                        print('  -', _z)
                    raise SystemExit(1)
    except FileNotFoundError:
        pass  # 注入脚本缺失不阻塞构建

if __name__ == '__main__':
    main()

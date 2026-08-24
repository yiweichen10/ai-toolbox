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

# 类目名 → CSS 变量名 / HEX颜色（Logo光晕版卡片用）

# OG图片自动生成：缺失时自动调用gen_seo_images生成

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

# 已发布工具 slug 集合缓存（坏链清理用）

# ════════════════════════════════════════════════════════
# Phase 4: Quiz 页面构建
# ════════════════════════════════════════════════════════

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

# 2026-08-24: 数据加载层抽到 build_lib/data_loaders.py（模块3），此处重导出保持兼容
from build_lib.data_loaders import (
    get_category_slug, load_tools, load_articles, get_tool_link_map,
    get_published_tool_slugs, load_compare_data, load_quiz_data,
    load_ranking_data, load_live_data, load_news_archive, _load_dict_terms,
)
from build_lib.render_tool import (
    resolve_icon, tool_icon_html, get_category_color_var, get_category_glow_styles,
    _hex_to_rgb, get_price_info, extract_rating_num, make_tool_card_html,
    ensure_og_image, inject_internal_links, clean_broken_tool_links,
    get_category_stats, build_tool_title, build_tool_cross_links,
    build_compare_section_html, build_tool_page,
)
from build_lib.render_article import (
    _get_article_description, build_article_page, _pagination_html,
    build_article_list_pages, build_article_category_pages,
    replace_between_tags, generate_rss,
)
from build_lib.render_category import (
    _build_category_index_page, get_subcat_def, build_category_page,
    build_subcategory_page,
)
from build_lib.render_compare import (
    build_compare_page, build_alternatives_page, build_compare_slug_from_slugs,
    build_quiz_page, _build_ranking_index_page, _build_compare_index_page,
    _build_alternatives_index_page,
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

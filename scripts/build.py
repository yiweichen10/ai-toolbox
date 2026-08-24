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

# ═══════════════════════════════════════════════════════
# Phase 5b: Live Dashboard 数据加载与页面构建（动态数据面板）
# ═══════════════════════════════════════════════════════

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

# === AI-NEWS-FUNC-BEGIN ===
from urllib.parse import quote as url_quote

# === AI-NEWS-FUNC-END ===

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
from build_lib.render_ranking import (
    build_ranking_page,
)
from build_lib.render_live import (
    build_live_page, _live_nav_tabs, _live_section_dashboard, _live_section_matrix,
    _live_section_trend, _make_sparkline, _live_section_heatmap, _live_section_battle,
)
from build_lib.render_news_dict import (
    build_news_page, build_dict_page, _build_dict_index_page,
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

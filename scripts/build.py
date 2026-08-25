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
        'keywords': 'AI资讯,AI行业动态,AI资讯长文,AI行业资讯,大模型动态,AI速览',
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
            <a href="/news/" class="gn-item">AI动态</a>
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

from urllib.parse import quote as url_quote

# === AI-NEWS-FUNC-BEGIN ===
from urllib.parse import quote as url_quote

# === AI-NEWS-FUNC-END ===

# 中文站 IndexNow key（与 Bing Webmaster Tools 验证文件 {KEY}.txt 一致）
# 模块级统一常量，全量推送(push_to_indexnow)与增量单URL推送(_push_single_url)共用，避免硬编码漂移
INDEXNOW_KEY = "e66c6b3965b6490abd7bee1521893b1b"

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
from build_lib.main import main

if __name__ == '__main__':
    main()

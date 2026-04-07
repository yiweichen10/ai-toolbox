import os
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Define I18N and helper functions
i18n_block = r'''
# UI国际化字典 (SEO Face-lift)
UI_I18N = {
    'zh-CN': {
        'nav_ranking': '📊 工具排行',
        'nav_quiz': '🎯 AI工具选择器',
        'nav_live': '📈 实时面板',
        'nav_compare': '⚖️ 对比评测',
        'nav_alternatives': '🔄 替代方案',
        'nav_categories': '📂 全部分类',
        'header_title': 'AI工具宝箱',
        'header_subtitle': '每日更新 · 收录工具 持续更新',
        'footer_text': 'AI工具宝箱 · 每日精选优质AI工具',
        'breadcrumb_home': '首页',
        'breadcrumb_articles': '文章列表',
        'breadcrumb_compare': '工具对比',
        'breadcrumb_alternative': '替代方案',
        'breadcrumb_quiz': '工具选择器',
        'breadcrumb_ranking': '工具排行榜',
        'breadcrumb_live': '实时看板',
        'breadcrumb_nav': '面包屑导航',
        'related_tools': '🔧 相关工具',
        'related_articles': '📖 相关文章',
        'back_to_top': '返回顶部',
        'last_updated': '最后更新',
        'tool_website': '官网',
        'tool_price': '价格',
        'tool_category': '分类',
        'tool_platform': '平台',
        'tool_use_now': '立即使用',
        'tool_features': '核心功能',
        'tool_pros_cons': '优缺点分析',
        'tool_pros': '✅ 优点',
        'tool_cons': '❌ 缺点',
        'view_details': '详情',
        'more_compare': '🔗 更多相关对比',
        'more_alternatives': '🔗 更多替代方案',
        'latest_articles': '📝 最新文章',
        'article_default_cat': '文章',
        'page_num_prefix': '第',
        'page_num_suffix': '页',
        'visit_site': '立即访问',
    },
    'en': {
        'nav_ranking': '📊 Ranking',
        'nav_quiz': '🎯 AI Selector',
        'nav_live': '📈 Live Board',
        'nav_compare': '⚖️ Comparison',
        'nav_alternatives': '🔄 Alternatives',
        'nav_categories': '📂 Categories',
        'header_title': 'AI Tool Box',
        'header_subtitle': 'Daily Updates · Hand-picked AI Tools',
        'footer_text': 'AI Tool Box · Quality AI Tools Daily',
        'breadcrumb_home': 'Home',
        'breadcrumb_articles': 'Articles',
        'breadcrumb_compare': 'Comparison',
        'breadcrumb_alternative': 'Alternatives',
        'breadcrumb_quiz': 'AI Selector',
        'breadcrumb_ranking': 'Ranking',
        'breadcrumb_live': 'Live Board',
        'breadcrumb_nav': 'Breadcrumb Navigation',
        'related_tools': '🔧 Related Tools',
        'related_articles': '📖 Related Articles',
        'back_to_top': 'Back to Top',
        'last_updated': 'Last Updated',
        'tool_website': 'Website',
        'tool_price': 'Pricing',
        'tool_category': 'Category',
        'tool_platform': 'Platform',
        'tool_use_now': 'Use Now',
        'tool_features': 'Key Features',
        'tool_pros_cons': 'Pros & Cons',
        'tool_pros': '✅ Pros',
        'tool_cons': '❌ Cons',
        'view_details': 'Details',
        'more_compare': '🔗 More Comparisons',
        'more_alternatives': '🔗 More Alternatives',
        'latest_articles': '📝 Latest Articles',
        'article_default_cat': 'Article',
        'page_num_prefix': 'Page',
        'page_num_suffix': '',
        'visit_site': 'Visit Site',
    }
}

def get_ui_text(key, lang='zh-CN'):
    """获取指定语言的UI文本"""
    if lang not in UI_I18N:
        lang = 'zh-CN'
    return UI_I18N[lang].get(key, UI_I18N['zh-CN'].get(key, ''))

def get_global_nav(lang='zh-CN'):
    """获取指定语言的全局导航栏HTML"""
    _t = lambda k: get_ui_text(k, lang)
    return f"""    <nav class="global-nav" aria-label="Global Navigation">
        <div class="global-nav-inner">
            <a href="/ranking/" class="gn-item">{_t("nav_ranking")}</a>
            <a href="/quiz/" class="gn-item">{_t("nav_quiz")}</a>
            <a href="/live/" class="gn-item">{_t("nav_live")}</a>
            <a href="/compare/" class="gn-item">{_t("nav_compare")}</a>
            <a href="/alternatives/" class="gn-item">{_t("nav_alternatives")}</a>
            <a href="/category/" class="gn-item">{_t("nav_categories")}</a>
        </div>
    </nav>"""

# 为旧有的手动HTML注入保留全局变量 (默认中文)
GLOBAL_NAV = get_global_nav('zh-CN')
'''

# Replace old GLOBAL_NAV safely using lambda to avoid backslash issues in replacement string
global_nav_pattern = r"GLOBAL_NAV = '''[\s\S]*?'''"
content = re.sub(global_nav_pattern, lambda m: i18n_block, content)

# 2. Inject helper variables into build functions (using _t)
functions = {
    'build_tool_page': 'tool',
    'build_compare_page': 'compare_data',
    'build_alternatives_page': 'alt_data',
    'build_quiz_page': 'quiz_data',
    'build_ranking_page': 'ranking_data',
    'build_live_page': 'live_data',
    'build_category_page': None,
    'build_article_page': 'article',
    'build_article_list_pages': None,
    'build_index_page': None
}

for func_name, obj_name in functions.items():
    if obj_name:
        injection = f"\n    lang = {obj_name}.get('lang', 'zh-CN')\n    _t = lambda k: get_ui_text(k, lang)\n    global_nav = get_global_nav(lang)\n"
    else:
        injection = f"\n    lang = 'zh-CN'\n    _t = lambda k: get_ui_text(k, lang)\n    global_nav = get_global_nav(lang)\n"
        
    pattern = rf'(def {func_name}\(.*?\):)'
    content = re.sub(pattern, rf'\1{injection}', content)

# 3. Handle generic string replacements (skipping the I18N block)
parts = content.split('# UI国际化字典')
if len(parts) > 1:
    header = parts[0]
    rest = parts[1]
    
    rest = rest.replace('aria-label="面包屑导航"', 'aria-label="{_t(\"breadcrumb_nav\")}"')
    rest = rest.replace('🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span>', '🛠️ {_t(\"header_title\")} <span>{_t(\"header_subtitle\")}</span>')
    rest = rest.replace('© 2026 AI工具宝箱 · 每日精选优质AI工具', '© 2026 {_t(\"header_title\")} · {_t(\"footer_text\")}')
    rest = rest.replace('&#xA9; 2026 AI工具宝箱 · 每日精选优质AI工具', '&#xA9; 2026 {_t(\"header_title\")} · {_t(\"footer_text\")}')
    rest = rest.replace('<h3>相关工具</h3>', '<h3>{_t(\"related_tools\")}</h3>')
    rest = rest.replace('<h3>相关文章</h3>', '<h3>{_t(\"related_articles\")}</h3>')
    rest = rest.replace('>文章列表<', '>{_t(\"breadcrumb_articles\")}<')
    rest = rest.replace(' 文章列表 ', ' {_t(\"breadcrumb_articles\")} ')
    rest = rest.replace('<h2>📝 最新文章</h2>', '<h2>{_t(\"latest_articles\")}</h2>')
    rest = rest.replace('<span>第 {page_num} 页</span>', '<span>{_t(\"page_num_prefix\")} {page_num} {_t(\"page_num_suffix\")}</span>')
    rest = rest.replace("{GLOBAL_NAV}", "{global_nav}")

    content = header + '# UI国际化字典' + rest

# 4. Correctly patch build_article_page which might have duplicate lang
content = content.replace("    \"\"\"生成单个文章页的完整HTML\"\"\"\n    lang = article.get('lang', 'zh-CN')\n    _t = lambda k: get_ui_text(k, lang)\n    global_nav = get_global_nav(lang)\n\n    \"\"\"生成单个文章页的完整HTML\"\"\"\n    lang = article.get('lang', 'zh-CN')", "    \"\"\"生成单个文章页的完整HTML\"\"\"\n    lang = article.get('lang', 'zh-CN')\n    _t = lambda k: get_ui_text(k, lang)\n    global_nav = get_global_nav(lang)")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully and safely injected I18N system into build.py (v7 - using lambda to fix re.sub escape)")

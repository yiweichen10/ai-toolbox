import os
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update UI_I18N dictionary with more keys
new_i18n = '''UI_I18N = {
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
}'''

# Replace UI_I18N block
content = re.sub(r'UI_I18N = \{.*?\}', new_i18n, content, flags=re.DOTALL)

# 2. Update all build functions to use lang-specific GLOBAL_NAV and translated strings
# I will use a regex-based approach for common elements

# Replace the hardcoded breadcrumb aria-label and breadcrumb text
content = content.replace('aria-label="面包屑导航"', 'aria-label="{t(\'breadcrumb_nav\')}"')
content = content.replace("escape_html(article.get('category', '文章'))", "escape_html(article.get('category', t('article_default_cat')))")
content = content.replace('文章列表', '{t(\'breadcrumb_articles\')}')
content = content.replace('<h2>&#x1F4DD; 最新文章</h2>', '<h2>{t(\'latest_articles\')}</h2>')
content = content.replace('<span>第 {page_num} 页</span>', '<span>{t(\'page_num_prefix\')} {page_num} {t(\'page_num_suffix\')}</span>')

# Update the footer everywhere (it's similar but slightly different in some places)
# Find: <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
content = content.replace('© 2026 AI工具宝箱 · 每日精选优质AI工具', '© 2026 {t(\'header_title\')} · {t(\'footer_text\')}')
content = content.replace('© 2026 AI工具宝箱 · 每日精选优质AI工具'.encode('utf-8').decode('utf-8'), '© 2026 {t(\'header_title\')} · {t(\'footer_text\')}')
# Also hex encoded ones found in read: &#xA9; 2026 AI工具宝箱 · 每日精选优质AI工具
content = content.replace('&#xA9; 2026 AI工具宝箱 · 每日精选优质AI工具', '&#xA9; 2026 {t(\'header_title\')} · {t(\'footer_text\')}')

# Ensure each build function hasGLOBAL_NAV updated
# Instead of a global GLOBAL_NAV, we should call get_global_nav(lang) inside each function
# I will find functions and inject the call

functions_to_update = [
    'build_tool_page', 'build_compare_page', 'build_alternatives_page', 
    'build_quiz_page', 'build_ranking_page', 'build_live_page', 
    'build_category_page', 'build_article_page', 'build_articles_list_page'
]

for func in functions_to_update:
    # Inject global_nav = get_global_nav(lang) after t = lambda k: ...
    pattern = rf'(def {func}\(.*?:\n\s+lang = .*?\n\s+t = lambda k: .*?\n)'
    content = re.sub(pattern, r'\1    global_nav = get_global_nav(lang)\n', content)

# Replace {GLOBAL_NAV} with {global_nav} in all those functions
# Actually, I'll just do a global replace for {GLOBAL_NAV} to {global_nav} since it's cleaner
content = content.replace('{GLOBAL_NAV}', '{global_nav}')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied comprehensive UI I18N and dynamic lang support to build.py")

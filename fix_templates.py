
import os
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
content = open(file_path, 'r', encoding='utf-8').read()

# 1. Comprehensive UI_I18N
UI_I18N_NEW = """UI_I18N = {
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
    }
}"""

content = re.sub(r"UI_I18N = \{[\s\S]*?\}", UI_I18N_NEW, content)

def common_replace(body, lang_var='lang'):
    # Inject translation helper
    if "t = lambda k: get_ui_text(k," not in body:
        for var_name in ['tool', 'article', 'compare_data', 'alternative_data', 'quiz_data', 'ranking_data']:
            if f"{lang_var} = {var_name}.get('lang', 'zh-CN')" in body:
                 body = body.replace(f"{lang_var} = {var_name}.get('lang', 'zh-CN')", 
                                    f"{lang_var} = {var_name}.get('lang', 'zh-CN')\n    t = lambda k: get_ui_text(k, {lang_var})")
                 break

    # Replace header
    header_old_pattern = r'<header class="header">[\s\S]*?<h1>.*?🛠️.*?AI工具宝箱.*?<span>.*?</span></h1>[\s\S]*?</header>'
    header_new = '''<header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ {t('header_title')} <span>{t('header_subtitle')}</span></h1></a>
        </div>
    </header>'''
    body = re.sub(header_old_pattern, header_new, body)
    
    # Breadcrumbs
    body = body.replace('"name": "首页"', '"name": t(\'breadcrumb_home\')')
    body = body.replace('<a href="/">首页</a>', '<a href="/">{t(\'breadcrumb_home\')}</a>')
    body = body.replace('name": "文章列表"', 'name": t(\'breadcrumb_articles\')')
    body = body.replace('name": "工具对比"', 'name": t(\'breadcrumb_compare\')')
    body = body.replace('name": "替代方案"', 'name": t(\'breadcrumb_alternative\')')
    body = body.replace('name": "工具选择器"', 'name": t(\'breadcrumb_quiz\')')
    body = body.replace('name": "工具排行榜"', 'name": t(\'breadcrumb_ranking\')')
    
    body = body.replace('<a>文章列表</a>', '<a>{t(\'breadcrumb_articles\')}</a>')
    body = body.replace('<a href="/compare/">工具对比</a>', '<a href="/compare/">{t(\'breadcrumb_compare\')}</a>')
    body = body.replace('<a href="/alternatives/">替代方案</a>', '<a href="/alternatives/">{t(\'breadcrumb_alternative\')}</a>')
    
    # Generic replacements
    body = body.replace('- AI工具宝箱', '- {t(\'header_title\')}')
    body = body.replace('AI工具宝箱深度评测', '{t(\'header_title\')}深度评测')
    body = body.replace('AI工具宝箱最新文章', '{t(\'header_title\')}最新文章')
    body = body.replace('"name": "AI工具宝箱"', '"name": f"{t(\'header_title\')}"')
    body = body.replace('content="AI工具宝箱">', 'content="{t(\'header_title\')}">')
    
    # Footer
    footer_old_pattern = r'<footer class="footer">[\s\S]*?<p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>[\s\S]*?</footer>'
    footer_new = '''<footer class="footer">
        <p>© 2026 {t('header_title')} · {t('footer_text')}</p>
    </footer>'''
    body = re.sub(footer_old_pattern, footer_new, body)
    
    return body

# Re-run all
content = re.sub(r'def build_article_page\(article, all_articles, all_tools=None\):[\s\S]*?return html', 
                 lambda m: common_replace(m.group(0), 'lang'), content)

def update_tool_page(m):
    body = common_replace(m.group(0), 'lang')
    body = body.replace('<h3>🔗 相关工具推荐</h3>', '<h3>{t(\'related_tools\')}</h3>')
    body = body.replace('<h3>📚 相关文章</h3>', '<h3>{t(\'related_articles\')}</h3>')
    body = body.replace('<strong>官网</strong>', '<strong>{t(\'tool_website\')}</strong>')
    body = body.replace('<strong>价格</strong>', '<strong>{t(\'tool_price\')}</strong>')
    body = body.replace('<strong>分类</strong>', '<strong>{t(\'tool_category\')}</strong>')
    body = body.replace('<strong>平台</strong>', '<strong>{t(\'tool_platform\')}</strong>')
    body = body.replace('立即使用 →', "{t('tool_use_now')} →")
    body = body.replace('详情</a>', "{t('view_details')}</a>")
    return body

content = re.sub(r'def build_tool_page\(tool, all_tools, all_articles=None\):[\s\S]*?return html', update_tool_page, content)

def update_compare(m):
    body = common_replace(m.group(0), 'lang')
    body = body.replace('<h3>🔗 更多相关对比</h3>', '<h3>{t(\'more_compare\')}</h3>')
    body = body.replace('详情</a>', "{t('view_details')}</a>")
    return body
content = re.sub(r'def build_compare_page\(compare_data, all_tools, all_articles=None\):[\s\S]*?return html', update_compare, content)

def update_alt(m):
    body = common_replace(m.group(0), 'lang')
    body = body.replace('<h3>🔗 更多替代方案</h3>', '<h3>{t(\'more_alternatives\')}</h3>')
    body = body.replace('详情</a>', "{t('view_details')}</a>")
    return body
content = re.sub(r'def build_alternative_page\(alternative_data, all_tools, all_articles=None\):[\s\S]*?return html', update_alt, content)

content = re.sub(r'def build_quiz_page\(quiz_data, all_tools\):[\s\S]*?return html', 
                 lambda m: common_replace(m.group(0), 'lang'), content)
content = re.sub(r'def build_ranking_page\(ranking_data, all_tools, all_articles=None\):[\s\S]*?return html', 
                 lambda m: common_replace(m.group(0), 'lang'), content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Success')

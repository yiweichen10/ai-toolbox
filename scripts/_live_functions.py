

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


def build_live_page(live_data, page_config, all_tools, articles):
    """
    构建 live dashboard 的子页面。
    type: dashboard | matrix | trend | heatmap | battle
    """
    from datetime import datetime as _ldt

    page_type = page_config.get('type', 'dashboard')
    page_slug = page_config.get('slug', 'unknown')
    page_title = page_config.get('title', 'AI工具实时监控面板')
    meta_desc = page_config.get('meta_description', '')
    keywords = page_config.get('keywords', [])
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

    # Build HTML parts
    header_nav = '<header class="header"><div class="container header-inner"><a href="/" class="logo">✨ AI工具宝箱</a><nav class="nav"><a href="/">首页</a><a href="/ranking/">排名</a><a href="/quiz/">选工具</a><a href="/live/">实时</a></nav></div></header>'
    page_icon = '<span class="tool-icon-lg">' + icon_emoji + '</span>'
    h1_tag = '<h1>' + escape_html(page_title) + '</h1>'
    subtitle = '<p class="subtitle">' + escape_html(meta_desc) + '</p>'
    update_info = '<div class="last-update">📅 数据更新：' + escape_html(last_updated) + '</div>'
    methodology = '<div class="methodology-note"><strong>数据说明：</strong>本面板数据由AIToolBox团队每日自动更新聚合，来源包括工具官方信息、公开搜索热度、用户评价等。所有数据仅供参考，具体选择请以各工具官方页面为准。</div>'
    footer = '<footer class="footer"><p>&copy; 2026 AI工具宝箱 · 每日精选优质AI工具 · 更新于 ' + _ldt.now().strftime('%Y-%m-%d %H:%M') + '</p></footer>'

    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <title>' + escape_html(page_title) + ' - AI工具宝箱</title>\n'
        '    <meta name="description" content="' + escape_html(meta_desc) + '">\n'
        '    <meta name="keywords" content="' + ','.join(keywords) + ',AI工具宝箱,aitoolbox.hk">\n'
        '    <link rel="canonical" href="https://www.aitoolbox.hk/live/' + page_slug + '/">\n'
        '    <meta property="og:type" content="website">\n'
        '    <meta property="og:title" content="' + escape_html(page_title) + ' - AI工具宝箱">\n'
        '    <meta property="og:description" content="' + escape_html(meta_desc) + '">\n'
        '    <meta property="og:url" content="https://www.aitoolbox.hk/live/' + page_slug + '/">\n'
        '    <link rel="stylesheet" href="/css/style.css">\n'
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

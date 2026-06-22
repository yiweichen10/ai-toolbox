// SEO网站 - 主入口脚本
// 首页：按类目分组展示全部工具 + 侧边导航跳转 + 搜索过滤

// ── 分类排序（与侧边栏顺序一致）──
var CATEGORY_ORDER = [
    'AI对话', 'AI写作', 'AI绘画', 'AI编程',
    'AI视频', 'AI音频', 'AI办公', 'AI设计',
    'AI搜索', 'AI翻译', 'AI自动化', 'AI效率',
    'AI智能体', 'AI开发', 'AI行业应用'
];

// ── 分类配色（CSS 变量名 → 色值）──
var CATEGORY_COLORS = {
    'AI对话':   '#10b981',
    'AI写作':   '#6366f1',
    'AI绘画':   '#f59e0b',
    'AI编程':   '#3b82f6',
    'AI视频':   '#ef4444',
    'AI音频':   '#8b5cf6',
    'AI办公':   '#0ea5e9',
    'AI设计':   '#ec4899',
    'AI搜索':   '#14b8a6',
    'AI翻译':   '#22c55e',
    'AI自动化': '#f97316',
    'AI效率':   '#a855f7',
    'AI智能体': '#06b6d4',
    'AI开发':   '#6366f1',
    'AI行业应用':'#4f46e5'
};

function buildCategoryId(category) {
    return 'cat-' + category.replace(/[^A-Za-z0-9\u4e00-\u9fa5]/g, '-');
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── 核心：按类目分组渲染全部工具 ──
function renderCategorizedSections(allTools) {
    var allSection = document.getElementById('allSection');
    if (!allSection) return;

    // 1. 按类目分组
    var grouped = {};
    CATEGORY_ORDER.forEach(function (cat) { grouped[cat] = []; });
    var other = [];

    allTools.forEach(function (t) {
        if (grouped[t.category]) {
            grouped[t.category].push(t);
        } else {
            other.push(t);
        }
    });

    // 2. 渲染每个类目为独立区块
    var html = '';
    var totalRendered = 0;

    CATEGORY_ORDER.forEach(function (cat) {
        var tools = grouped[cat];
        if (tools.length === 0) return;
        totalRendered += tools.length;

        var catId = buildCategoryId(cat);
        var catColor = CATEGORY_COLORS[cat] || '#4f46e5';
        html += '<section class="home-section cat-section" id="' + catId + '" style="--cat-color:' + catColor + '">';
        html += '<div class="section-header">';
        html += '<div class="section-header-left">';
        html += '<span class="cat-dot" style="background:' + catColor + '"></span>';
        html += '<h3>' + escapeHtml(cat) + '<span class="cat-badge">' + tools.length + ' 款</span></h3>';
        html += '</div>';
        html += '</div>';
        html += '<div class="tools-grid">';

        tools.forEach(function (t, i) {
            var badge = t.badge ? '<span class="badge badge-' + t.badge.type + '">' + t.badge.text + '</span>' : '';
            var tags = (t.tags || []).map(function (tag) {
                return '<span class="tag ' + (tag.type || '') + '">' + tag.text + '</span>';
            }).join('');
            html += '<article class="tool-card fade-in" style="animation-delay: ' + (i * 0.05).toFixed(2) + 's;" onclick="location.href=\'/tools/' + t.slug + '/index.html\'">';
            html += '<div class="tool-icon" style="background:' + t.color + ';">' + t.emoji + '</div>';
            html += '<h4>' + escapeHtml(t.name) + ' ' + badge + '</h4>';
            html += '<p class="desc">' + escapeHtml(t.description) + '</p>';
            html += '<div class="tags">' + tags + '</div>';
            html += '<div class="meta">';
            html += '<span class="rating">' + t.rating + '</span>';
            html += '<span class="visits">&#x1F441; ' + t.visits + '</span>';
            html += '</div>';
            html += '</article>';
        });

        html += '</div></section>';
    });

    // 更新工具总数（静默，不显示顶部标题栏）
    var countEl = document.getElementById('toolCount');
    if (countEl) countEl.textContent = '共 ' + totalRendered + ' 款';

    // 直接渲染类目区块，移除了冗余的"全部工具 ALL TOOLS"标题
    allSection.innerHTML = html;

    // 更新侧边栏各分类工具数
    updateSidebarCounts(grouped);
}

// ── 更新侧边栏分类工具数 ──
function updateSidebarCounts(grouped) {
    document.querySelectorAll('.sidebar-cat').forEach(function (btn) {
        var cat = btn.dataset.category;
        if (cat === 'all') return;
        var count = grouped[cat] ? grouped[cat].length : 0;
        var existing = btn.querySelector('.sidebar-count');
        if (existing) existing.remove();
        if (count > 0) {
            var span = document.createElement('span');
            span.className = 'sidebar-count';
            span.textContent = count;
            btn.appendChild(span);
        }
    });
}

// ── 侧边栏导航：点击滚动到对应类目 ──
function initCategoryFilter() {
    var sidebarBtns = document.querySelectorAll('.sidebar-cat');
    var mobileBtns = document.querySelectorAll('.mobile-categories .cat-btn');

    function clearActive() {
        sidebarBtns.forEach(function (b) { b.classList.remove('active'); });
        mobileBtns.forEach(function (b) { b.classList.remove('active'); });
    }

    function setActive(category) {
        sidebarBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === category); });
        mobileBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === category); });
    }

    function scrollToCategory(category) {
        clearActive();
        setActive(category);

        var HEADER_OFFSET = 155;
        if (category === 'all') {
            var allSection = document.getElementById('allSection');
            if (allSection) {
                var top = allSection.getBoundingClientRect().top + window.pageYOffset - HEADER_OFFSET;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        } else {
            var catId = buildCategoryId(category);
            var section = document.getElementById(catId);
            if (section) {
                // 补偿顶部固定 header（sticky header ~120px + global-nav ~32px + search-bar ~44px）
                var top = section.getBoundingClientRect().top + window.pageYOffset - HEADER_OFFSET;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        }
    }

    sidebarBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            scrollToCategory(btn.dataset.category);
        });
    });

    mobileBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            scrollToCategory(btn.dataset.category);
        });
    });

    // ── ScrollSpy: 滚动时自动高亮当前类目 ──
    var ticking = false;
    window.addEventListener('scroll', function () {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
            var found = 'all';
            var minTop = Infinity;

            CATEGORY_ORDER.forEach(function (cat) {
                var catId = buildCategoryId(cat);
                var section = document.getElementById(catId);
                if (section) {
                    var rect = section.getBoundingClientRect();
                    if (rect.top < 200 && rect.top > -rect.height && rect.top < minTop) {
                        minTop = rect.top;
                        found = cat;
                    }
                }
            });

            setActive(found);
            ticking = false;
        });
    }, { passive: true });
}

// ── 搜索：按类目过滤 ──
function initSearch(allTools) {
    var searchBtn = document.querySelector('.search-bar-below-nav .search-box button');
    var searchInput = document.getElementById('searchInput');
    if (!searchBtn || !searchInput) return;

    function performSearch() {
        var query = searchInput.value.trim().toLowerCase();
        var sidebarBtns = document.querySelectorAll('.sidebar-cat');
        var mobileBtns = document.querySelectorAll('.mobile-categories .cat-btn');

        if (!query) {
            // 清空搜索：显示全部
            document.querySelectorAll('#allSection .cat-section').forEach(function (s) {
                s.style.display = '';
                s.querySelectorAll('.tool-card').forEach(function (c) {
                    c.style.display = '';
                });
            });
            sidebarBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });
            mobileBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });
            return;
        }

        // 对每个类目内的卡片进行搜索过滤
        var totalHits = 0;
        document.querySelectorAll('#allSection .cat-section').forEach(function (section) {
            var catHits = 0;
            section.querySelectorAll('.tool-card').forEach(function (card) {
                var title = (card.querySelector('h4') || {}).textContent || '';
                var desc = (card.querySelector('.desc') || {}).textContent || '';
                var tagTexts = '';
                card.querySelectorAll('.tag').forEach(function (tag) { tagTexts += tag.textContent.toLowerCase() + ' '; });

                var match = title.toLowerCase().indexOf(query) !== -1 ||
                    desc.toLowerCase().indexOf(query) !== -1 ||
                    tagTexts.indexOf(query) !== -1;

                card.style.display = match ? '' : 'none';
                if (match) catHits++;
            });
            section.style.display = catHits > 0 ? '' : 'none';
            totalHits += catHits;
        });

        // 高亮"全部"
        sidebarBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });
        mobileBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });

        // 更新计数
        var countEl = document.getElementById('toolCount');
        if (countEl) countEl.textContent = '找到 ' + totalHits + ' 款';

        // 滚动到第一个可见类目
        if (totalHits > 0) {
            var firstVisible = document.querySelector('#allSection .cat-section[style*="display:"]:not([style*="display: none"]), #allSection .cat-section:not([style])');
            // 更精确：找到第一个 display 不为 none 的
            var allCatSections = document.querySelectorAll('#allSection .cat-section');
            var first = null;
            allCatSections.forEach(function (s) {
                if (!first && s.style.display !== 'none') first = s;
            });
            if (first) {
                setTimeout(function () {
                    var top = first.getBoundingClientRect().top + window.pageYOffset - 155;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }, 100);
            }
        }
    }

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') performSearch();
    });
}

// ── 内容Tab切换（左侧卡片式）──
function initContentTabs() {
    var container = document.getElementById('contentTabs');
    if (!container) return;
    var cards = container.querySelectorAll('.tab-card');
    var panels = container.querySelectorAll('.tab-panel');

    cards.forEach(function (card) {
        card.addEventListener('click', function () {
            var tab = card.dataset.tab;
            cards.forEach(function (c) { c.classList.remove('active'); });
            panels.forEach(function (p) { p.classList.remove('active'); });
            card.classList.add('active');
            var target = document.getElementById('panel-' + tab);
            if (target) target.classList.add('active');
        });
    });
}

// ── 返回顶部 ──
(function initBackToTop() {
    var existingBtn = document.getElementById('backToTop');
    if (!existingBtn) return;
    var btn = existingBtn.cloneNode(true);
    existingBtn.parentNode.replaceChild(btn, existingBtn);
    var tickingBt = false;
    var onScroll = function () {
        if (!tickingBt) {
            requestAnimationFrame(function () {
                btn.classList.toggle('visible', window.scrollY > 150);
                tickingBt = false;
            });
            tickingBt = true;
        }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    btn.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
})();

// ── 入口 ──
document.addEventListener('DOMContentLoaded', function () {
    if (!window.__ALL_TOOLS__) return;

    var allTools = window.__ALL_TOOLS__;

    // 1. 按类目分组渲染全部工具（核心功能）
    renderCategorizedSections(allTools);

    // 2. 侧边导航滚动跳转
    initCategoryFilter();

    // 3. 搜索过滤
    initSearch(allTools);

    // 4. 内容Tab切换
    initContentTabs();
});

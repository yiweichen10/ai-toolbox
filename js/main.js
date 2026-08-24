// SEO网站 - 主入口脚本
// 首页：按类目分组展示全部工具 + 侧边导航跳转 + 搜索过滤

// ── 分类排序（与侧边栏顺序一致）──
var CATEGORY_ORDER = [
    'AI对话', 'AI写作', 'AI绘画', 'AI编程',
    'AI视频', 'AI音频', 'AI办公', 'AI设计',
    'AI搜索', 'AI翻译', 'AI自动化', 'AI效率',
    'AI智能体', 'AI开发', 'AI行业应用',
    'AI学习', 'AI检测', 'AI提示词'
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
    'AI行业应用':'#4f46e5',
    'AI学习':   '#6366f1',
    'AI检测':   '#ef4444',
    'AI提示词': '#8b5cf6'
};

function buildCategoryId(category) {
    return 'cat-' + category.replace(/[^A-Za-z0-9\u4e00-\u9fa5]/g, '-');
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function getCategorySlugByName(categoryName) {
    var slugMap = window.__CATEGORY_SLUG_MAP__;
    if (slugMap && slugMap[categoryName]) return slugMap[categoryName];
    var subcats = window.__SUBCATEGORIES__;
    if (subcats) {
        for (var slug in subcats) {
            if (subcats[slug].name === categoryName) return slug;
        }
    }
    return null;
}

function buildSubcatId(parentSlug, subSlug) {
    return 'subcat-' + parentSlug + '-' + subSlug;
}

var NEW_BADGE_MAX_DAYS = 30;

// 判断 NEW 标签是否已过期（收录超过 30 天自动隐藏）
function isNewBadgeExpired(createdDate) {
    if (!createdDate) return true;
    var d = new Date(String(createdDate).replace(/-/g, '/'));
    if (isNaN(d.getTime())) return true;
    return (Date.now() - d.getTime()) > NEW_BADGE_MAX_DAYS * 24 * 60 * 60 * 1000;
}

// 归一化标签类型：数据缺失时按文案推断，保证样式类名有效
function getBadgeType(t) {
    var b = t.badge;
    var type = b && b.type;
    if (type === 'new' || type === 'hot' || type === 'pick') return type;
    var text = String((b && b.text) || '');
    if (/new|新/i.test(text)) return 'new';
    if (/hot|热/i.test(text)) return 'hot';
    if (/pick|推荐/i.test(text)) return 'pick';
    return 'hot';
}

// 生成角标 HTML；空值/未定义/null 一律不渲染，NEW 过期后自动隐藏
function buildBadgeHtml(t) {
    var b = t.badge;
    if (!b) return '';
    var text = b.text == null ? '' : String(b.text);
    if (!text || text === 'undefined' || text === 'null') return '';
    var type = getBadgeType(t);
    // 按文案判断是否为 NEW 类标签（避免 type 字段不规范的旧数据绕过过期规则）
    if (/new|新/i.test(text) && isNewBadgeExpired(t.created_date)) return '';
    return '<span class="badge badge-' + type + '">' + text + '</span>';
}

function buildToolCardHtml(t, i) {
    var delay = (i * 0.05).toFixed(2);
    var badge = buildBadgeHtml(t);
    var tags = (t.tags || []).map(function (tag) {
        if (!tag) return '';
        var text = typeof tag === 'string' ? tag : (tag.text == null ? '' : String(tag.text));
        if (!text || text === 'undefined' || text === 'null') return '';
        var cls = (typeof tag === 'object' && tag.type) ? ' ' + tag.type : '';
        return '<span class="tag' + cls + '">' + text + '</span>';
    }).join('');
    var iconHtml = (t.icon)
        ? '<img src="' + t.icon + '" class="tool-icon-real" alt="' + escapeHtml(t.name || '') + '" loading="lazy" width="48" height="48">'
        : '<div class="tool-icon" style="background:' + t.color + ';">' + t.emoji + '</div>';
    var subcatAttr = t.subcategory ? ' data-subcat="' + t.subcategory + '"' : '';
    return '<article class="tool-card fade-in" data-slug="' + t.slug + '" style="animation-delay: ' + delay + 's;"' + subcatAttr + ' onclick="location.href=\'/tools/' + t.slug + '/\'">' +
        iconHtml +
        '<h4>' + escapeHtml(t.name) + ' ' + badge + '</h4>' +
        '<p class="desc">' + escapeHtml(t.description) + '</p>' +
        '<div class="tags">' + tags + '</div>' +
        '<div class="meta">' +
        '<span class="rating">' + t.rating + '</span>' +
        '<span class="visits">&#x1F441; ' + t.visits + '</span>' +
        '</div>' +
        '</article>';
}

// ── 核心：按类目分组渲染全部工具，支持子类目锚点区块 ──
// v6: 每个分类默认只渲染前 8 款，支持「展开全部」；搜索/子类目过滤自动加载全量
var __CAT_VIEW__ = { expanded: {}, expandedAll: false, searchMode: false };
var CAT_PAGE_SIZE = (typeof window !== 'undefined' && window.innerWidth < 768) ? 4 : 8;

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
    var expandedAll = __CAT_VIEW__.expandedAll || __CAT_VIEW__.searchMode;

    CATEGORY_ORDER.forEach(function (cat) {
        var tools = grouped[cat];
        if (tools.length === 0) return;
        totalRendered += tools.length;

        var catId = buildCategoryId(cat);
        var catColor = CATEGORY_COLORS[cat] || '#4f46e5';
        var parentSlug = getCategorySlugByName(cat);
        var subcatMap = parentSlug && window.__SUBCATEGORIES__ && window.__SUBCATEGORIES__[parentSlug]
            ? window.__SUBCATEGORIES__[parentSlug].subcats
            : null;

        html += '<section class="home-section cat-section" id="' + catId + '" data-cat="' + escapeHtml(cat) + '" style="--cat-color:' + catColor + '">';
        html += '<div class="section-header">';
        html += '<div class="section-header-left">';
        html += '<span class="cat-dot" style="background:' + catColor + '"></span>';
        html += '<h3>' + escapeHtml(cat) + '<span class="cat-badge">' + tools.length + ' 款</span></h3>';
        html += '</div>';
        if (parentSlug) {
            html += '<a class="cat-more-link" href="/category/' + parentSlug + '/">查看更多</a>';
        }
        html += '</div>';

        // 子类目胶囊 pills（红框区域）→ 首页内锚点+过滤，与左侧子类目联动同步
        if (subcatMap) {
            html += '<div class="subcat-pills">';
            Object.keys(subcatMap).forEach(function (subSlug) {
                html += '<a href="#' + catId + '" class="subcat-pill" data-parent="' + parentSlug + '" data-subcat="' + subSlug + '">' + escapeHtml(subcatMap[subSlug].name) + '</a>';
            });
            html += '</div>';
        }

        var expanded = expandedAll || __CAT_VIEW__.expanded[cat] === true;
        var shown = expanded ? tools : tools.slice(0, CAT_PAGE_SIZE);

        // 工具渲染：扁平宫格（不分组），每张卡带 data-subcat 用于过滤
        html += '<div class="tools-grid">';
        shown.forEach(function (t, i) { html += buildToolCardHtml(t, i); });
        if (!expanded && tools.length > CAT_PAGE_SIZE) {
            html += '<div class="cat-expand-row"><button type="button" class="cat-expand-btn" data-cat="' + escapeHtml(cat) + '">展开全部 ' + tools.length + ' 款</button></div>';
        }
        html += '</div>';

        html += '</section>';
    });

    // v6: 顶部主标题 + 全部分类展开/收起按钮（JS 渲染，模板中的静态头会被替换）
    var masterHeader = '';
    masterHeader += '<div class="section-header all-master-header">';
    masterHeader += '<div class="section-header-left"><h2>全部工具<span>ALL TOOLS</span></h2></div>';
    masterHeader += '<a href="/tools/" style="font-size:13px;font-weight:600;color:var(--primary);text-decoration:none;white-space:nowrap;">查看全部工具 →</a>';
    masterHeader += '<button type="button" class="all-expand-btn" id="allExpandBtn">' + (expandedAll ? '收起分类' : '展开全部分类') + '</button>';
    masterHeader += '<span class="tool-count" id="toolCount">共 ' + totalRendered + ' 款</span>';
    masterHeader += '</div>';

    allSection.innerHTML = masterHeader + html;

    // 更新侧边栏各分类工具数
    updateSidebarCounts(grouped);
    wireExpandButtons();
    wireAllExpand();

    // 通知收藏模块重新绑定（卡片已被重绘）
    if (window.dispatchEvent) {
        try { window.dispatchEvent(new CustomEvent('aitools:rendered')); } catch (e) {}
    }
}

function wireExpandButtons() {
    var allSection = document.getElementById('allSection');
    if (!allSection) return;
    allSection.querySelectorAll('.cat-expand-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var cat = btn.getAttribute('data-cat');
            __CAT_VIEW__.expanded[cat] = true;
            renderCategorizedSections(window.__ALL_TOOLS__ || []);
            var sec = document.getElementById(buildCategoryId(cat));
            if (sec) {
                setTimeout(function () {
                    var off = getStickyOffsetForScroll();
                    window.scrollTo({ top: sec.getBoundingClientRect().top + window.pageYOffset - off, behavior: 'smooth' });
                }, 50);
            }
        });
    });
}

function wireAllExpand() {
    var btn = document.getElementById('allExpandBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
        __CAT_VIEW__.expandedAll = !__CAT_VIEW__.expandedAll;
        if (!__CAT_VIEW__.expandedAll) __CAT_VIEW__.expanded = {};
        renderCategorizedSections(window.__ALL_TOOLS__ || []);
    });
}

function getStickyOffsetForScroll() {
    var offset = 0;
    ['.header', '.global-nav', '.search-bar-below-nav'].forEach(function (sel) {
        var el = document.querySelector(sel);
        if (el) {
            var pos = window.getComputedStyle(el).position;
            if (pos === 'sticky' || pos === 'fixed' || pos === '-webkit-sticky') offset += el.getBoundingClientRect().height;
        }
    });
    return offset + 16;
}

// ── 更新侧边栏分类工具数 ──
function updateSidebarCounts(grouped) {
    document.querySelectorAll('.sidebar-cat, .cat-btn').forEach(function (btn) {
        var cat = btn.dataset.category;
        if (cat === 'all') return;
        var count = grouped[cat] ? grouped[cat].length : 0;
        var label = btn.querySelector('.sc-label') || btn;
        var existing = label.querySelector('.sidebar-count');
        if (existing) existing.remove();
        if (count > 0) {
            var span = document.createElement('span');
            span.className = 'sidebar-count';
            span.textContent = count;
            label.appendChild(span);
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

    // 动态计算页面顶部所有 sticky/fixed 元素的实际占用高度
    function getStickyOffset() {
        var offset = 0;
        // 按顺序累加所有固定在顶部的元素高度
        var selectors = ['.header', '.global-nav', '.search-bar-below-nav'];
        selectors.forEach(function (sel) {
            var el = document.querySelector(sel);
            if (el) {
                var style = window.getComputedStyle(el);
                var pos = style.position;
                if (pos === 'sticky' || pos === 'fixed' || pos === '-webkit-sticky') {
                    offset += el.getBoundingClientRect().height;
                }
            }
        });
        // 额外留 16px 视觉喘息空间，避免区块标题顶边贴着固定栏
        return offset + 16;
    }

    // 点击导航后短暂挂起 ScrollSpy，避免平滑滚动期间被覆盖为 "all"
    var spySuspended = false;

    function suspendSpy() {
        spySuspended = true;
        clearTimeout(window.___spyTimer);
        window.___spyTimer = setTimeout(function () { spySuspended = false; }, 800);
    }

    function scrollToCategory(category) {
        clearActive();
        setActive(category);
        suspendSpy();

        var HEADER_OFFSET = getStickyOffset();
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
                // 点击大类时清除子类目过滤（恢复全部）
                if (window.resetSectionFilter) window.resetSectionFilter(section);
                var top = section.getBoundingClientRect().top + window.pageYOffset - HEADER_OFFSET;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        }
    }

    sidebarBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (btn.tagName === 'A' && btn.getAttribute('href')) e.preventDefault();
            scrollToCategory(btn.dataset.category);
        });
    });

    mobileBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (btn.tagName === 'A' && btn.getAttribute('href')) e.preventDefault();
            scrollToCategory(btn.dataset.category);
        });
    });

    // ── ScrollSpy: 滚动时自动高亮当前类目 ──
    // 修复：按顺序取第一个“顶部已进入视口阈值下方且未完全滚出视口”的类目，
    // 避免已滚出视口的负 top 区域被错误选中（导致点击后高亮滞后一个分类）。
    var ticking = false;
    var SPY_THRESHOLD = 200;
    window.addEventListener('scroll', function () {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
            // 点击导航后短暂挂起，等待 smooth scroll 到位
            if (spySuspended) { ticking = false; return; }
            var found = 'all';

            CATEGORY_ORDER.forEach(function (cat) {
                var catId = buildCategoryId(cat);
                var section = document.getElementById(catId);
                if (section) {
                    var rect = section.getBoundingClientRect();
                    if (rect.top <= SPY_THRESHOLD && rect.bottom > SPY_THRESHOLD) {
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
        // v6: 搜索需在全量卡片上过滤，退出搜索恢复折叠视图
        if (query && !window.__CAT_VIEW__.searchMode) {
            window.__CAT_VIEW__.searchMode = true;
            renderCategorizedSections(allTools);
        } else if (!query && window.__CAT_VIEW__.searchMode) {
            window.__CAT_VIEW__.searchMode = false;
            renderCategorizedSections(allTools);
        }
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
            hideArticleSearchResults();
            sidebarBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });
            mobileBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.category === 'all'); });
            var hint0 = document.getElementById('searchEmptyHint');
            if (hint0) hint0.style.display = 'none';
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

        // 同时匹配页面内可见的文章链接（首页文章区块 / 相关文章），弥补"只搜工具"的缺口
        showArticleSearchResults(query);

        // 更新计数
        var countEl = document.getElementById('toolCount');
        if (countEl) countEl.textContent = '找到 ' + totalHits + ' 款';
        var hint1 = document.getElementById('searchEmptyHint');
        if (hint1) hint1.style.display = totalHits === 0 ? 'block' : 'none';

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
                    var HEADER_OFFSET = (function () {
                        var off = 0;
                        ['.header', '.global-nav', '.search-bar-below-nav'].forEach(function (sel) {
                            var el = document.querySelector(sel);
                            if (el) {
                                var pos = window.getComputedStyle(el).position;
                                if (pos === 'sticky' || pos === 'fixed' || pos === '-webkit-sticky') off += el.getBoundingClientRect().height;
                            }
                        });
                        return off + 16;
                    })();
                    var top = first.getBoundingClientRect().top + window.pageYOffset - HEADER_OFFSET;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }, 100);
            }
        }
    }

    // v8 (2026-08-09, P0-1)：搜索时同时匹配页面内可见的文章链接，
    // 让"搜文章"在首页直达入口（完整文章索引留待 P1 搜索页实现）。
    function showArticleSearchResults(query) {
        var container = document.getElementById('articleSearchResults');
        if (!container) {
            container = document.createElement('div');
            container.id = 'articleSearchResults';
            container.style.cssText = 'margin:20px auto;max-width:880px;padding:16px 18px;'
                + 'background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);display:none;';
            var allSection = document.getElementById('allSection');
            if (allSection && allSection.parentNode) {
                allSection.parentNode.insertBefore(container, allSection);
            }
        }
        var seen = {};
        var hits = [];
        document.querySelectorAll('a[href*="/articles/"]').forEach(function (a) {
            var href = a.getAttribute('href');
            if (!href || seen[href]) return;
            var title = (a.textContent || '').replace(/\s+/g, ' ').trim();
            title = title.replace(/^\d{2}\/\d{2}\s*/, '').replace(/\s*(AI资讯|AI评测|教程|快讯)\s*$/, '').trim();
            if (title && title.toLowerCase().indexOf(query) !== -1) {
                seen[href] = 1;
                hits.push({ href: href, title: title });
            }
        });
        if (!hits.length) {
            container.style.display = 'none';
            return;
        }
        var html = '<div style="font-weight:700;margin-bottom:10px;">📖 相关文章（' + hits.length + '）</div>';
        hits.slice(0, 5).forEach(function (h) {
            html += '<a href="' + h.href + '" style="display:block;padding:9px 0;border-bottom:1px solid var(--border-light);'
                + 'color:var(--primary);font-size:14px;text-decoration:none;">' + h.title + '</a>';
        });
        html += '<a href="/articles/" style="display:inline-block;margin-top:10px;font-size:13px;color:var(--text-muted);">查看全部文章 →</a>';
        container.innerHTML = html;
        container.style.display = 'block';
    }

    function hideArticleSearchResults() {
        var container = document.getElementById('articleSearchResults');
        if (container) container.style.display = 'none';
    }

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') performSearch();
    });

    // v8 (2026-08-09, P0-1)：支持 /?q= 直达搜索。
    // 404 页搜索框、全站搜索条（GET /?q=）、Google sitelinks SearchAction 都走这条链路。
    (function () {
        var m = location.search.match(/[?&]q=([^&]*)/);
        if (m) {
            var q = decodeURIComponent(m[1].replace(/\+/g, ' ')).trim();
            if (q) {
                searchInput.value = q;
                performSearch();
                // 让搜索结果区可见（若搜索后页面未滚动到工具区，主动滚动一次）
                setTimeout(function () {
                    var hint = document.getElementById('searchEmptyHint');
                    var toolCount = document.getElementById('toolCount');
                    if ((hint && hint.style.display !== 'none') || (toolCount && toolCount.textContent.indexOf('找到') !== -1)) {
                        var first = document.querySelector('#allSection .cat-section:not([style*="display: none"]), #allSection');
                        if (first) first.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 150);
            }
        }
    })();

    // v6.3: 热门搜索词快捷入口
    document.querySelectorAll('#hotSearch [data-q]').forEach(function (chip) {
        chip.addEventListener('click', function () {
            searchInput.value = chip.getAttribute('data-q');
            performSearch();
            // v6.10: 手机版反馈——点击后滚动到工具列表区，避免"点了没反应"的错觉
            var _allSec = document.getElementById('allSection');
            if (_allSec) {
                _allSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// ── 左侧导航子类目展开：读取 __SUBCATEGORIES__，在大类按钮旁加箭头和子类链接 ──
function initSidebarSubcategories() {
    var subcats = window.__SUBCATEGORIES__;
    if (!subcats) return;

    var sidebarNav = document.getElementById('sidebarNav');
    if (!sidebarNav) return;

    Object.keys(subcats).forEach(function (parentSlug) {
        var parentData = subcats[parentSlug];
        var parentName = parentData.name;
        var subcatMap = parentData.subcats || {};
        var subcatSlugs = Object.keys(subcatMap);
        if (subcatSlugs.length === 0) return;

        // 找到对应大类按钮
        var btn = null;
        sidebarNav.querySelectorAll('.sidebar-cat').forEach(function (b) {
            if (b.dataset.category === parentName) btn = b;
        });
        if (!btn) return;

        // 包装成可展开组
        var group = document.createElement('div');
        group.className = 'sidebar-cat-group';
        group.setAttribute('data-category', parentName);

        btn.parentNode.insertBefore(group, btn);
        group.appendChild(btn);

        var toggle = document.createElement('button');
        toggle.className = 'sidebar-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', '展开' + parentName + '子分类');
        toggle.innerHTML = '▾';
        group.appendChild(toggle);

        var list = document.createElement('div');
        list.className = 'sidebar-subcats';
        list.hidden = true;

        subcatSlugs.forEach(function (subSlug) {
            var subName = subcatMap[subSlug].name;
            var a = document.createElement('a');
            a.className = 'sidebar-subcat';
            a.href = '#subcat-' + parentSlug + '-' + subSlug;
            a.dataset.parent = parentSlug;
            a.dataset.subcat = subSlug;
            a.textContent = subName;
            list.appendChild(a);
        });

        group.appendChild(list);

        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            var expanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', String(!expanded));
            list.hidden = expanded;
            toggle.classList.toggle('open', !expanded);
        });
    });
}

// ── 子类目联动同步：点击红框 pill 或左侧子类目，过滤该分类宫格 + 高亮 pill + 高亮侧边栏 ──
function initSubcatSync() {
    if (!window.__SUBCATEGORIES__) return;

    function getStickyOffset() {
        var offset = 0;
        ['.header', '.global-nav', '.search-bar-below-nav'].forEach(function (sel) {
            var el = document.querySelector(sel);
            if (el) {
                var style = window.getComputedStyle(el);
                if (style.position === 'sticky' || style.position === 'fixed' || style.position === '-webkit-sticky') {
                    offset += el.getBoundingClientRect().height;
                }
            }
        });
        return offset + 16;
    }

    function getSectionByParent(parentSlug) {
        var subs = window.__SUBCATEGORIES__;
        if (!subs || !subs[parentSlug]) return null;
        var name = subs[parentSlug].name;
        return document.getElementById(buildCategoryId(name));
    }

    // 供外部（如左侧分类点击）调用：清除该 section 的子分类过滤
    window.resetSectionFilter = function (section) {
        if (!section) return;
        section.querySelectorAll('.tool-card').forEach(function (c) { c.style.display = ''; });
        section.querySelectorAll('.subcat-pill').forEach(function (p) { p.classList.remove('active'); });
        section.dataset.activeSubcat = '';
    };

    function applyFilter(parentSlug, subSlug) {
        var section = getSectionByParent(parentSlug);
        if (!section) return;
        // v6: 折叠态下先展开该分类，保证子类目过滤能看到全量卡片
        var cat = section.getAttribute('data-cat');
        if (cat && window.__CAT_VIEW__ && !window.__CAT_VIEW__.expanded[cat] && !window.__CAT_VIEW__.expandedAll && !window.__CAT_VIEW__.searchMode) {
            window.__CAT_VIEW__.expanded[cat] = true;
            renderCategorizedSections(window.__ALL_TOOLS__ || []);
            section = getSectionByParent(parentSlug);
            if (!section) return;
        }
        var cards = section.querySelectorAll('.tool-card');
        cards.forEach(function (card) {
            if (!subSlug || card.dataset.subcat === subSlug) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        // 高亮当前 section 内的 pill
        section.querySelectorAll('.subcat-pill').forEach(function (pill) {
            pill.classList.toggle('active', pill.dataset.subcat === subSlug);
        });
        // 高亮侧边栏
        document.querySelectorAll('.sidebar-subcat').forEach(function (a) {
            a.classList.toggle('active', a.dataset.parent === parentSlug && a.dataset.subcat === subSlug);
        });
        section.dataset.activeSubcat = subSlug || '';
    }

    function scrollToSection(section) {
        var offset = getStickyOffset();
        var top = section.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: top, behavior: 'smooth' });
    }

    // 统一点击处理：红框 pills + 侧边栏子类目
    document.body.addEventListener('click', function (e) {
        var el = e.target;
        while (el && el !== document.body) {
            if (el.classList && (el.classList.contains('subcat-pill') || el.classList.contains('sidebar-subcat'))) {
                e.preventDefault();
                var parentSlug = el.dataset.parent;
                var subSlug = el.dataset.subcat;
                if (!parentSlug || !subSlug) return;
                var section = getSectionByParent(parentSlug);
                if (!section) return;
                applyFilter(parentSlug, subSlug);
                if (el.classList.contains('sidebar-subcat')) {
                    scrollToSection(section);
                }
                return;
            }
            el = el.parentNode;
        }
    });

    // 处理页面带锚点进入
    if (location.hash && location.hash.indexOf('#subcat-') === 0) {
        var parts = location.hash.slice(1).split('-');
        if (parts.length >= 3) {
            var subSlug = parts.pop();
            var parentSlug = parts.slice(1).join('-');
            setTimeout(function () {
                var section = getSectionByParent(parentSlug);
                if (section) { applyFilter(parentSlug, subSlug); scrollToSection(section); }
            }, 100);
        }
    }
}

// ── 紧凑卡片悬停简介（v6.4）：鼠标悬停小卡片弹出基本信息 ──
function initToolPreview() {
    // 触屏设备无 hover，跳过
    try {
        if (window.matchMedia && window.matchMedia('(hover: none)').matches) return;
    } catch (e) {}

    var preview = document.getElementById('toolPreview');
    if (!preview) {
        preview = document.createElement('div');
        preview.id = 'toolPreview';
        preview.className = 'tool-preview';
        preview.style.display = 'none';
        document.body.appendChild(preview);
    }

    var map = {};
    (window.__ALL_TOOLS__ || []).forEach(function (t) { map[t.slug] = t; });

    document.addEventListener('mouseover', function (e) {
        var card = e.target.closest ? e.target.closest('.tool-card') : null;
        if (!card) { preview.style.display = 'none'; return; }
        var slug = card.dataset ? card.dataset.slug : null;
        if (!slug) {
            var host = card.closest ? card.closest('a[href]') : null;
            if (host) { var m = host.getAttribute('href').match(/\/tools\/([^\/]+)\//); slug = m ? m[1] : null; }
        }
        var t = map[slug];
        if (!t) { preview.style.display = 'none'; return; }

        preview.innerHTML = '';
        var name = document.createElement('div'); name.className = 'tp-name'; name.textContent = t.name || '';
        var cat = document.createElement('div'); cat.className = 'tp-cat'; cat.textContent = (t.category || '') + ' · ' + (t.price || '免费');
        var desc = document.createElement('p'); desc.className = 'tp-desc'; desc.textContent = t.description || '';
        var meta = document.createElement('div'); meta.className = 'tp-meta';
        meta.textContent = '评分 ' + (t.rating || '') + ' · 访问 ' + (t.visits || '0');
        preview.appendChild(name); preview.appendChild(cat); preview.appendChild(desc); preview.appendChild(meta);

        var r = card.getBoundingClientRect();
        preview.style.display = 'block';
        var pw = preview.offsetWidth, ph = preview.offsetHeight;
        var left = r.right + 10, top = r.top;
        if (left + pw > window.innerWidth - 8) left = r.left - pw - 10;
        if (left < 8) left = 8;
        if (top + ph > window.innerHeight - 8) top = window.innerHeight - ph - 8;
        if (top < 8) top = 8;
        preview.style.left = left + 'px';
        preview.style.top = top + 'px';
    });

    document.addEventListener('mouseout', function (e) {
        var card = e.target.closest ? e.target.closest('.tool-card') : null;
        if (!card) return;
        var to = e.relatedTarget;
        if (!to || !(to.closest && to.closest('.tool-card'))) {
            preview.style.display = 'none';
        }
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

    // 2. 初始化左侧子类目导航
    initSidebarSubcategories();

    // 3. 侧边导航滚动跳转
    initCategoryFilter();

    // 3.5 子类目联动同步（红框 pills + 左侧子类目，统一过滤+高亮+滚动）
    initSubcatSync();

    // 3. 搜索过滤
    initSearch(allTools);

    // 4. 内容Tab切换
    initContentTabs();

    // 5. 紧凑卡片悬停简介
    initToolPreview();
});

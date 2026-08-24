/* AI工具宝箱 收藏模块 v1（localStorage 本地收藏，无后端）
 * 首页/工具页收藏按钮 + 右下角收藏夹入口 + /favorites.html 收藏列表
 */
(function () {
    'use strict';
    var KEY = 'aitoolbox_favorites_v1';
    var HIST_KEY = 'aitoolbox_history_v1';

    function getHist() {
        try { return JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); } catch (e) { return []; }
    }
    function setHist(list) {
        try { localStorage.setItem(HIST_KEY, JSON.stringify(list)); } catch (e) {}
    }
    function recordHistory(slug) {
        if (!slug) return;
        var h = getHist();
        h = [slug].concat(h.filter(function (s) { return s !== slug; })).slice(0, 12);
        setHist(h);
    }

    function getFavs() {
        try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; }
    }
    function setFavs(list) {
        try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
    }
    function toggleFav(slug) {
        var list = getFavs();
        var i = list.indexOf(slug);
        if (i >= 0) { list.splice(i, 1); } else { list.push(slug); }
        setFavs(list);
        return list.indexOf(slug) >= 0;
    }
    function isFav(slug) { return getFavs().indexOf(slug) >= 0; }
    function countFavs() { return getFavs().length; }

    function slugFromCard(card) {
        if (card.dataset && card.dataset.slug) return card.dataset.slug;
        var host = card.closest ? card.closest('a[href]') : null;
        if (host) {
            var m = host.getAttribute('href').match(/\/tools\/([^\/]+)\//);
            if (m) return m[1];
        }
        var oc = card.getAttribute('onclick') || '';
        var m2 = oc.match(/\/tools\/([^\/]+)\//);
        return m2 ? m2[1] : null;
    }

    function makeStar(slug, active) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'fav-star' + (active ? ' active' : '');
        btn.setAttribute('data-slug', slug);
        btn.setAttribute('aria-label', '收藏 ' + slug);
        btn.title = active ? '取消收藏' : '收藏';
        btn.textContent = active ? '★' : '☆';
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var on = toggleFav(slug);
            btn.classList.toggle('active', on);
            btn.textContent = on ? '★' : '☆';
            btn.title = on ? '取消收藏' : '收藏';
            updateFAB();
            if (isFavoritesPage()) renderFavoritesPage();
        });
        return btn;
    }

    function bindCardStars() {
        document.querySelectorAll('.tool-card').forEach(function (card) {
            var host = card.closest ? card.closest('a[href]') : null;
            var container = host || card;
            if (container.querySelector('.fav-star')) return;
            var slug = slugFromCard(card);
            if (!slug) return;
            container.appendChild(makeStar(slug, isFav(slug)));
        });
    }

    function bindSlugButtons() {
        document.querySelectorAll('[data-fav-slug]').forEach(function (btn) {
            if (btn.dataset.favBound) return;
            btn.dataset.favBound = '1';
            var slug = btn.getAttribute('data-fav-slug');
            var update = function () {
                var on = isFav(slug);
                btn.classList.toggle('active', on);
                btn.textContent = (on ? '★ ' : '☆ ') + '收藏';
            };
            update();
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                toggleFav(slug);
                update();
                updateFAB();
                if (isFavoritesPage()) renderFavoritesPage();
            });
        });
    }

    function updateFAB() {
        if (isFavoritesPage()) return;
        var n = countFavs();
        var fab = document.getElementById('favFab');
        if (!fab) {
            fab = document.createElement('a');
            fab.id = 'favFab';
            fab.className = 'fav-fab';
            fab.href = '/favorites.html';
            fab.title = '我的收藏';
            document.body.appendChild(fab);
        }
        fab.innerHTML = '☆ <b>' + n + '</b>';
    }

    function isFavoritesPage() { return !!document.getElementById('favList'); }

    function renderFavoritesPage() {
        var listEl = document.getElementById('favList');
        if (!listEl) return;
        var slugs = getFavs();
        var tools = window.__ALL_TOOLS__ || [];
        if (!slugs.length) {
            listEl.innerHTML = '<div class="fav-empty">还没有收藏任何工具。<a href="/">去首页逛逛 →</a></div>';
            return;
        }
        var html = '';
        tools.forEach(function (t) {
            if (slugs.indexOf(t.slug) < 0) return;
            var icon;
            if (t.icon) {
                icon = '<img class="fav-page-logo" src="' + t.icon + '" alt="' + (t.name || '') + '" loading="lazy" width="44" height="44">';
            } else {
                icon = '<div class="fav-page-logo" style="display:flex;align-items:center;justify-content:center;background:' + (t.color || '#4f46e5') + ';color:#fff;">' + (t.emoji || (t.name || '?')[0]) + '</div>';
            }
            html += '<a class="fav-page-card" href="/tools/' + t.slug + '/">' +
                icon +
                '<div class="fav-page-info"><div class="fav-page-name">' + (t.name || '') + '</div>' +
                '<div class="fav-page-cat">' + (t.category || '') + ' · ' + (t.price || '') + '</div></div>' +
                '<button type="button" class="fav-page-remove" data-remove="' + t.slug + '">移除</button>' +
                '</a>';
        });
        listEl.innerHTML = html || '<div class="fav-empty">收藏的工具已下架。<a href="/">去首页看看 →</a></div>';
        listEl.querySelectorAll('[data-remove]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var slug = btn.getAttribute('data-remove');
                var list = getFavs();
                var i = list.indexOf(slug);
                if (i >= 0) { list.splice(i, 1); setFavs(list); }
                renderFavoritesPage();
            });
        });
    }

    function renderHistory() {
        var listEl = document.getElementById('historyList');
        var wrap = document.getElementById('historyWrap');
        if (!listEl || !wrap) return;
        var slugs = getHist();
        var tools = window.__ALL_TOOLS__ || [];
        var html = '';
        tools.forEach(function (t) {
            if (slugs.indexOf(t.slug) < 0) return;
            var icon;
            if (t.icon) {
                icon = '<img class="fav-page-logo" src="' + t.icon + '" alt="' + (t.name || '') + '" loading="lazy" width="44" height="44">';
            } else {
                icon = '<div class="fav-page-logo" style="display:flex;align-items:center;justify-content:center;background:' + (t.color || '#4f46e5') + ';color:#fff;">' + (t.emoji || (t.name || '?')[0]) + '</div>';
            }
            html += '<a class="fav-page-card" href="/tools/' + t.slug + '/">' + icon +
                '<div class="fav-page-info"><div class="fav-page-name">' + (t.name || '') + '</div>' +
                '<div class="fav-page-cat">' + (t.category || '') + ' · ' + (t.price || '') + '</div></div></a>';
        });
        listEl.innerHTML = html;
        wrap.style.display = html ? 'block' : 'none';
    }

    // P1-1（2026-08-09）：收藏导出 / 导入 / 复制清单（LocalStorage 数据可带走、可恢复）
    function initImportExport() {
        var exportBtn = document.getElementById('favExport');
        var copyBtn = document.getElementById('favCopy');
        var importBtn = document.getElementById('favImport');
        var fileInput = document.getElementById('favImportFile');
        if (!exportBtn || !importBtn || !fileInput) return;

        exportBtn.addEventListener('click', function () {
            var data = { site: 'aitoollab.cn', version: 1, exportedAt: new Date().toISOString(), slugs: getFavs() };
            var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'aitoollab-favorites.json';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
        });

        if (copyBtn) {
            copyBtn.addEventListener('click', function () {
                var tools = window.__ALL_TOOLS__ || [];
                var slugs = getFavs();
                var names = [];
                tools.forEach(function (t) {
                    if (slugs.indexOf(t.slug) >= 0) names.push(t.name || t.slug);
                });
                var text = names.length ? ('我在 AI工具宝箱 收藏的工具：\n' + names.join('、')) : '我还没有收藏工具';
                var done = function (ok) {
                    copyBtn.textContent = ok ? '已复制 ✓' : '复制失败';
                    setTimeout(function () { copyBtn.textContent = '复制清单'; }, 2000);
                };
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(function () { done(true); }, function () { fallbackCopy(text, done); });
                } else {
                    fallbackCopy(text, done);
                }
            });
        }

        importBtn.addEventListener('click', function () { fileInput.click(); });
        fileInput.addEventListener('change', function () {
            var file = fileInput.files && fileInput.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function () {
                try {
                    var data = JSON.parse(reader.result);
                    var slugs = Array.isArray(data) ? data : (data.slugs || []);
                    if (!Array.isArray(slugs)) throw new Error('bad format');
                    var merged = getFavs();
                    slugs.forEach(function (s) {
                        if (typeof s === 'string' && s && merged.indexOf(s) < 0) merged.push(s);
                    });
                    setFavs(merged);
                    renderFavoritesPage();
                    importBtn.textContent = '导入成功（' + merged.length + ' 个）';
                    setTimeout(function () { importBtn.textContent = '导入收藏'; }, 2000);
                } catch (e) {
                    alert('导入失败：文件格式不正确，请使用本站导出的 JSON 文件。');
                }
                fileInput.value = '';
            };
            reader.readAsText(file, 'utf-8');
        });
    }

    // P1-6（2026-08-09）：通用"复制链接"按钮（工具页 action-bar 使用）
    function bindCopyLinks() {
        document.querySelectorAll('[data-copy-link]').forEach(function (btn) {
            if (btn.dataset.copyBound) return;
            btn.dataset.copyBound = '1';
            var label = btn.getAttribute('data-label') || '复制链接';
            btn.addEventListener('click', function () {
                var url = location.href;
                var done = function (ok) {
                    btn.textContent = ok ? '已复制 ✓' : '复制失败';
                    setTimeout(function () { btn.textContent = label; }, 2000);
                };
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url).then(function () { done(true); }, function () { fallbackCopy(url, done); });
                } else {
                    fallbackCopy(url, done);
                }
            });
        });
    }

    function fallbackCopy(text, done) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        ta.remove();
        done(ok);
    }

    function init() {
        // 工具页：进入即记录最近浏览
        var pageSlug = document.querySelector('[data-fav-slug]');
        if (pageSlug) recordHistory(pageSlug.getAttribute('data-fav-slug'));
        bindCardStars();
        bindSlugButtons();
        updateFAB();
        initImportExport();
        bindCopyLinks();
        if (isFavoritesPage()) { renderFavoritesPage(); renderHistory(); }
        // 首页卡片点击：记录最近浏览（星标点击已阻止冒泡，不会误记）
        document.addEventListener('click', function (e) {
            var card = e.target.closest ? e.target.closest('.tool-card') : null;
            if (card) {
                var slug = slugFromCard(card);
                if (slug) recordHistory(slug);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
    window.addEventListener('aitools:rendered', function () {
        bindCardStars();
        bindSlugButtons();
        updateFAB();
    });
})();

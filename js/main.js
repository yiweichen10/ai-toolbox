// SEO网站 - 主入口脚本
// 首屏 12 个工具已在 HTML 内静态渲染，此脚本负责：
// 1. 懒加载剩余工具（用 IntersectionObserver 感知滚动触底）
// 2. 分类筛选（直接用内联的 window.__ALL_TOOLS__ 数据）
// 3. 搜索功能

document.addEventListener('DOMContentLoaded', () => {
    // 优先使用服务端内联数据，避免再次 fetch
    const allTools = window.__ALL_TOOLS__ || [];
    const remainingTools = window.__REMAINING_TOOLS__ || [];

    // 懒加载剩余工具（滚动到底部时追加）
    if (remainingTools.length > 0) {
        setupLazyLoadTools(remainingTools);
    }

    // 分类筛选
    initCategoryFilter(allTools);

    // 搜索
    initSearch(allTools);

    // 文章列表（内联渲染，不再 fetch）
    // 如果 articleList 为空则不重新渲染（已静态渲染）
});

// ─────────────────────────────────────
// 懒加载：在 toolsGrid 末尾放一个哨兵节点
// 当哨兵进入视口时，批量追加工具卡片
// ─────────────────────────────────────
function setupLazyLoadTools(tools) {
    const grid = document.getElementById('toolsGrid');
    if (!grid) return;

    // 当前已渲染数（首屏静态 12 个）
    let rendered = grid.querySelectorAll('.tool-card').length;
    const BATCH = 12; // 每次追加数量
    let queue = tools.slice(); // 剩余待渲染列表

    // 哨兵节点
    const sentinel = document.createElement('div');
    sentinel.id = 'lazyLoadSentinel';
    sentinel.style.cssText = 'height:1px;width:100%;';
    grid.after(sentinel);

    function loadBatch() {
        if (queue.length === 0) {
            observer.disconnect();
            sentinel.remove();
            return;
        }
        const batch = queue.splice(0, BATCH);
        const fragment = document.createDocumentFragment();
        batch.forEach((t, i) => {
            const card = createToolCard(t, rendered + i);
            fragment.appendChild(card);
        });
        grid.appendChild(fragment);
        rendered += batch.length;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                loadBatch();
            }
        });
    }, { rootMargin: '200px' }); // 提前 200px 触发

    observer.observe(sentinel);
}

function createToolCard(t, index) {
    const badge = t.badge ? `<span class="badge badge-${t.badge.type}">${t.badge.text}</span>` : '';
    const tags = (t.tags || []).map(tag => `<span class="tag ${tag.type || ''}">${tag.text}</span>`).join('');
    const article = document.createElement('article');
    article.className = 'tool-card fade-in';
    article.style.animationDelay = `${(index % 12) * 0.05}s`;
    article.onclick = () => { location.href = `/tools/${t.slug}/index.html`; };
    article.innerHTML = `
        <div class="tool-icon" style="background:${t.color};">${t.emoji}</div>
        <h4>${escapeHtml(t.name)} ${badge}</h4>
        <p class="desc">${escapeHtml(t.description)}</p>
        <div class="tags">${tags}</div>
        <div class="meta">
            <span class="rating">${t.rating}</span>
            <span class="visits">👁 ${t.visits}</span>
        </div>`;
    return article;
}

// ─────────────────────────────────────
// 分类筛选（覆盖渲染 toolsGrid）
// ─────────────────────────────────────
function initCategoryFilter(tools) {
    const btns = document.querySelectorAll('.cat-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const category = btn.dataset.category;
            const filtered = category === 'all' ? tools : tools.filter(t => t.category === category);
            renderTools(filtered);
        });
    });
}

function renderTools(toolsToRender) {
    const grid = document.getElementById('toolsGrid');
    if (!grid) return;
    // 移除懒加载哨兵
    const sentinel = document.getElementById('lazyLoadSentinel');
    if (sentinel) sentinel.remove();

    grid.innerHTML = toolsToRender.map((t, index) => `
        <article class="tool-card fade-in" style="animation-delay: ${index * 0.05}s;" onclick="location.href='/tools/${t.slug}/index.html'">
            <div class="tool-icon" style="background:${t.color};">${t.emoji}</div>
            <h4>${escapeHtml(t.name)} ${t.badge ? `<span class="badge badge-${t.badge.type}">${t.badge.text}</span>` : ''}</h4>
            <p class="desc">${escapeHtml(t.description)}</p>
            <div class="tags">${(t.tags || []).map(tag => `<span class="tag ${tag.type || ''}">${tag.text}</span>`).join('')}</div>
            <div class="meta">
                <span class="rating">${t.rating}</span>
                <span class="visits">👁 ${t.visits}</span>
            </div>
        </article>
    `).join('');
}

// ─────────────────────────────────────
// 搜索
// ─────────────────────────────────────
function initSearch(tools) {
    const searchBtn = document.querySelector('.search-box button');
    const searchInput = document.getElementById('searchInput');
    if (!searchBtn || !searchInput) return;

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(); });

    function performSearch() {
        const query = searchInput.value.trim().toLowerCase();
        if (!query) return;
        const results = tools.filter(t =>
            t.name.toLowerCase().includes(query) ||
            t.description.toLowerCase().includes(query) ||
            (t.tags || []).some(tag => tag.text.toLowerCase().includes(query))
        );
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
        const allBtn = document.querySelector('.cat-btn[data-category="all"]');
        if (allBtn) allBtn.classList.add('active');
        renderTools(results);
    }
}

// ─────────────────────────────────────
// 返回顶部按钮（内联兜底 + IIFE主逻辑）
// ─────────────────────────────────────
// 注意：index.html 内联了一个 fail-safe 版本，
// 这里是正式版本。如果此文件加载失败，内联版本仍能工作。
(function initBackToTop() {
    // 清除内联兜底版本的事件（避免重复绑定）
    const existingBtn = document.getElementById('backToTop');
    if (!existingBtn) return;

    // 克隆节点以移除内联事件监听器
    const btn = existingBtn.cloneNode(true);
    existingBtn.parentNode.replaceChild(btn, existingBtn);

    // 滚动超过 400px 时显示按钮
    let ticking = false;
    const onScroll = () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                if (window.scrollY > 400) {
                    btn.classList.add('visible');
                } else {
                    btn.classList.remove('visible');
                }
                ticking = false;
            });
            ticking = true;
        }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    // 初始检查（页面可能已经滚动了）
    onScroll();

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
})();

// ─────────────────────────────────────
// 工具函数
// ─────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// SEO网站 - 主入口脚本
// 负责加载文章数据、渲染列表、搜索、分类筛选

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // 加载文章数据
    const articles = await loadArticles();
    const tools = await loadTools();
    
    // 渲染最新文章
    renderArticles(articles.slice(0, 6));
    
    // 初始化分类筛选
    initCategoryFilter(tools);
    
    // 初始化搜索
    initSearch(tools);
}

async function loadArticles() {
    try {
        const res = await fetch('/data/articles.json');
        return await res.json();
    } catch {
        return [];
    }
}

async function loadTools() {
    try {
        const res = await fetch('/data/tools.json');
        return await res.json();
    } catch {
        return [];
    }
}

function renderArticles(articles) {
    const list = document.getElementById('articleList');
    if (!list) return;
    list.innerHTML = articles.map(a => `
        <li>
            <span class="date">${a.date}</span>
            <a class="title" href="/articles/${a.slug}/index.html">${a.title}</a>
        </li>
    `).join('');
}

function initCategoryFilter(tools) {
    const btns = document.querySelectorAll('.cat-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const category = btn.dataset.category;
            renderTools(category === 'all' ? tools : tools.filter(t => t.category === category));
        });
    });
}

function renderTools(toolsToRender) {
    const grid = document.getElementById('toolsGrid');
    if (!grid) return;
    grid.innerHTML = toolsToRender.map((t, index) => `
        <article class="tool-card fade-in" style="animation-delay: ${index * 0.05}s;" onclick="location.href='/tools/${t.slug}/index.html'">
            <div class="tool-icon" style="background:${t.color};">${t.emoji}</div>
            <h4>${t.name} ${t.badge ? `<span class="badge badge-${t.badge.type}">${t.badge.text}</span>` : ''}</h4>
            <p class="desc">${t.description}</p>
            <div class="tags">${t.tags.map(tag => `<span class="tag ${tag.type || ''}">${tag.text}</span>`).join('')}</div>
            <div class="meta">
                <span class="rating">⭐ ${t.rating}</span>
                <span class="visits">👁 ${t.visits}</span>
            </div>
        </article>
    `).join('');
}

function initSearch(tools) {
    const searchBtn = document.querySelector('.search-box button');
    const searchInput = document.getElementById('searchInput');
    if (!searchBtn) return;
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(); });
    
    function performSearch() {
        const query = searchInput.value.trim().toLowerCase();
        if (!query) return;
        const results = tools.filter(t => 
            t.name.toLowerCase().includes(query) || 
            t.description.toLowerCase().includes(query) ||
            t.tags.some(tag => tag.text.toLowerCase().includes(query))
        );
        // 清除分类按钮激活状态
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('.cat-btn[data-category="all"]').classList.add('active');
        renderTools(results);
    }
}

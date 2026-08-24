/*!
 * 工具点赞（口碑信号）v1（2026-08-08）
 * 每款工具行一个 👍 按钮：同浏览器只能点一次；服务器另有 IP 级去重与每日上限。
 * 点赞数会参与 AI 助手的“口碑分”排序。
 */
(function () {
  'use strict';
  if (window.__aiToolLikesLoaded) return;
  window.__aiToolLikesLoaded = true;

  var TOKEN_KEY = 'ai_like_token_v1';
  var LIKED_KEY = 'ai_liked_slugs_v1';
  var token = '';
  var liked = new Set();

  try {
    token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) {
      token = 't-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(TOKEN_KEY, token);
    }
    liked = new Set(JSON.parse(localStorage.getItem(LIKED_KEY) || '[]'));
  } catch (e) { /* 隐私模式等场景降级为仅 IP 去重 */ }

  function saveLiked() {
    try { localStorage.setItem(LIKED_KEY, JSON.stringify(Array.from(liked))); } catch (e) {}
  }

  function fmt(n) {
    return n >= 10000 ? (Math.round(n / 1000) / 10) + 'k' : String(n);
  }

  var btns = Array.prototype.slice.call(document.querySelectorAll('.tool-like[data-slug]'));
  if (!btns.length) return;

  // 初始化计数 + 本浏览器已赞状态
  fetch('/api/likes', { headers: { 'Accept': 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d || !d.ok) return;
      btns.forEach(function (b) {
        var slug = b.getAttribute('data-slug');
        var c = b.querySelector('.tool-like-count');
        if (c && d.likes && d.likes[slug]) c.textContent = fmt(d.likes[slug]);
        if (liked.has(slug)) b.classList.add('liked');
      });
    })
    .catch(function () {});

  function onClick(e) {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    var b = e.currentTarget;
    if (b.classList.contains('liked')) return; // 只赞不踩，避免刷数
    var slug = b.getAttribute('data-slug');
    var c = b.querySelector('.tool-like-count');
    var old = c ? parseInt(c.textContent, 10) : 0;

    b.classList.add('liked'); // 乐观更新
    if (c && !isNaN(old)) c.textContent = fmt(old + 1);

    fetch('/api/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug: slug, token: token })
    }).then(function (r) {
      return r.json().catch(function () { return {}; });
    }).then(function (d) {
      if (d && d.ok) {
        if (typeof d.likes === 'number' && c) c.textContent = fmt(d.likes);
        liked.add(slug);
        saveLiked();
      } else {
        b.classList.remove('liked');
        if (c && !isNaN(old)) c.textContent = fmt(old);
      }
    }).catch(function () {
      b.classList.remove('liked');
      if (c && !isNaN(old)) c.textContent = fmt(old);
    });
  }

  btns.forEach(function (b) {
    b.addEventListener('click', onClick);
    b.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick(e);
      }
    });
  });
})();

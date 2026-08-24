(function () {
  'use strict';

  /* ---------- 优先使用服务端 edge-tts（方案 B），失败回退浏览器原生 ---------- */
  var TTS_ENDPOINT = '/tts';
  var DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural';

  var useServer = true; // 默认走服务端统一音色

  /* ---------- 底部 Mini 播放条（单例） ---------- */
  var mini = null;
  function ensureMiniBar() {
    if (mini && mini.bar) return mini;
    var bar = document.createElement('div');
    bar.className = 'tts-mini';
    bar.setAttribute('aria-label', '语音朗读控制');
    bar.innerHTML =
      '<div class="tts-mini-icon"><span class="glyph">🎧</span></div>' +
      '<div class="tts-mini-info">' +
        '<div class="tts-mini-title"></div>' +
        '<div class="tts-mini-sub">' +
          '<span class="tts-mini-author"></span>' +
          '<span class="tts-mini-progress"><i></i></span>' +
          '<span class="tts-mini-time"></span>' +
        '</div>' +
      '</div>' +
      '<div class="tts-mini-ctrl">' +
        '<button class="tts-mini-toggle" title="暂停/继续" type="button">⏸</button>' +
        '<button class="tts-mini-close" title="停止并关闭" type="button">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    var titleEl = bar.querySelector('.tts-mini-title');
    var authorEl = bar.querySelector('.tts-mini-author');
    var progressEl = bar.querySelector('.tts-mini-progress > i');
    var timeEl = bar.querySelector('.tts-mini-time');
    var iconEl = bar.querySelector('.tts-mini-icon');
    var toggleBtn = bar.querySelector('.tts-mini-toggle');
    var closeBtn = bar.querySelector('.tts-mini-close');

    toggleBtn.addEventListener('click', function () { togglePlay(); });
    closeBtn.addEventListener('click', function () { stop(); });

    /* ---------- 拖拽 + 位置记忆（自由停靠，不贴边） ---------- */
    initDraggable(bar, iconEl);

    mini = {
      bar: bar, titleEl: titleEl, authorEl: authorEl,
      progressEl: progressEl, timeEl: timeEl, iconEl: iconEl,
      toggleBtn: toggleBtn, closeBtn: closeBtn
    };
    return mini;
  }

  /* ---------- 拖拽逻辑：Pointer 事件（鼠标/触摸通用），自由停靠 + localStorage 记忆 ---------- */
  function initDraggable(bar, iconEl) {
    var KEY = 'tts-mini-pos';
    try {
      var saved = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (saved && typeof saved.left === 'number' && typeof saved.top === 'number') {
        bar.style.right = 'auto';
        bar.style.bottom = 'auto';
        bar.style.left = saved.left + 'px';
        bar.style.top = saved.top + 'px';
      }
    } catch (e) { /* localStorage 不可用时忽略 */ }

    var dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
    bar.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.tts-mini-ctrl')) return; // 按钮不触发拖拽
      dragging = true;
      bar.classList.add('dragging');
      var r = bar.getBoundingClientRect();
      bar.style.right = 'auto';
      bar.style.bottom = 'auto';
      bar.style.left = r.left + 'px';
      bar.style.top = r.top + 'px';
      sx = e.clientX; sy = e.clientY; ox = r.left; oy = r.top;
      try { bar.setPointerCapture(e.pointerId); } catch (err) {}
    });
    bar.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var nx = ox + (e.clientX - sx), ny = oy + (e.clientY - sy);
      nx = Math.max(4, Math.min(nx, window.innerWidth - bar.offsetWidth - 4));
      ny = Math.max(4, Math.min(ny, window.innerHeight - bar.offsetHeight - 4));
      bar.style.left = nx + 'px';
      bar.style.top = ny + 'px';
    });
    function endDrag() {
      if (!dragging) return;
      dragging = false;
      bar.classList.remove('dragging');
      try {
        localStorage.setItem(KEY, JSON.stringify({ left: bar.offsetLeft, top: bar.offsetTop }));
      } catch (e) {}
    }
    bar.addEventListener('pointerup', endDrag);
    bar.addEventListener('pointercancel', endDrag);
  }

  function showMini(title, author) {
    ensureMiniBar();
    mini.titleEl.textContent = title || '正在朗读';
    mini.authorEl.textContent = author || '';
    mini.bar.classList.add('show');
    document.body.classList.add('tts-mini-open');
  }

  function hideMini() {
    if (!mini) return;
    mini.bar.classList.remove('show');
    document.body.classList.remove('tts-mini-open');
    mini.progressEl.style.width = '0%';
    mini.timeEl.textContent = '';
    mini.toggleBtn.textContent = '⏸';
  }

  function updateMiniBtn(paused) {
    if (!mini) return;
    mini.toggleBtn.textContent = paused ? '▶' : '⏸';
    if (mini.iconEl) mini.iconEl.classList.toggle('paused', !!paused);
  }

  function updateMiniProgress(percent, timeText) {
    if (!mini) return;
    mini.progressEl.style.width = Math.max(0, Math.min(100, percent)) + '%';
    mini.timeEl.textContent = timeText || '';
  }

  /* ---------- 朗读状态 ---------- */
  var state = {
    container: null, blocks: [], idx: -1, started: false, paused: false,
    current: null, audio: null, totalChars: 0, elapsedChars: 0
  };

  function formatTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' + s : s);
  }

  function getBlocks(container) {
    var sel = 'p,li,h2,h3,h4,blockquote,td,pre';
    var nodes = container.querySelectorAll(sel);
    var firstP = container.querySelector('p');
    var list = [];
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.closest && n.closest('.tts-bar')) continue;
      if (n.closest && n.closest('.tts-skip')) continue;
      if (n.closest && n.closest('.related-tools')) continue;
      if (n.closest && n.closest('.article-toc')) continue;
      if (n.closest && n.closest('.table-of-contents')) continue;
      if (firstP && n.nodeName.toLowerCase() === 'blockquote' && (firstP.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_PRECEDING)) continue;
      var text;
      if (n.querySelector && n.querySelector('.tts-bar')) {
        var clone = n.cloneNode(true);
        var barInClone = clone.querySelector('.tts-bar');
        if (barInClone) barInClone.remove();
        text = (clone.textContent || '').replace(/\s+/g, ' ').trim();
      } else {
        text = (n.textContent || '').replace(/\s+/g, ' ').trim();
      }
      if (text.length < 2) continue;
      list.push({ el: n, text: text });
    }
    return list;
  }

  function highlight(el) {
    if (state.current) state.current.classList.remove('tts-active');
    state.current = el;
    if (state.current && state.current.scrollIntoView) {
      state.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (state.current) state.current.classList.add('tts-active');
  }

  function clearHL() {
    if (state.current) state.current.classList.remove('tts-active');
    state.current = null;
  }

  /* ---------- 服务端 TTS（方案 B）：逐段 fetch MP3 + audio 播放 ---------- */
  function speakFrom(i) {
    if (!state.started) return;
    if (i >= state.blocks.length) { finish(); return; }
    state.idx = i;
    var b = state.blocks[i];
    highlight(b.el);
    state.elapsedChars += b.text.length;

    if (state.audio) { try { state.audio.pause(); } catch (e) {} }

    var audio = new Audio();
    state.audio = audio;
    var url = TTS_ENDPOINT + '?voice=' + encodeURIComponent(DEFAULT_VOICE) +
              '&text=' + encodeURIComponent(b.text);
    audio.src = url;
    audio.preload = 'auto';

    audio.addEventListener('timeupdate', function () {
      if (!state.started) return;
      var cur = audio.currentTime || 0;
      var dur = audio.duration || 0;
      var blockRatio = dur > 0 ? cur / dur : 0;
      var doneChars = state.elapsedChars - b.text.length + Math.floor(b.text.length * blockRatio);
      var pct = state.totalChars > 0 ? (doneChars / state.totalChars) * 100 : 0;
      var remainSec = Math.max(0, dur - cur) + estimateRemainAfter(i);
      updateMiniProgress(pct, '-' + formatTime(remainSec));
    });
    audio.addEventListener('ended', function () {
      if (state.started) speakFrom(i + 1);
    });
    audio.addEventListener('error', function () {
      // 单段失败不阻断全文，跳下一段；连续失败则整体降级
      if (state.started) speakFrom(i + 1);
    });

    audio.play().catch(function () { if (state.started) speakFrom(i + 1); });
  }

  function estimateRemainAfter(i) {
    var sum = 0;
    for (var k = i + 1; k < state.blocks.length; k++) {
      // edge-tts 中文约 4.3 字/秒
      sum += state.blocks[k].text.length / 4.3;
    }
    return sum;
  }

  /* ---------- 浏览器原生 TTS（回退方案，仅当服务端不可用） ---------- */
  function pickVoice(langPrefix) {
    if (!('speechSynthesis' in window)) return null;
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) return null;
    var isZh = (langPrefix || '').toLowerCase().indexOf('zh') === 0;
    if (isZh) {
      var order = ['xiaoxiao', 'yunxi', 'yunjian', 'xiaoyi', 'xiaohan', 'xiaomeng'];
      for (var k = 0; k < order.length; k++) {
        var m = voices.filter(function (v) {
          var n = (v.name || '').toLowerCase();
          return v.lang && v.lang.toLowerCase().indexOf('zh') === 0 &&
            (n.indexOf('microsoft') >= 0 || n.indexOf('edge') >= 0 || n.indexOf('neural') >= 0) &&
            n.indexOf(order[k]) >= 0;
        });
        if (m.length) return m[0];
      }
    }
    return null;
  }

  function speakNative(i) {
    if (!state.started || !('speechSynthesis' in window)) return;
    if (i >= state.blocks.length) { finish(); return; }
    state.idx = i;
    var b = state.blocks[i];
    highlight(b.el);
    state.elapsedChars += b.text.length;
    var u = new SpeechSynthesisUtterance(b.text);
    u.lang = 'zh-CN';
    var v = pickVoice('zh-CN');
    if (v) u.voice = v;
    u.onend = function () { if (state.started) speakNative(i + 1); };
    u.onerror = function () { if (state.started) speakNative(i + 1); };
    state.audio = u;
    window.speechSynthesis.speak(u);
  }

  function start(container, playBtn) {
    if (state.started) { togglePlay(); return; }
    state.container = container;
    var isZh = /^zh/i.test(document.documentElement.lang || 'en');
    var L = isZh
      ? { play: '🎧 听全文', pause: '⏸ 暂停', resume: '▶ 继续', stop: '⏹ 停止' }
      : { play: '🎧 Listen', pause: '⏸ Pause', resume: '▶ Resume', stop: '⏹ Stop' };

    state.blocks = getBlocks(container);
    if (!state.blocks.length) return;

    state.totalChars = 0;
    for (var i = 0; i < state.blocks.length; i++) state.totalChars += state.blocks[i].text.length;
    state.elapsedChars = 0;
    state.started = true;
    state.paused = false;

    var h1 = document.querySelector('h1') || document.querySelector('h1.article-title');
    var title = h1 ? (h1.textContent || '').trim() : (document.title || '正在朗读');
    var authorEl = document.querySelector('[itemprop="author"] [itemprop="name"]');
    var author = authorEl ? (authorEl.textContent || '').trim() : '';

    showMini(title, author);
    updateMiniBtn(false);
    if (playBtn) playBtn.textContent = L.pause;

    if (useServer) {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      speakFrom(0);
    } else {
      speakNative(0);
    }
  }

  function togglePlay() {
    if (!state.started) return;
    if (useServer) {
      var a = state.audio;
      if (!a) return;
      if (a.paused) { a.play(); state.paused = false; updateMiniBtn(false); }
      else { a.pause(); state.paused = true; updateMiniBtn(true); }
    } else {
      if (!('speechSynthesis' in window)) return;
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume(); state.paused = false; updateMiniBtn(false);
      } else if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause(); state.paused = true; updateMiniBtn(true);
      }
    }
  }

  function stop() {
    state.started = false;
    state.paused = false;
    if (useServer) {
      if (state.audio) { try { state.audio.pause(); } catch (e) {} state.audio = null; }
    } else if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    clearHL();
    hideMini();
    var bars = document.querySelectorAll('.tts-bar');
    for (var i = 0; i < bars.length; i++) {
      var btn = bars[i].querySelector('.tts-btn');
      if (btn) {
        var isZh = /^zh/i.test(document.documentElement.lang || 'en');
        btn.textContent = isZh ? '🎧 听全文' : '🎧 Listen';
      }
    }
  }

  function finish() {
    state.started = false;
    if (state.audio) { try { state.audio.pause(); } catch (e) {} state.audio = null; }
    hideMini();
    var bars = document.querySelectorAll('.tts-bar');
    for (var i = 0; i < bars.length; i++) {
      var btn = bars[i].querySelector('.tts-btn');
      if (btn) {
        var isZh = /^zh/i.test(document.documentElement.lang || 'en');
        btn.textContent = isZh ? '🎧 听全文' : '🎧 Listen';
      }
    }
  }

  function createBar(container) {
    var bar = document.createElement('span');
    bar.className = 'tts-bar';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tts-btn tts-play';
    var isZh = /^zh/i.test(document.documentElement.lang || 'en');
    btn.textContent = isZh ? '🎧 听全文' : '🎧 Listen';
    bar.appendChild(btn);

    var authorSlot = container.querySelector('.article-authorbar .author-tts-slot');
    if (authorSlot) {
      authorSlot.appendChild(bar);
    } else {
      var firstP = container.querySelector('p');
      if (firstP) {
        firstP.insertBefore(bar, firstP.firstChild);
      } else {
        var fb = container.querySelector('h3') || container.querySelector('h2');
        if (fb) fb.appendChild(bar);
        else container.insertBefore(bar, container.firstChild);
      }
    }

    btn.addEventListener('click', function () { start(container, btn); });
    return bar;
  }

  function initContainer(container) {
    if (container.__ttsReady) return;
    container.__ttsReady = true;
    createBar(container);
  }

  function init() {
    ensureMiniBar();
    var targets = document.querySelectorAll('[data-tts]');
    for (var i = 0; i < targets.length; i++) {
      initContainer(targets[i]);
    }
  }

  function tryInit() { init(); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInit);
  } else {
    tryInit();
  }
})();

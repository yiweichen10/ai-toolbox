/*!
 * AI 工具助手挂件 v1（2026-08-08）
 * 位置：/tools/ 页左下角悬浮按钮 + 抽屉式对话面板
 * 后端：/api/chat（同源，服务端代理 LLM（千问/GLM），Key 不外泄）
 * 说明：本挂件只处理「选工具」类问题，答案基于本站工具库检索结果，由 LLM 生成。
 */
(function () {
  'use strict';
  if (window.__aiToolAssistantLoaded) return;
  window.__aiToolAssistantLoaded = true;

  var API = '/api/chat';
  var HEALTH = '/api/health';
  var CHIPS = [
    '推荐几款免费的 AI 写作工具',
    '视频生成哪个工具好用？',
    '哪个 AI 写代码最强？',
    '想找国内能直接用的 AI 对话'
  ];
  var history = [];
  var chipBtns = [];

  // ---------------- DOM 构建 ----------------
  var fab = document.createElement('button');
  fab.type = 'button';
  fab.id = 'aiFab';
  fab.className = 'ai-fab';
  fab.setAttribute('aria-label', 'AI 工具助手');
  fab.setAttribute('aria-haspopup', 'dialog');
  fab.title = 'AI 帮你选工具';
  fab.innerHTML =
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="4.2" y="7" width="15.6" height="11.5" rx="4"/>' +
    '<path d="M12 7V4.1"/>' +
    '<circle cx="12" cy="3.2" r="1.15" fill="#fff" stroke="none"/>' +
    '<circle cx="9.1" cy="12.2" r="1.65" fill="#fff" stroke="none"/>' +
    '<circle cx="14.9" cy="12.2" r="1.65" fill="#fff" stroke="none"/>' +
    '<path d="M9.1 15.7h5.8"/>' +
    '</svg>';

  var panel = document.createElement('div');
  panel.id = 'aiPanel';
  panel.className = 'ai-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'AI 工具助手');
  panel.hidden = true;
  panel.innerHTML =
    '<div class="ai-panel-head">' +
    '  <div class="ai-panel-title">AI 帮你选工具' +
    '    <span class="ai-panel-sub" id="aiPanelSub">正在连接…</span>' +
  '  </div>' +
  '  <span class="ai-panel-actions">' +
  '    <button type="button" class="ai-panel-clear" id="aiPanelClear" aria-label="清空对话" title="清空对话">清</button>' +
    '    <button type="button" class="ai-panel-close" id="aiPanelClose" aria-label="关闭">×</button>' +
    '  </span>' +
    '</div>' +
    '<div class="ai-msgs" id="aiMsgs"></div>' +
    '<div class="ai-chips" id="aiChips"></div>' +
    '<div class="ai-input-row">' +
    '  <input type="text" id="aiInput" class="ai-input" placeholder="例如：推荐一个免费的 AI 配音工具" maxlength="200" autocomplete="off">' +
    '  <button type="button" id="aiSend" class="ai-send">发送</button>' +
    '</div>' +
    '<div class="ai-foot">基于本站工具库检索 · AI 生成内容仅供参考</div>';

  document.body.appendChild(fab);
  document.body.appendChild(panel);

  var msgsEl = document.getElementById('aiMsgs');
  var chipsEl = document.getElementById('aiChips');
  var inputEl = document.getElementById('aiInput');
  var sendBtn = document.getElementById('aiSend');
  var subEl = document.getElementById('aiPanelSub');
  var closeBtn = document.getElementById('aiPanelClose');
  var clearBtn = document.getElementById('aiPanelClear');

  // 浏览器身份 token（与点赞共用同一标识，用于反馈去重/改票）
  var token = '';
  try {
    token = localStorage.getItem('ai_like_token_v1') || '';
    if (!token) {
      token = 't-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
      localStorage.setItem('ai_like_token_v1', token);
    }
  } catch (e) { /* 隐私模式降级 */ }

  // ---------------- 会话记忆（P1-6）----------------
  var HISTORY_KEY = 'ai_chat_history_v1';
  var MAX_HISTORY = 10;

  function saveHistory() {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(-MAX_HISTORY))); } catch (e) {}
  }

  function loadHistory() {
    try {
      var h = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      if (!Array.isArray(h)) return false;
      var valid = h.filter(function (m) {
        return m && (m.role === 'user' || m.role === 'assistant') &&
          typeof m.content === 'string' && m.content;
      }).slice(-MAX_HISTORY);
      if (!valid.length) return false;
      history = valid;
      valid.forEach(function (m) { addMsg(m.role, m.content); });
      return true;
    } catch (e) { return false; }
  }

  function clearHistory() {
    history = [];
    try { localStorage.removeItem(HISTORY_KEY); } catch (e) {}
    msgsEl.innerHTML = '';
  }

  function buildChips(chips) {
    chipsEl.innerHTML = '';
    chipBtns = [];
    chips.forEach(function (text) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'ai-chip';
      b.textContent = text;
      b.addEventListener('click', function () { ask(text); });
      chipsEl.appendChild(b);
      chipBtns.push(b);
    });
  }

  // ---------------- 工具函数 ----------------
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function escRe(s) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // 把回答里出现的工具名自动变成详情页链接（后端下发 name->/tools/slug/ 映射）
  function addToolLinks(h, map) {
    var names = Object.keys(map || {});
    if (!names.length) return h;
    names.sort(function (a, b) { return b.length - a.length; });
    var lowerMap = {};
    names.forEach(function (n) { lowerMap[n.toLowerCase()] = n; });
    var re = new RegExp('(?<![A-Za-z0-9])(' + names.map(escRe).join('|') + ')(?![A-Za-z0-9])', 'gi');
    return h.split(/(<a\b[^>]*>[\s\S]*?<\/a>)/g).map(function (seg) {
      if (/^<a\b/.test(seg)) return seg;
      return seg.replace(re, function (m, name, offset, str) {
        var key = lowerMap[name.toLowerCase()];
        if (!key || !map[key]) return m;
        // 跳过 &amp; &lt; 等 HTML 实体里的误匹配
        if (offset > 0 && str.charAt(offset - 1) === '&' && str.charAt(offset + name.length) === ';') return m;
        return '<a href="' + map[key] + '" class="ai-link" target="_self">' + name + '</a>';
      });
    }).join('');
  }

  function renderMd(s, links) {
    var h = esc(s);
    // 兼容模型坏格式（2026-08-13）：模型偶尔输出 "工具名 [slug/]"（非标准 markdown 链接），
    // 直接归一化为站内详情页链接（只吃紧邻的短名称，避免把整句吞进链接文本）；
    // 标准格式 [工具名](/tools/slug/) 由下一行处理
    h = h.replace(/(^|[\s>：:，。；;、])([^\[\]\n<*：:，。；;、]{1,40}?)\s*\[([A-Za-z0-9._-]+)\/\]/g,
      function (m, sep, name, slug) {
        return sep + '<a href="/tools/' + slug + '/" class="ai-link" target="_self">' + name + '</a>';
      });
    h = h.replace(/\[([^\]]+)\]\((\/tools\/[^)]+)\)/g, '<a href="$2" class="ai-link" target="_self">$1</a>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    h = h.replace(/\n/g, '<br>');
    if (links) h = addToolLinks(h, links);
    // 名称已被 addToolLinks 加链后，吞掉紧跟的 "[slug/]" 残留（同一 slug 才吞，防误删）
    h = h.replace(/<a href="(\/tools\/([A-Za-z0-9._-]+)\/)"[^>]*>([^<]*)<\/a>(?:<\/b>)?\s*\[\2\/\]/g,
      function (m, href, slug, name) {
        return '<a href="' + href + '" class="ai-link" target="_self">' + name + '</a>';
      });
    return h;
  }

  function scrollBottom() {
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function addMsg(role, text, links) {
    var div = document.createElement('div');
    div.className = 'ai-msg ai-' + role;
    if (role === 'assistant') {
      div.innerHTML = renderMd(text, links);
    } else {
      div.textContent = text;
    }
    msgsEl.appendChild(div);
    scrollBottom();
    return div;
  }

  function addTyping() {
    var div = document.createElement('div');
    div.className = 'ai-msg ai-assistant ai-typing';
    div.innerHTML = '<span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>';
    msgsEl.appendChild(div);
    scrollBottom();
    return div;
  }

  function setBusy(b) {
    sendBtn.disabled = b;
    sendBtn.textContent = b ? '…' : '发送';
  }

  function renderStreaming(el, text) {
    el.className = 'ai-msg ai-assistant';
    el.innerHTML = renderMd(text);
    scrollBottom();
  }

  function appendNote(bubble, text) {
    var n = document.createElement('div');
    n.className = 'ai-note';
    n.textContent = text;
    bubble.appendChild(n);
    scrollBottom();
  }

  // ---------------- 回答反馈（P1-4）----------------
  function attachFeedback(bubble, answerId) {
    if (!answerId) return;
    var row = document.createElement('div');
    row.className = 'ai-feedback';
    row.innerHTML = '<span class="ai-fb-label">这个回答有帮助吗</span>' +
      '<button type="button" class="ai-fb-btn ai-fb-up" data-v="1">👍 有用</button>' +
      '<button type="button" class="ai-fb-btn ai-fb-down" data-v="-1">👎 没用</button>';
    bubble.appendChild(row);
    var btns = row.querySelectorAll('.ai-fb-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () {
        var btn = this;
        if (btn.classList.contains('sending')) return;
        var v = parseInt(btn.getAttribute('data-v'), 10);
        btn.classList.add('sending');
        fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answer_id: answerId, value: v, token: token })
        }).then(function (r) { return r.json().catch(function () { return {}; }); })
          .then(function (d) {
            btn.classList.remove('sending');
            if (d && d.ok) {
              for (var j = 0; j < btns.length; j++) {
                btns[j].classList.toggle('on', btns[j] === btn);
              }
            }
          }).catch(function () { btn.classList.remove('sending'); });
      });
    }
  }

  // ---------------- 问答主流程 ----------------
  var MAX_RETRY = 3;
  var RETRY_DELAYS = [2500, 5000, 10000];

  function isRetryable(err) {
    if (!err) return false;
    var m = String(err.message || '');
    return !!err.retryable || /429|503|繁忙|访问量过大|排队|请稍后/.test(m);
  }

  function renderQueueWait(typingEl, round) {
    typingEl.className = 'ai-msg ai-assistant ai-typing ai-queue';
    typingEl.innerHTML =
      '<span class="ai-queue-text">前面还有人在咨询，正在排队…（第 ' + round + ' 次重试）</span>' +
      '<span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>';
    scrollBottom();
  }

  function ask(text) {
    text = (text || '').trim();
    if (!text || sendBtn.disabled) return;
    history.push({ role: 'user', content: text });
    addMsg('user', text);
    setBusy(true);
    var typingEl = addTyping();

    attempt(0);

    function attempt(n) {
      var answerId = null;
      var notes = [];
      var linkMap = {};
      fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: history.slice(0, -1).slice(-6) })
      }).then(function (res) {
        if (!res.ok) {
          return res.json().catch(function () { return {}; }).then(function (d) {
            var err = new Error((d && d.error) || ('请求失败 (' + res.status + ')'));
            err.retryable = (res.status === 429 || res.status === 503);
            throw err;
          });
        }
        var reader = res.body.getReader();
        var decoder = new TextDecoder('utf-8');
        var buf = '';
        var answer = '';

        function pump() {
          return reader.read().then(function (r) {
            if (r.done) return answer;
            buf += decoder.decode(r.value, { stream: true });
            var blocks = buf.split('\n\n');
            buf = blocks.pop();
            blocks.forEach(function (block) {
              block.split('\n').forEach(function (line) {
                line = line.trim();
                if (line.indexOf('data:') !== 0) return;
                var payload = line.slice(5).trim();
                if (payload === '[DONE]') return;
                try {
                  var obj = JSON.parse(payload);
                  if (obj && typeof obj.content === 'string') {
                    answer += obj.content;
                    renderStreaming(typingEl, answer);
                  } else if (obj && obj.error) {
                    var e2 = new Error(obj.error);
                    e2.retryable = /429|繁忙|访问量过大/.test(obj.error);
                    throw e2;
                  }
                  if (obj && obj.answer_id) answerId = obj.answer_id;
                  if (obj && obj.note) notes.push(obj.note);
                  if (obj && obj.links && obj.links.map) linkMap = obj.links.map;
                } catch (e) {
                  if (e instanceof SyntaxError) { /* 忽略半包 JSON */ } else { throw e; }
                }
              });
            });
            return pump();
          });
        }
        return pump();
      }).then(function (full) {
        if (typingEl && typingEl.parentNode) typingEl.parentNode.removeChild(typingEl);
        if (full) {
          var bubble = addMsg('assistant', full, linkMap);
          if (notes.length) {
            for (var i = 0; i < notes.length; i++) appendNote(bubble, notes[i]);
          }
          attachFeedback(bubble, answerId);
        }
        history.push({ role: 'assistant', content: full || '' });
        saveHistory();
        setBusy(false);
      }).catch(function (err) {
        if (isRetryable(err) && n < MAX_RETRY) {
          renderQueueWait(typingEl, n + 1);
          setTimeout(function () { attempt(n + 1); }, RETRY_DELAYS[n]);
        } else {
          if (typingEl && typingEl.parentNode) typingEl.parentNode.removeChild(typingEl);
          addMsg('assistant', '抱歉，AI 助手暂时开小差了（' + err.message + '）。请稍后再试。');
          history.pop();
          saveHistory();
          setBusy(false);
        }
      });
    }
  }

  // ---------------- 开关与初始化 ----------------
  // 快捷问题条：支持滚轮横滑 + 按住拖拽（PC 上默认无法左右滑动）
  (function initChipsScroll() {
    var chips = chipsEl;
    var downX = 0;
    var startLeft = 0;
    var dragging = false;
    var moved = false;
    var suppressUntil = 0;

    chips.addEventListener('wheel', function (e) {
      if (chips.scrollWidth <= chips.clientWidth) return;
      e.preventDefault();
      chips.scrollLeft += (e.deltaY || e.deltaX);
    }, { passive: false });

    chips.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      downX = e.clientX;
      startLeft = chips.scrollLeft;
      moved = false;
      dragging = true;
      chips.classList.add('ai-chips-dragging');
      // 拖拽期间改监听 document：setPointerCapture 会把后续 click 的目标
      // 重定向到容器，导致快捷问题按钮上的点击回调永远不触发
      document.addEventListener('pointermove', onDragMove, true);
      document.addEventListener('pointerup', endDrag, true);
      document.addEventListener('pointercancel', endDrag, true);
    });

    function onDragMove(e) {
      if (!dragging) return;
      var dx = e.clientX - downX;
      if (Math.abs(dx) > 5) moved = true;
      chips.scrollLeft = startLeft - dx;
    }

    function endDrag() {
      if (!dragging) return;
      dragging = false;
      chips.classList.remove('ai-chips-dragging');
      document.removeEventListener('pointermove', onDragMove, true);
      document.removeEventListener('pointerup', endDrag, true);
      document.removeEventListener('pointercancel', endDrag, true);
      if (moved) suppressUntil = Date.now() + 350;
    }

    // 拖拽后不误触发现选的快捷问题
    chips.addEventListener('click', function (e) {
      if (Date.now() < suppressUntil) {
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);
  })();

  function openPanel() {
    panel.hidden = false;
    fab.classList.add('ai-fab-open');
    setTimeout(function () { inputEl.focus(); }, 80);
  }

  function closePanel() {
    panel.hidden = true;
    fab.classList.remove('ai-fab-open');
  }

  fab.addEventListener('click', function () {
    if (panel.hidden) { openPanel(); } else { closePanel(); }
  });
  closeBtn.addEventListener('click', closePanel);
  clearBtn.addEventListener('click', clearHistory);
  sendBtn.addEventListener('click', function () { ask(inputEl.value); inputEl.value = ''; });
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      ask(inputEl.value);
      inputEl.value = '';
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) closePanel();
  });

  // P2-8 详情页语境化提问：按当前工具生成快捷问题
  var ctxTool = document.body.getAttribute('data-ai-tool');
  if (ctxTool) {
    CHIPS = [
      ctxTool + ' 好用吗？适合什么人用？',
      ctxTool + ' 有免费版吗？',
      ctxTool + ' 有哪些替代工具？'
    ];
  }
  buildChips(CHIPS);

  // 恢复上次对话（P1-6）
  var restored = loadHistory();

  fetch(HEALTH, { headers: { 'Accept': 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d && d.ok) {
        if (d.mode === 'mock') {
          // 后端尚未接入模型 Key：暂不开放提问，配好 Key 后自动恢复
          subEl.textContent = '即将上线';
          inputEl.disabled = true;
          sendBtn.disabled = true;
          sendBtn.textContent = '待上线';
          chipBtns.forEach(function (b) { b.disabled = true; });
          if (!restored) addMsg('assistant', 'AI 助手正在做最后的准备，很快就能帮你选工具啦，先逛逛上面的工具列表吧 👀');
        } else {
          subEl.textContent = d.tools ? ('本站已收录 ' + d.tools + ' 款工具') : 'AI 在线';
          if (!restored) {
            addMsg('assistant',
              '你好，我是 AI 工具助手 👋 我能从本站 ' + (d.tools || '529') + ' 款工具里帮你快速挑出合适的。\n\n' +
              '你可以试试：\n' + CHIPS.map(function (c) { return '· ' + c; }).join('\n'));
          }
        }
      } else {
        subEl.textContent = '服务暂不可用';
        addMsg('assistant', 'AI 助手正在准备中，稍后再来试试吧。');
      }
    })
    .catch(function () {
      subEl.textContent = '服务暂不可用';
      addMsg('assistant', 'AI 助手正在准备中，稍后再来试试吧。');
    });
})();

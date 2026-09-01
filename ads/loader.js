/*
 * ads/loader.js — aitoollab.cn 广告 / 推广自动加载器
 * 职责：读取 /ads/config.json，按当前页面类型(data-page-type)把对应广告位 / CPS 推广卡
 *       的代码动态注入到页面合适位置。
 * 特点：
 *   - 广告/CPS代码全部放在服务器 ads/ 文件夹，修改后无需重建站点（fetch 带 no-store）
 *   - 增删广告位 / 调整位置，只改 config.json 即可，同样无需重建
 *   - 支持 AdSense / 联盟 / 自营 banner（自动执行 <script> 并去重外部库）
 *   - 注入的广告容器预留 min-height，避免布局抖动(CLS)
 *   - v2设计（2026-07-14）：嵌入式自然融合，无虚线框，无"广告位"占位标签
 *   - CPS推广卡（2026-07-14）：工具页按 data-category 注入品类相关的"立即体验"卡
 */
(function () {
  'use strict';

  // ⚠️ 路径去广告特征（2026-09-01）：原 /ads/ 前缀命中 uBlock/AdGuard 默认规则，
  // 实测约 57% 的页面访问未加载配置（08-31：真人PV 5275 → cps.json 仅 2258 次请求）。
  // 物理文件仍在服务器 ads/ 目录，由 nginx 的 location /reco/ 做 alias 映射，磁盘文件名未变。
  // 改动此处必须同步：① /etc/nginx/conf.d/aitoollab.conf 的 /reco/ 块
  //                   ② scripts/analyze_beacon.py 的 BEACON_RE
  var CONFIG_URL = '/reco/config.json';
  var CPS_JSON_URL = '/reco/data.json';
  var CPS_TPL_URL = '/reco/slots/cps-card.html';
  var STYLE_ID = 'ads-loader-style';
  var STYLE_CSS =
    /* 通用容器：完全透明，不做任何装饰 */
    '.ads-slot{display:block;width:100%;box-sizing:border-box;clear:both;}' +
    '.ads-slot-inner{display:block;}' +
    /* 标签：极简灰色小字，不抢眼 */
    '.ads-slot .ad-label{font-size:10px;color:#9ca3af;letter-spacing:.08em;margin-bottom:6px;text-align:center;}' +
    /* === 内容区顶部：文章开篇后的推荐横幅 === */
    '.ads-slot-content-top{margin:0 0 32px 0;}' +
    /* === 正文内嵌：与文章段落融为一体的推荐卡 === */
    '.ads-slot-in-article{margin:28px 0;padding:0;}' +
    /* === 侧边栏：匹配sidebar-card卡片风格 === */
    '.ads-slot-sidebar-top,.ads-slot-sidebar-mid,.ads-slot-sidebar-bottom{margin:0 0 18px 0;}' +
    '.ads-slot-sidebar-top .ad-slot-inner,.ads-slot-sidebar-mid .ad-slot-inner,.ads-slot-sidebar-bottom .ad-slot-inner{border-radius:14px;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,0.06),0 0 0 1px rgba(0,0,0,0.04);padding:18px;}' +
    /* === 内容底部：分割线+居中推荐 === */
    '.ads-slot-content-bottom{margin:40px 0 0 0;}' +
    /* === 页脚上方：通栏 === */
    '.ads-slot-footer{margin:0;}' +
    /* === 信息流卡片：匹配tool-card网格 === */
    '.ads-slot-in-feed-grid{}' +
    /* === CPS 推广卡片：品牌化精美推荐卡（2026-07-27 重设计）=== */
    '.ads-slot-cps{margin:0;}' +
    '.ads-slot-cps+.sidebar-card{margin-top:2px;}' +
    /* === 资讯页信息流 CPS 卡：第 4 条快讯之后，与 news-card 同列布局 === */
    '.ads-slot-cps-news{margin:22px 0 6px;}' +
    /* === 文章页 CPS 卡：桌面侧边栏顶部 / 移动正文第4段后，只显示其一 === */
    '.ads-slot-cps-article-inline{display:none;}' +
    '@media (max-width:768px){.ads-slot-cps-article-sidebar{display:none;}.ads-slot-cps-article-inline{display:block;margin:24px 0;}}' +
    /* === 工具页 CPS 卡：桌面侧边栏顶部 / 移动正文第2段后，只显示其一 === */
    '.ads-slot-cps-tool-inline{display:none;}' +
    '@media (max-width:768px){.ads-slot-cps-tool-sidebar{display:none;}.ads-slot-cps-tool-inline{display:block;margin:24px 0;}}' +
    '.cps-card{position:relative;display:block;border-radius:16px;overflow:hidden;background:#fff;' +
      'box-shadow:0 6px 22px rgba(15,23,42,.10),0 0 0 1px rgba(15,23,42,.05);' +
      'padding:18px 18px 20px;border-top:3px solid var(--cps-brand,#0284c7);' +
      'transition:transform .18s ease,box-shadow .18s ease;}' +
    '.cps-card:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(15,23,42,.16),0 0 0 1px rgba(15,23,42,.07);}' +
    '.cps-card-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}' +
    /* === 引流钩子福利条：数据里配了 hook 就显示（空则隐藏）=== */
    '.cps-card-hook{display:block;margin:0 0 12px;padding:9px 12px;border-radius:10px;' +
      'background:linear-gradient(135deg,#fff7ed,#ffedd5);border:1px solid #fed7aa;color:#c2410c;' +
      'font-size:12.5px;font-weight:700;line-height:1.45;text-align:center;letter-spacing:.02em;}' +
    '.cps-card-hook:empty{display:none;}' +
    /* 图片卡（官方 banner）下方的钩子条：与图片拉开间距 */
    '.cps-card-banner-wrap + .cps-card-hook{margin:12px 0 0;}' +
    '.cps-card-brand{display:flex;align-items:center;gap:8px;}' +
    '.cps-card-logo{width:30px;height:30px;display:flex;align-items:center;justify-content:center;border-radius:8px;' +
      'background:#f1f5f9;box-shadow:0 1px 3px rgba(15,23,42,.12),0 0 0 1px rgba(15,23,42,.06);overflow:hidden;}' +
    '.cps-card-logo-svg{display:block;width:24px;height:24px;}' +
    '.cps-card-logo-fallback{width:100%;height:100%;display:flex;align-items:center;justify-content:center;' +
      'font-size:15px;font-weight:800;color:#fff;line-height:1;' +
      'background:linear-gradient(135deg,var(--cps-brand,#0284c7),var(--cps-brand2,#0369a1));}' +
    '.cps-card-tag{font-size:10px;line-height:1;color:#fff;background:rgba(100,116,139,.6);padding:3px 7px;border-radius:6px;letter-spacing:.06em;}' +
    /* === 官方推广图卡片（腾讯等，含 Logo+文案，整卡可点击）=== */
    '.cps-card-banner-wrap{position:relative;display:block;line-height:0;}' +
    '.cps-card-imgonly{display:block;text-decoration:none;line-height:0;}' +
    '.cps-card-imgonly img{display:block;width:100%;height:auto;border-radius:14px;' +
      'box-shadow:0 6px 22px rgba(15,23,42,.10),0 0 0 1px rgba(15,23,42,.05);transition:transform .18s ease,box-shadow .18s ease;}' +
    '.cps-card-imgonly:hover img{transform:translateY(-2px);box-shadow:0 10px 30px rgba(15,23,42,.16),0 0 0 1px rgba(15,23,42,.07);}' +
    '.cps-card-banner-wrap .cps-card-tag{position:absolute;top:10px;right:12px;z-index:2;background:rgba(100,116,139,.72);}' +
    '.cps-card-brand-text{font-size:13px;font-weight:600;color:#0f172a;letter-spacing:-.01em;line-height:1;}' +
    '.cps-card-name{font-size:17px;font-weight:800;color:#0f172a;letter-spacing:-.01em;line-height:1.35;margin:0 0 6px;}' +
    '.cps-card-desc{font-size:12.5px;color:#64748b;line-height:1.55;margin:0 0 16px;}' +
    '.cps-card-btn{display:inline-flex;align-items:center;gap:6px;' +
      'background:linear-gradient(135deg,var(--cps-brand,#0284c7),var(--cps-brand2,#0369a1));' +
      'color:#fff;font-size:14px;font-weight:700;padding:11px 20px;border-radius:11px;text-decoration:none;' +
      'box-shadow:0 4px 14px rgba(2,132,199,.35);transition:filter .15s,transform .15s;}' +
    /* 按钮居中：整行 flex 居中，避免卡片右侧大面积留白（2026-08-13） */
    '.cps-card-btn-row{display:flex;justify-content:center;}' +
    '.cps-card-btn:hover{filter:brightness(1.07);transform:translateY(-1px);}' +
    '.cps-card-arrow{transition:transform .15s;}' +
    '.cps-card-btn:hover .cps-card-arrow{transform:translateX(3px);}' +
    /* 渠道品牌色（由 loader 按 network 加 class） */
    '.cps-net-aliyun{--cps-brand:#ff6a00;--cps-brand2:#ff8f3c;}' +
    '.cps-net-tencent{--cps-brand:#006eff;--cps-brand2:#2b8bff;}' +
    '.cps-net-baidu{--cps-brand:#2932e1;--cps-brand2:#4b54f0;}' +
    /* === 暗黑模式适配：CPS 推广卡 / 侧边栏广告容器（2026-08-13）=== */
    '[data-theme="dark"] .cps-card{background:#1e293b;box-shadow:0 6px 22px rgba(0,0,0,.4),0 0 0 1px rgba(148,163,184,.12);}' +
    '[data-theme="dark"] .cps-card-brand-text{color:#e2e8f0;}' +
    '[data-theme="dark"] .cps-card-name{color:#f1f5f9;}' +
    '[data-theme="dark"] .cps-card-desc{color:#94a3b8;}' +
    '[data-theme="dark"] .cps-card-hook{background:linear-gradient(135deg,#33291a,#4a3a1d);border-color:#8a6326;color:#fbbf24;}' +
    '[data-theme="dark"] .cps-card-logo{background:#334155;box-shadow:0 1px 3px rgba(0,0,0,.4),0 0 0 1px rgba(148,163,184,.15);}' +
    '[data-theme="dark"] .ads-slot-sidebar-top .ad-slot-inner,[data-theme="dark"] .ads-slot-sidebar-mid .ad-slot-inner,[data-theme="dark"] .ads-slot-sidebar-bottom .ad-slot-inner{background:#1e293b;box-shadow:0 2px 12px rgba(0,0,0,.35),0 0 0 1px rgba(148,163,184,.12);}' +
    '@media (max-width:768px){.ads-slot-cps{margin:0;}.ads-slot-cps+.sidebar-card{margin-top:0;}}' +
    '@media (max-width:768px){.ads-slot-sidebar-top,.ads-slot-sidebar-mid,.ads-slot-sidebar-bottom{display:none;}}';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = STYLE_CSS;
    document.head.appendChild(s);
  }

  function currentPageType() {
    var b = document.body;
    return (b && b.getAttribute('data-page-type')) || 'unknown';
  }

  function fetchText(url) {
    return fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'text/html,application/json' }
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    });
  }

  // 把可能含 <script> 的 HTML 注入容器；<script> 会真正执行（含外部库去重）
  function injectHTML(container, html) {
    var tmp = document.createElement('div');
    tmp.innerHTML = html;
    var nodes = Array.prototype.slice.call(tmp.childNodes);
    nodes.forEach(function (node) {
      if (node.nodeType === 1 && node.tagName.toLowerCase() === 'script') {
        var src = node.getAttribute('src');
        if (src && document.querySelector('script[src="' + src + '"]')) return; // 外部库去重
        var s = document.createElement('script');
        if (src) s.src = src;
        if (node.type) s.type = node.type;
        if (node.async) s.async = true;
        if (node.defer) s.defer = true;
        s.textContent = node.textContent;
        container.appendChild(s);
      } else {
        container.appendChild(node.cloneNode(true));
      }
    });
  }

  function placeWrapper(wrapper, target, position) {
    position = position || 'append';
    if (position === 'prepend') target.insertBefore(wrapper, target.firstChild);
    else if (position === 'append') target.appendChild(wrapper);
    else if (position === 'before') { if (target.parentNode) target.parentNode.insertBefore(wrapper, target); }
    else if (position === 'after') { if (target.parentNode) target.parentNode.insertBefore(wrapper, target.nextSibling); }
    else target.appendChild(wrapper);
  }

  function findTarget(selectors) {
    var list = Array.isArray(selectors) ? selectors : [selectors];
    for (var i = 0; i < list.length; i++) {
      try {
        var el = document.querySelector(list[i]);
        if (el) return el;
      } catch (e) { /* 非法选择器，跳过 */ }
    }
    return null;
  }

  function makeLabel(text) {
    if (!text) return null;
    var d = document.createElement('div');
    d.className = 'ad-label';
    d.textContent = text;
    return d;
  }

  function processSlot(id, slot, pageType, globalLabel) {
    if (slot.enabled === false) return Promise.resolve();
    if (!slot.pageTypes || slot.pageTypes.indexOf(pageType) === -1) return Promise.resolve();

    var target = findTarget(slot.target);
    if (!target) {
      if (pageType !== 'unknown') console.warn('[ads] 广告位 "' + id + '" 未找到目标元素，已跳过');
      return Promise.resolve();
    }

    var wrapper = document.createElement('div');
    wrapper.className = 'ads-slot ads-slot-' + id;
    wrapper.setAttribute('data-slot', id);
    if (slot.minHeight) {
      wrapper.style.minHeight = slot.minHeight + 'px';
    }
    if (slot.maxWidth) {
      wrapper.style.maxWidth = slot.maxWidth + 'px';
      wrapper.style.marginLeft = 'auto';
      wrapper.style.marginRight = 'auto';
    }

    var labelText = (slot.label !== undefined) ? slot.label : globalLabel;
    var lbl = makeLabel(labelText);
    if (lbl) wrapper.appendChild(lbl);

    var box = document.createElement('div');
    box.className = 'ad-slot-inner';
    wrapper.appendChild(box);

    if (slot.insertAfterIndex != null && slot.insertAfterIndex >= 0) {
      // 信息流广告：插到列表容器第 N 个子元素之后（N 越界则退化为末尾）
      var kids = target.children;
      var idx = slot.insertAfterIndex;
      if (idx >= kids.length) idx = Math.max(0, kids.length - 1);
      var ref = kids[idx];
      if (ref && ref.nextSibling) target.insertBefore(wrapper, ref.nextSibling);
      else target.appendChild(wrapper);
    } else {
      placeWrapper(wrapper, target, slot.position);
    }

    var url = slot.file || ('slots/' + id + '.html');
    if (url.indexOf('/') !== 0) url = '/reco/' + url;

    return fetchText(url).then(function (html) {
      if (!html || !html.trim()) return; // 空文件：保留预留空间，不报错
      injectHTML(box, html);
    }).catch(function (e) {
      console.warn('[ads] 加载广告位 "' + id + '" 失败：', e.message);
    });
  }

  /*
   * CPS 推广卡：工具页(tool) + 资讯页(news)生效
   * 工具页流程：读 data-category → 查 cps.json 的 by_category 取该品类渠道
   * 资讯页流程：读第一条快讯的栏目标签 → 查 by_news_category 取渠道（未命中用 default）
   * 文章页流程：读 data-category → 先查 by_category（AI对话等工具品类直接复用），
   *            再查 by_article_category（AI资讯/行业趋势等），未命中用 default
   * 共同流程：链接未配置({{占位符})则跳过 → 读 cps-card.html 模板替换占位符 →
   *          注入（工具页=侧边栏顶部/文章末尾；资讯页=第 N 条快讯之后）→ 曝光/点击上报百度统计
   */

  // 图片加载失败 → 替换为预渲染的文字卡（window 全局暴露，供 img onerror 回调）
  window.__cpsImgError = function (imgEl) {
    var card = imgEl.closest('.cps-card-imgonly');
    if (!card) return;
    card.outerHTML = window.__cpsTextFallback || '';
  };

  // 品牌 SVG Logo（源自 @lobehub/icons，MIT License）—— 内联，CSS 兜底卡无需外部图片
  function getBrandSvg(net) {
    var svgs = {
      tencent: '<svg class="cps-card-logo-svg" viewBox="0 0 24 24" width="26" height="26" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20.0483 17.1416C19.6945 17.4914 18.987 18.0161 17.7488 18.0161C17.2182 18.0161 16.5991 18.0161 16.3338 18.0161C15.98 18.0161 13.3268 18.0161 10.143 18.0161C12.4424 15.8298 14.3881 13.9932 14.565 13.8183C14.7419 13.6434 15.1841 13.2061 15.6263 12.8563C16.5107 12.0692 17.2182 11.9817 17.8373 11.9817C18.7217 11.9817 19.4292 12.3316 20.0483 12.8563C21.2864 13.9932 21.2864 16.0047 20.0483 17.1416ZM21.5518 11.457C20.6674 10.495 19.3408 9.88281 17.9257 9.88281C16.6875 9.88281 15.6263 10.3201 14.6534 11.0197C14.2997 11.3695 13.769 11.7194 13.3268 12.2441C12.9731 12.5939 5.36719 19.9401 5.36719 19.9401C5.80939 20.0276 6.34003 20.0276 6.78223 20.0276C7.22443 20.0276 16.0685 20.0276 16.4222 20.0276C17.1298 20.0276 17.6604 20.0276 18.191 19.9401C19.3408 19.8527 20.4905 19.4154 21.4633 18.5409C23.4975 16.6168 23.4975 13.381 21.5518 11.457Z" fill="#00A3FF"/><path d="M9.1701 10.9323C8.19726 10.2326 7.22442 9.88281 6.07469 9.88281C4.65965 9.88281 3.33304 10.495 2.44864 11.457C0.502952 13.4685 0.502952 16.6168 2.53708 18.6283C3.42148 19.4154 4.30589 19.8527 5.36717 19.9401L7.4013 18.0161C7.04754 18.0161 6.60533 18.0161 6.25157 18.0161C5.10185 17.9287 4.39433 17.5789 3.95212 17.1416C2.71396 15.9172 2.71396 13.9932 3.86368 12.7688C4.48277 12.1566 5.19029 11.8943 6.07469 11.8943C6.60533 11.8943 7.4013 11.9817 8.19726 12.7688C8.55102 13.1186 9.52386 13.8183 9.87763 14.1681H9.96607L11.2927 12.8563V12.7688C10.6736 12.1566 9.70075 11.3695 9.1701 10.9323Z" fill="#00C8DC"/><path d="M18.4564 8.74536C17.4836 6.12171 14.9188 4.28516 12.0003 4.28516C8.5511 4.28516 5.80945 6.82135 5.27881 9.96973C5.54413 9.96973 5.80945 9.88228 6.16321 9.88228C6.51697 9.88228 6.95917 9.96973 7.31294 9.96973C7.75514 7.78336 9.70082 6.20917 12.0003 6.20917C13.946 6.20917 15.6263 7.34608 16.4223 9.00773C16.4223 9.00773 16.5107 9.09518 16.5107 9.00773C17.1298 8.92027 17.8373 8.74536 18.4564 8.74536C18.4564 8.83282 18.4564 8.83282 18.4564 8.74536Z" fill="#006EFF"/></svg>',
      aliyun: '<svg class="cps-card-logo-svg" viewBox="0 0 24 24" width="26" height="26" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M14.752 4.64h5.274C22.242 4.64 24 6.475 24 8.691V15.8a3.947 3.947 0 01-3.974 3.975h-5.274l1.299-1.835 3.822-1.222c.688-.23 1.146-.918 1.146-1.605v-5.81c0-.687-.458-1.375-1.146-1.605L16.05 6.475l-1.3-1.835zM2.98 15.111c0 .688.46 1.376 1.147 1.606l3.822 1.146 1.3 1.835H3.974A3.947 3.947 0 010 15.723V8.69c0-2.216 1.758-4.05 3.975-4.05h5.273L7.95 6.474 4.127 7.697c-.688.23-1.146.918-1.146 1.606v5.808z" fill="#FF6A00"/><path d="M16.051 11.213H8.025v1.835h8.026v-1.835z" fill="#FF6A00"/></svg>',
      baidu: '<svg class="cps-card-logo-svg" viewBox="0 0 24 24" width="26" height="26" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M21.715 5.61l-3.983 2.31a.903.903 0 01-.896 0L12.44 5.384a.903.903 0 00-.897 0L7.156 7.92a.903.903 0 01-.896 0L2.276 5.617 12.002 0l9.713 5.61z" fill="#5BCA87"/><path d="M18.641 9.467a.89.89 0 00-.438.77v5.072a.896.896 0 01-.445.77l-4.428 2.51a.884.884 0 00-.445.777v4.607l4.429-2.536 5.31-3.047V7.157l-3.983 2.31z" fill="#EC5D3E"/><path d="M10.98 18.941a.936.936 0 00-.305-.352l-4.429-2.516a.903.903 0 01-.431-.764v-5.078a.89.89 0 00-.452-.757l-.451-.26L1.38 7.158V18.39l5.311 3.047L11.126 24v-4.608a.881.881 0 00-.146-.45z" fill="#2464F5"/></svg>'
    };
    if (net.indexOf('阿里云') !== -1) return svgs.aliyun;
    if (net.indexOf('腾讯') !== -1) return svgs.tencent;
    if (net.indexOf('百度') !== -1) return svgs.baidu;
    return '';
  }

  function processCps(pageType, afterIndex) {
    pageType = pageType || 'tool';
    var cat = (document.body && document.body.getAttribute('data-category')) || '';
    return fetchText(CPS_JSON_URL).then(function (txt) {
      var data;
      try { data = JSON.parse(txt); } catch (e) { return; }
      if (!data) return;
      var mapping = null;
      if (pageType === 'tool') {
        var _sm = location.pathname.match(/\/(tools|articles|news)\/([^/?#]+)/);
        var _sslug = _sm ? _sm[2] : '';
        mapping = (data.by_slug && _sslug && data.by_slug[_sslug]) ? data.by_slug[_sslug]
                : (data.by_category && data.by_category[cat]) ? data.by_category[cat]
                : data.default;
      } else if (pageType === 'news') {
        var tag = document.querySelector('.news-cards .news-card .news-cat-tag');
        var catLabel = tag ? (tag.textContent || '').trim() : '';
        mapping = (data.by_news_category && data.by_news_category[catLabel])
          ? data.by_news_category[catLabel] : data.default;
      } else if (pageType === 'article') {
        mapping = (data.by_category && data.by_category[cat]) ? data.by_category[cat]
                : (data.by_article_category && data.by_article_category[cat]) ? data.by_article_category[cat]
                : data.default;
      }
      if (!mapping) mapping = data.default;
      if (!mapping || !mapping.url) return;
      if (mapping.url.indexOf('{{') !== -1) return; // 链接未配置，跳过（避免展示无效链接）

      // 查找该渠道对应的 banner 图片
      var imgMap = data.images || {};
      var imgPath = imgMap[mapping.network] || '';
      var fullImgPath = imgPath;
      if (imgPath && imgPath.indexOf('/') !== 0) fullImgPath = '/reco/' + imgPath;

      return fetchText(CPS_TPL_URL).then(function (tpl) {
        if (!tpl || !tpl.trim()) return;
        // 按渠道决定品牌色 class
        var net = mapping.network || '';
        var netClass = net.indexOf('阿里云') !== -1 ? 'cps-net-aliyun'
                     : net.indexOf('腾讯') !== -1 ? 'cps-net-tencent'
                     : net.indexOf('百度') !== -1 ? 'cps-net-baidu' : '';
        // 品牌 SVG Logo（内联，无需外部图片）
        var logoHtml = getBrandSvg(net) || '<span class="cps-card-logo-fallback">' + (mapping.name ? mapping.name.charAt(0) : '') + '</span>';
        // 引流钩子（如"新用户赠 1 亿+ Tokens"）：条目可配 hook，未配则取 cps.json 顶层 hooks[渠道]
        var hookText = mapping.hook || (data.hooks && data.hooks[mapping.network]) || '';
        // 预渲染文字卡（主卡，CSS 渲染，品牌色随渠道变化）
        var textHtml = tpl
          .replace(/\{LOGO\}/g, logoHtml)
          .replace(/\{IMG\}/g, '')
          .replace(/\{HOOK\}/g, hookText)
          .replace(/\{NAME\}/g, mapping.name || '')
          .replace(/\{HEADLINE\}/g, mapping.headline || mapping.name || '')
          .replace(/\{CTA\}/g, mapping.cta || '立即体验')
          .replace(/\{URL\}/g, mapping.url || '#')
          .replace(/\{DESC\}/g, mapping.desc || '')
          .replace(/\{BRAND_TEXT\}/g, mapping.brandText || mapping.network || '');
        window.__cpsTextFallback = textHtml;

        // 主卡：有官方推广图则优先用图（含 Logo+文案，可信度高，整卡可点击）；无图降级 CSS 卡片
        var html;
        if (fullImgPath) {
          html = '<div class="cps-card-banner-wrap">'
            + '<span class="cps-card-tag">推广</span>'
            + '<a class="cps-card-imgonly" href="' + (mapping.url || '#') + '" target="_blank" rel="nofollow noopener sponsored">'
            + '<img src="' + fullImgPath + '" alt="' + (mapping.name || mapping.network || '') + '" width="800" height="450" loading="lazy" onerror="if(window.__cpsImgError)window.__cpsImgError(this)">'
            + '</a></div>'
            + (hookText ? '<div class="cps-card-hook">' + hookText + '</div>' : '');
        } else {
          html = textHtml;
        }

        var channel = mapping.network || '';
        // 曝光/点击双通道上报（2026-08-15）：
        // ① 自建 beacon → /reco/r.gif（2026-09-01 改路径规避拦截），nginx access log 留痕
        // ② 百度统计 _trackEvent（免费版无事件分析权限，仅备用，不依赖）
        // 曝光口径（2026-09-01 修正）：元素 ≥50% 进入视口并停留 ≥1s 才计一次（MRC viewable 标准）。
        //   ⚠️ 原实现用 offsetParent !== null，语义仅为"参与布局未被 display:none 隐藏"，
        //   与是否在视口内无关 → 用户没滚到也计曝光 → 分母虚高 → CTR 被系统性低估。勿改回。
        var CPS_BEACON_URL = '/reco/r.gif';
        function cpsBeacon(act) {
          try {
            var m = location.pathname.match(/\/(tools|articles|news)\/([^/?#]+)/);
            var slug = m ? m[2] : '';
            var src = CPS_BEACON_URL + '?act=' + encodeURIComponent(act)
              + '&ch=' + encodeURIComponent(channel)
              + '&pt=' + encodeURIComponent(pageType)
              + (slug ? '&slug=' + encodeURIComponent(slug) : '')
              + '&ts=' + Date.now();
            (new Image()).src = src;
          } catch (e) { /* beacon 失败不影响任何功能 */ }
        }
        function attachCpsTracking(w) {
          w.setAttribute('data-cps-channel', channel);
          // 曝光判定（2026-09-01 重写）：IntersectionObserver，≥50% 可见且持续 ≥1s 才计一次。
          // - 桌面/移动双占位天然去重：被 display:none 的那份永不进入视口，不会触发。
          // - 用户快速滑过不计数（timer 在移出视口时清除）。
          // - 老浏览器无 IntersectionObserver 时降级为"插入即计一次"，保证不丢数。
          var impressionSent = false;
          function sendImpression() {
            if (impressionSent) return;
            impressionSent = true;
            cpsBeacon('impression');
            try {
              if (window._hmt && window._hmt.push) {
                window._hmt.push(['_trackEvent', 'CPS', 'impression', channel + '|' + pageType]);
              }
            } catch (e) { /* 统计失败不影响展示 */ }
          }
          if (typeof window.IntersectionObserver !== 'function') {
            window.setTimeout(sendImpression, 0);
          } else {
            var dwellTimer = null;
            var io = new window.IntersectionObserver(function (entries) {
              for (var i = 0; i < entries.length; i++) {
                var e = entries[i];
                if (e.isIntersecting && e.intersectionRatio >= 0.5) {
                  if (!dwellTimer && !impressionSent) {
                    dwellTimer = window.setTimeout(function () {
                      dwellTimer = null;
                      sendImpression();
                    }, 1000);
                  }
                } else if (dwellTimer) {
                  window.clearTimeout(dwellTimer);
                  dwellTimer = null;
                }
              }
              if (impressionSent && dwellTimer === null) {
                try { io.disconnect(); } catch (e2) { /* 已断开 */ }
              }
            }, { threshold: [0, 0.5] });
            window.setTimeout(function () { io.observe(w); }, 0);
          }
          w.addEventListener('click', function (ev) {
            var link = ev.target && ev.target.closest ? ev.target.closest('a') : null;
            if (!link) return;
            cpsBeacon('click');
            try {
              if (window._hmt && window._hmt.push) {
                window._hmt.push(['_trackEvent', 'CPS', 'click', channel + '|' + pageType]);
              }
            } catch (e2) { /* 统计失败不影响跳转 */ }
          });
        }
        function makeCpsWrap(extraClass) {
          var w = document.createElement('div');
          w.className = 'ads-slot ads-slot-cps' + (netClass ? ' ' + netClass : '')
            + (extraClass ? ' ' + extraClass : '');
          var b = document.createElement('div');
          b.className = 'ad-slot-inner';
          b.innerHTML = html;
          w.appendChild(b);
          attachCpsTracking(w);
          return w;
        }
        function insertSidebarTop(el) {
          var sb = findTarget(['aside.page-sidebar']);
          if (!sb) return false;
          var ref = sb.firstChild;
          while (ref && ref.nodeType !== 1) ref = ref.nextSibling;
          if (ref) sb.insertBefore(el, ref); else sb.appendChild(el);
          return true;
        }
        function insertAfterNthP(el, n) {
          var p = findTarget(['article.article-body > p:nth-of-type(' + n + ')']);
          // 2026-08-31 修复：若目标段紧邻标题(h1-h4)，优先向后顺延到同段落块的下一 <p>；
          // 顺延被非 <p> 元素(ul/table/div)挡住时，改为把卡片插到该标题之前（上一段落块末尾），
          // 保证卡片永不落在"标题与其内容"之间切断阅读（工具页/文章页移动端均命中）
          var guard = 0;
          while (p && p.previousElementSibling && /^H[1-4]$/.test(p.previousElementSibling.tagName) && guard < 6) {
            var nextEl = p.nextElementSibling;
            if (nextEl && nextEl.tagName === 'P') { p = nextEl; guard++; continue; }
            var head = p.previousElementSibling;
            if (head && head.parentNode) { head.parentNode.insertBefore(el, head); return true; }
            break;
          }
          if (p && p.parentNode) { p.parentNode.insertBefore(el, p); return true; }
          var body = findTarget(['article.article-body']);
          if (body) { body.insertBefore(el, body.firstChild); return true; }
          return false;
        }

        // 资讯页：插到快讯流第 afterIndex 条之后（默认第 4 条，与 news-inline 广告位同位置语义，互不影响）
        if (pageType === 'news') {
          var cards = document.querySelector('.news-cards');
          if (cards) {
            var idx = (typeof afterIndex === 'number') ? afterIndex : 3;
            var ref = cards.children[idx];
            var wNews = makeCpsWrap('ads-slot-cps-news');
            if (ref && ref.nextSibling) cards.insertBefore(wNews, ref.nextSibling);
            else cards.appendChild(wNews);
          }
          return;
        }

        // 文章页：桌面端侧边栏顶部、移动端正文第 4 段后（CSS 互斥只显示其一）
        if (pageType === 'article') {
          insertSidebarTop(makeCpsWrap('ads-slot-cps-article-sidebar'));
          insertAfterNthP(makeCpsWrap('ads-slot-cps-article-inline'), 4);
          return;
        }

        // 工具页：桌面端侧边栏顶部、移动端正文第 afterIndex+1 段后（默认第 2 段，cps.tool.afterIndex 可调）
        if (pageType === 'tool') {
          insertSidebarTop(makeCpsWrap('ads-slot-cps-tool-sidebar'));
          var toolN = (typeof afterIndex === 'number') ? (afterIndex + 1) : 2;
          insertAfterNthP(makeCpsWrap('ads-slot-cps-tool-inline'), toolN);
          return;
        }

        // 兜底（其他页型）：侧边栏顶部或容器末尾
        var target = findTarget(['.page-sidebar', '.sidebar', 'article']);
        if (!target) return;
        var wOther = makeCpsWrap('');
        if (target.classList.contains('page-sidebar') || target.classList.contains('sidebar')) {
          var refOther = null;
          var nOther = target.firstChild;
          while (nOther) {
            if (nOther.nodeType === 1 && nOther !== wOther) {
              var csOther = window.getComputedStyle(nOther);
              if (csOther.display !== 'none') { refOther = nOther; break; }
            }
            nOther = nOther.nextSibling;
          }
          if (refOther) target.insertBefore(wOther, refOther);
          else target.appendChild(wOther);
        } else {
          target.appendChild(wOther);
        }
      });
    }).catch(function (e) {
      console.warn('[ads] CPS 加载失败：', e.message);
    });
  }

  function init() {
    injectStyle();
    fetchText(CONFIG_URL).then(function (txt) {
      var cfg;
      try { cfg = JSON.parse(txt); } catch (e) { console.warn('[ads] 配置文件解析失败', e); return; }
      var globalLabel = (cfg.label !== undefined) ? cfg.label : '广告';
      var pageType = currentPageType();
      var slots = cfg.slots || {};
      var tasks = [];
      Object.keys(slots).forEach(function (id) {
        tasks.push(processSlot(id, slots[id], pageType, globalLabel));
      });
      return Promise.all(tasks).then(function () {
        if (!cfg.cps) return;
        if (cfg.cps.enabled && pageType === 'tool') {
          return processCps('tool', cfg.cps.tool ? cfg.cps.tool.afterIndex : 1);
        }
        if (cfg.cps.news && cfg.cps.news.enabled && pageType === 'news') {
          return processCps('news', cfg.cps.news.afterIndex);
        }
        if (cfg.cps.article && cfg.cps.article.enabled && pageType === 'article') {
          return processCps('article', 0);
        }
      });
    }).catch(function (e) {
      console.warn('[ads] 配置加载失败', e.message);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

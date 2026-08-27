/* AI工具宝箱 Service Worker v5（2026-08-27 二次修：/tts /api /ads 纯网络不回退假响应，杜绝"读一段跳一段"）（2026-08-27 bump：HTML/JS/CSS 全部 network-only，
 * 杜绝 SW 缓存旧页面/旧 ?v=hash 资源导致朗读跳段、样式错乱）
 * 背景：v3 的 fetch 正则 /\.html?$/ 只匹配带后缀的页面，漏掉了目录型路由
 * （如 /tools/language-tool/），使旧 HTML（指向旧 JS 版本号）被缓存并在弱网回退时吐出。
 * 用途：
 *   1. 满足 PWA 安装条件（Chrome 要求注册 SW 才能安装/落桌面图标）；
 *   2. 仅预缓存根壳做离线兜底；所有动态资源（HTML/JS/CSS）一律走网络、永不缓存。
 * 策略：动态资源 network-only（失败仅回退预缓存根壳）；静态资源网络优先+缓存回退。
 */
var CACHE_NAME = 'aitoollab-cache-v5';
var PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/assets/icons/pwa-192.png',
  '/assets/icons/pwa-512.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_URLS).catch(function () {});
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

// 是否为「永不缓存、必须走网络的动态资源」（页面 HTML / js / css / API / TTS）
function isNetworkOnly(url) {
  var p = url.pathname;
  if (p.indexOf('/js/') === 0) return true;
  if (p.indexOf('/css/') === 0) return true;
  if (p === '/tts' || p.indexOf('/api/') === 0 || p.indexOf('/ads/') === 0) return true; // v5：动态端点绝不走缓存（失败回退假 HTML 会毒死 fetch→decode 链路，2026-08-27"读一段跳一段"根因之一）
  if (/\.html?$/.test(p)) return true;          // 带后缀的页面
  if (p === '/' || p.charAt(p.length - 1) === '/') return true; // 目录型路由（/ 、/tools/xxx/）
  return false;
}

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  // 只处理同源请求；跨域（广告/统计等）直接走网络，不缓存
  if (url.origin !== self.location.origin) return;

  if (isNetworkOnly(url)) {
    var p = url.pathname;
    // API/TTS/JS/CSS：纯网络，失败就是失败——绝不回退假响应（v5 修复）
    if (p === '/tts' || p.indexOf('/api/') === 0 || p.indexOf('/js/') === 0 || p.indexOf('/css/') === 0 || p.indexOf('/ads/') === 0) {
      event.respondWith(fetch(req));
      return;
    }
    // 页面：网络优先，失败仅回退预缓存根壳做离线兜底
    event.respondWith(fetch(req).catch(function () { return caches.match('/'); }));
    return;
  }

  // 静态资源（图片/字体等）：网络优先，失败回退缓存（用完整 req.url 含 query 作 key，避免 ?v= 串味）
  event.respondWith(
    fetch(req).then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE_NAME).then(function (cache) { cache.put(req.url, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(req.url).then(function (hit) { return hit || caches.match('/'); });
    })
  );
});

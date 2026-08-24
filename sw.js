/* AI工具宝箱 Service Worker v3（2026-08-22 bump：清掉 v2 旧缓存，解决移动端 SW 返回旧 CSS/JS 导致样式错乱）
 * 用途：
 *   1. 满足 PWA 安装条件（Chrome 要求注册 SW 才能安装/落桌面图标）；
 *   2. 基础离线兜底：网络优先，失败回退缓存。
 * 策略说明：网络优先 → 内容始终新鲜，缓存仅作离线/弱网兜底；
 * 更新缓存版本号（CACHE_NAME）即可全量刷新缓存。
 */
var CACHE_NAME = 'aitoollab-cache-v3';
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

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  // 只处理同源请求；跨域（广告/统计等）直接走网络，不缓存
  if (url.origin !== self.location.origin) return;
  // CSS/JS/HTML 全部走网络，不缓存也不回退（旧版预缓存的会污染 ?v=hash 后的新资源，
  // 这是 2026-08-22 移动端"样式丢失"的根因）
  var p = url.pathname;
  if (p.indexOf('/css/') === 0 || p.indexOf('/js/') === 0 || /\.html?$/.test(p)) {
    event.respondWith(fetch(req).catch(function () { return caches.match('/'); }));
    return;
  }
  // 网络优先，失败回退缓存（剥离 query 匹配预缓存，兼容 ?v= 版本号）
  event.respondWith(
    fetch(req).then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        var cacheKey = url.origin + url.pathname;
        var copy = res.clone();
        caches.open(CACHE_NAME).then(function (cache) {
          cache.put(cacheKey, copy);
        });
      }
      return res;
    }).catch(function () {
      return caches.match(url.origin + url.pathname).then(function (hit) {
        return hit || caches.match('/');
      });
    })
  );
});

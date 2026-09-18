// 行隅 PWA Service Worker v20
// 策略：页面 network-first（保证每日更新的岗位能及时看到）；图标/manifest cache-first
var CACHE = 'xingyu-v20';
var PRECACHE = [
  './',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];
self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){ return c.addAll(PRECACHE); }).then(function(){ return self.skipWaiting(); })
  );
});
self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){ if(k !== CACHE) return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});
self.addEventListener('fetch', function(e){
  var url = e.request.url;
  if(e.request.method !== 'GET') return;
  // 统计/外部资源不拦截
  if(url.indexOf('busuanzi') >= 0) return;
  var isPage = e.request.mode === 'navigate';
  if(isPage){
    // 页面：有网取最新，失败回退缓存
    e.respondWith(
      fetch(e.request).then(function(res){
        var copy = res.clone();
        caches.open(CACHE).then(function(c){ c.put('./', copy); });
        return res;
      }).catch(function(){
        return caches.match(e.request).then(function(m){ return m || caches.match('./'); });
      })
    );
    return;
  }
  // 其他静态资源：cache-first，后台更新
  e.respondWith(
    caches.match(e.request).then(function(hit){
      if(hit) return hit;
      return fetch(e.request).then(function(res){
        if(res.ok && url.indexOf(location.origin) === 0){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        }
        return res;
      });
    })
  );
});

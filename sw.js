const CACHE_NAME = 'ebook-reader-cache-v1.2';
const urlsToCache = [
  '/',
  '/index.html',
  '/reader.html',
  '/styles/main.css',
  '/styles/reader.css',
  '/scripts/jszip.min.js',
  '/scripts/epub.min.js',
  '/favicon.png'
];

// 安装 Service Worker 时，缓存核心文件
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        // 使用 addAll 来原子性地添加所有资源
        // 注意：要使用相对于域名的绝对路径
        const absoluteUrlsToCache = urlsToCache.map(url => {
            // 如果 URL 已经是完整的（例如，以 / 开头），则直接使用
            if (url.startsWith('/')) {
                // 假设部署在根目录，对于 GitHub Pages，需要处理仓库名路径
                // 但一个通用的 Service Worker 通常假定根路径行为
                // GitHub Pages 会正确处理相对于域名的路径
                return url;
            }
            // 对于相对路径，需要转换为相对于 Service Worker 位置的路径
            return new URL(url, self.location).pathname;
        });
        return cache.addAll(urlsToCache);
      })
  );
});

// 激活 Service Worker 时，清理旧缓存
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// 拦截网络请求，优先从缓存中获取
self.addEventListener('fetch', event => {
  // 我们只处理 GET 请求
  if (event.request.method !== 'GET') {
    return;
  }

  // 对于导航请求（例如，请求 HTML 页面），使用 Network Falling Back to Cache
  // 这确保用户总能获取到最新的 HTML（如果在线），同时在离线时仍能访问
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // 对于其他资源（CSS, JS, 图片等），使用 Cache First 策略
  // 这使得应用加载非常快
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // 如果缓存中有匹配的资源，则直接返回
        if (response) {
          return response;
        }

        // 如果缓存中没有，则通过网络获取
        return fetch(event.request).then(
          networkResponse => {
            // 检查我们是否收到了一个有效的响应
            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
              return networkResponse;
            }

            // 重要：克隆响应。因为响应是一个流，只能被消费一次。
            // 我们需要一个给浏览器，一个给缓存。
            const responseToCache = networkResponse.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });

            return networkResponse;
          }
        );
      })
    );
});

// sw.js - 自我注销和清理缓存的 Service Worker

// 在 install 事件中，强制新的 worker 跳过等待，立即进入 active 状态。
// 这是确保能够尽快替换掉旧 worker 的关键步骤。
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

// 在 activate 事件中，执行所有清理工作。
// 这是新 worker 被激活后立即运行的生命周期钩子。
self.addEventListener('activate', (event) => {
  // 使用 event.waitUntil 来确保在所有清理操作完成前，浏览器不会终止这个 worker。
  event.waitUntil(
    // 1. 注销当前 Service Worker
    self.registration.unregister()
      .then(() => {
        // 2. Service Worker 注销成功后，获取所有由本站创建的缓存空间
        return caches.keys();
      })
      .then(keys => {
        // 3. 删除所有找到的缓存空间
        // Promise.all 会等待所有删除操作都完成
        return Promise.all(keys.map(key => caches.delete(key)));
      })
      .then(() => {
        // 4. (可选但推荐) 强制刷新所有当前打开的、受此 worker 控制的页面
        // 这样可以确保用户立即从旧的缓存中解放出来，加载最新的、不受 worker 控制的页面。
        return self.clients.matchAll({ type: 'window' });
      })
      .then(clients => {
        clients.forEach(client => {
          // 使用 client.navigate() 来重新加载页面
          if (client.url && 'navigate' in client) {
            client.navigate(client.url);
          }
        });
      })
      .catch(err => {
        // 如果过程中出现任何错误，在控制台打印出来，方便调试
        console.error("自杀式 Worker 清理失败:", err);
      })
  );
});

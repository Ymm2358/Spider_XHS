// 运行在页面主世界（MAIN world），只复制白名单接口的响应。
// 限流 + 去重 + 最小体积过滤，避免在消息页这类高频页面上拖慢页面。
(() => {
  // 只在小红书域名下工作。即使浏览器忽略了 manifest 的 matches，也不会碰别的网站。
  if (!/(^|\.)xiaohongshu\.com$/i.test(location.hostname)) return;

  const MAX_BYTES = 120000;
  const MIN_BYTES = 200;
  const DEDUPE_MS = 3000;
  const WINDOW_MS = 3000;
  const MAX_PER_WINDOW = 5;

  // 只收这些接口，其余一律不碰。宁可少收，也不能影响正常使用。
  const WHITELIST = [
    /^\/api\/sns\/web\/v2\/search\/notes$/,
    /^\/api\/sns\/web\/v1\/homefeed$/,
    /^\/api\/sns\/web\/v1\/feed$/,
    /^\/api\/sns\/web\/v2\/comment\/page$/,
    /^\/api\/sns\/web\/v1\/user_posted$/,
    /^\/api\/sns\/web\/v1\/you\//,
    /^\/api\/sns\/web\/v2\/user\/me$/,
    /^\/api\/sns\/web\/v1\/notification\//
  ];

  const lastSeen = new Map();
  let windowHits = [];

  const pathOf = (url) => {
    try {
      return new URL(url, location.href).pathname;
    } catch (e) {
      return "";
    }
  };

  const allowed = (url) => {
    const path = pathOf(url);
    if (!path || !WHITELIST.some((re) => re.test(path))) return false;

    const now = Date.now();
    if (now - (lastSeen.get(path) || 0) < DEDUPE_MS) return false;

    windowHits = windowHits.filter((t) => now - t < WINDOW_MS);
    if (windowHits.length >= MAX_PER_WINDOW) return false;

    lastSeen.set(path, now);
    windowHits.push(now);

    if (lastSeen.size > 200) {
      for (const [key, ts] of lastSeen) {
        if (now - ts > 60000) lastSeen.delete(key);
      }
    }
    return true;
  };

  const send = (url, text) => {
    if (!text || text.length < MIN_BYTES || text.length > MAX_BYTES) return;
    // 放到下一个任务，避免在页面关键渲染路径上做序列化。
    setTimeout(() => {
      try {
        window.postMessage({ source: "xhsops", url, body: text }, "*");
      } catch (e) {
        /* 忽略 */
      }
    }, 0);
  };

  const originalFetch = window.fetch;
  if (typeof originalFetch === "function") {
    window.fetch = function (...args) {
      const promise = originalFetch.apply(this, args);
      try {
        const input = args[0];
        const url = typeof input === "string" ? input : input && input.url ? input.url : "";
        if (url && allowed(url)) {
          promise
            .then((response) => {
              response.clone().text().then((text) => send(url, text)).catch(() => {});
            })
            .catch(() => {});
        }
      } catch (e) {
        /* 忽略 */
      }
      return promise;
    };
  }

  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__xhsops_url = url;
    return originalOpen.call(this, method, url, ...rest);
  };

  XMLHttpRequest.prototype.send = function (...args) {
    try {
      const url = this.__xhsops_url || "";
      if (url && allowed(url)) {
        this.addEventListener("load", () => {
          try {
            if (this.responseText) send(url, this.responseText);
          } catch (e) {
            /* 忽略 */
          }
        });
      }
    } catch (e) {
      /* 忽略 */
    }
    return originalSend.apply(this, args);
  };
})();

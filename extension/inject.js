// 运行在页面主世界（MAIN world），能看到页面自己的 fetch / XHR。
// 只复制响应，不改请求、不改返回值，页面行为完全不受影响。
(() => {
  const MAX_BYTES = 150000;
  const TARGETS = [/edith\.xiaohongshu\.com/, /so\.xiaohongshu\.com/];

  const shouldCapture = (url) => {
    if (!url) return false;
    return TARGETS.some((re) => re.test(url));
  };

  const send = (url, text) => {
    if (!text || text.length > MAX_BYTES) return;
    try {
      window.postMessage({ source: "xhsops", url, body: text }, "*");
    } catch (e) {
      /* 页面 CSP 或序列化失败时静默放弃，不影响页面 */
    }
  };

  const originalFetch = window.fetch;
  if (typeof originalFetch === "function") {
    window.fetch = function (...args) {
      const promise = originalFetch.apply(this, args);
      try {
        const input = args[0];
        const url = typeof input === "string" ? input : input && input.url ? input.url : "";
        if (shouldCapture(url)) {
          promise
            .then((response) => {
              response
                .clone()
                .text()
                .then((text) => send(url, text))
                .catch(() => {});
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
      this.addEventListener("load", () => {
        try {
          if (shouldCapture(this.__xhsops_url || "") && this.responseText) {
            send(this.__xhsops_url, this.responseText);
          }
        } catch (e) {
          /* 忽略 */
        }
      });
    } catch (e) {
      /* 忽略 */
    }
    return originalSend.apply(this, args);
  };
})();

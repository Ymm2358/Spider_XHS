// 运行在隔离世界，负责把主世界抓到的响应转给后台。
// 不读取页面 DOM，不做业务判断。
(() => {
  // 双保险：manifest 已经限定域名，这里再判一次，避免浏览器把脚本注入到所有页面。
  if (!/(^|\.)xiaohongshu\.com$/i.test(location.hostname)) return;

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!data || data.source !== "xhsops" || !data.body) return;
    try {
      chrome.runtime.sendMessage({
        type: "ingest",
        url: String(data.url || ""),
        body: String(data.body),
        page: location.href
      });
    } catch (e) {
      // 扩展被重载后旧的 content script 会失效，忽略即可。
    }
  });
})();

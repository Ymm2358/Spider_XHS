// 后台：把页面数据 POST 到本地服务，并记录成功/失败计数。
const DEFAULT_ENDPOINT = "http://127.0.0.1:8787";

async function config() {
  const stored = await chrome.storage.local.get(["token", "endpoint"]);
  return {
    token: stored.token || "",
    endpoint: stored.endpoint || DEFAULT_ENDPOINT
  };
}

async function bump(key) {
  const stored = await chrome.storage.local.get([key]);
  await chrome.storage.local.set({ [key]: (stored[key] || 0) + 1 });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "ingest") return;

  (async () => {
    const { token, endpoint } = await config();
    try {
      const response = await fetch(`${endpoint}/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-XHSOPS-TOKEN": token
        },
        body: JSON.stringify({
          url: message.url,
          body: message.body,
          page: message.page,
          ts: Date.now()
        })
      });
      if (response.ok) {
        await bump("okCount");
        sendResponse({ ok: true });
      } else {
        await bump("failCount");
        sendResponse({ ok: false, status: response.status });
      }
    } catch (error) {
      await bump("failCount");
      sendResponse({ ok: false, error: String(error) });
    }
  })();

  return true; // 异步响应
});

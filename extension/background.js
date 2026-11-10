// 后台：把页面数据 POST 到本地服务。
// 服务没开时先存本地队列（最多 100 条），下次成功发送后自动补发。
const DEFAULT_ENDPOINT = "http://127.0.0.1:8787";
const QUEUE_LIMIT = 100;

async function config() {
  const stored = await chrome.storage.local.get(["token", "endpoint"]);
  return {
    token: stored.token || "",
    endpoint: stored.endpoint || DEFAULT_ENDPOINT
  };
}

async function bump(key, delta = 1) {
  const stored = await chrome.storage.local.get([key]);
  await chrome.storage.local.set({ [key]: (stored[key] || 0) + delta });
}

async function post(payload) {
  const { token, endpoint } = await config();
  const response = await fetch(`${endpoint}/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-XHSOPS-TOKEN": token
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

async function enqueue(payload) {
  const { queue = [] } = await chrome.storage.local.get(["queue"]);
  queue.push(payload);
  await chrome.storage.local.set({ queue: queue.slice(-QUEUE_LIMIT) });
}

async function flushQueue() {
  const { queue = [] } = await chrome.storage.local.get(["queue"]);
  if (!queue.length) return;
  const remaining = [];
  for (const item of queue) {
    try {
      await post(item);
      await bump("okCount");
    } catch (error) {
      remaining.push(item);
    }
  }
  await chrome.storage.local.set({ queue: remaining });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "ingest") return;

  (async () => {
    const payload = {
      url: message.url,
      body: message.body,
      page: message.page,
      ts: Date.now()
    };
    try {
      await post(payload);
      await bump("okCount");
      await flushQueue();
      sendResponse({ ok: true });
    } catch (error) {
      await enqueue(payload);
      await bump("failCount");
      sendResponse({ ok: false, error: String(error) });
    }
  })();

  return true; // 异步响应
});

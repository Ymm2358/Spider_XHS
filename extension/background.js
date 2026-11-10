// 后台：批量把页面数据送到本地服务。
// 目的：减少 HTTP 次数和消息通道压力，消息页这类高频页面不卡。
const DEFAULT_ENDPOINT = "http://127.0.0.1:8787";
const QUEUE_LIMIT = 200;
const BATCH_SIZE = 10;
const FLUSH_DELAY = 1500;

let buffer = [];
let timer = null;

async function config() {
  const stored = await chrome.storage.local.get(["token", "endpoint", "paused"]);
  return {
    token: stored.token || "",
    endpoint: stored.endpoint || DEFAULT_ENDPOINT,
    paused: Boolean(stored.paused)
  };
}

async function bump(key, delta = 1) {
  const stored = await chrome.storage.local.get([key]);
  await chrome.storage.local.set({ [key]: (stored[key] || 0) + delta });
}

async function postBatch(items) {
  const { token, endpoint } = await config();
  const response = await fetch(`${endpoint}/ingest/batch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-XHSOPS-TOKEN": token
    },
    body: JSON.stringify({ items })
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
}

async function pushQueue(items) {
  const { queue = [] } = await chrome.storage.local.get(["queue"]);
  const merged = queue.concat(items);
  await chrome.storage.local.set({ queue: merged.slice(-QUEUE_LIMIT) });
}

async function flushQueue() {
  const { queue = [] } = await chrome.storage.local.get(["queue"]);
  if (!queue.length) return;
  const remaining = [];
  for (let i = 0; i < queue.length; i += BATCH_SIZE) {
    const chunk = queue.slice(i, i + BATCH_SIZE);
    try {
      await postBatch(chunk);
      await bump("okCount", chunk.length);
    } catch (error) {
      remaining.push(...chunk);
    }
  }
  await chrome.storage.local.set({ queue: remaining });
}

function schedule() {
  if (timer) return;
  timer = setTimeout(() => {
    timer = null;
    flush();
  }, FLUSH_DELAY);
}

async function flush() {
  if (!buffer.length) return;
  const items = buffer.splice(0, BATCH_SIZE);
  try {
    await postBatch(items);
    await bump("okCount", items.length);
    await flushQueue();
  } catch (error) {
    await pushQueue(items);
    await bump("failCount", items.length);
  }
  if (buffer.length) schedule();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "ingest") return;

  (async () => {
    const page = String(message.page || (sender.tab && sender.tab.url) || "");
    if (!/^https:\/\/([a-z0-9-]+\.)*xiaohongshu\.com\//i.test(page)) {
      sendResponse({ ok: true, skipped: "not xiaohongshu" });
      return;
    }
    const { paused } = await config();
    if (paused) {
      sendResponse({ ok: true, paused: true });
      return;
    }
    buffer.push({
      url: message.url,
      body: message.body,
      page: message.page,
      ts: Date.now()
    });
    if (buffer.length >= BATCH_SIZE) {
      await flush();
    } else {
      schedule();
    }
    sendResponse({ ok: true });
  })();

  return true;
});

chrome.runtime.onStartup.addListener(flushQueue);
chrome.runtime.onInstalled.addListener(flushQueue);

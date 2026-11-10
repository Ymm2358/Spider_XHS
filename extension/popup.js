const DEFAULT_ENDPOINT = "http://127.0.0.1:8787";

const $ = (id) => document.getElementById(id);

async function load() {
  const stored = await chrome.storage.local.get(["token", "endpoint", "okCount", "failCount"]);
  $("endpoint").value = stored.endpoint || DEFAULT_ENDPOINT;
  $("token").value = stored.token || "";
  $("counts").textContent = `已发送 ${stored.okCount || 0} 条，失败 ${stored.failCount || 0} 条`;
  checkHealth();
}

async function checkHealth() {
  const endpoint = $("endpoint").value.trim() || DEFAULT_ENDPOINT;
  try {
    const response = await fetch(`${endpoint}/health`, { cache: "no-store" });
    const data = await response.json();
    $("status").textContent = data.ok ? "服务在线" : "服务异常";
    $("status").className = data.ok ? "ok" : "bad";
  } catch (error) {
    $("status").textContent = "服务未启动：先在项目目录跑 python -m xhsops serve";
    $("status").className = "bad";
  }
}

async function save() {
  await chrome.storage.local.set({
    endpoint: $("endpoint").value.trim() || DEFAULT_ENDPOINT,
    token: $("token").value.trim()
  });
  checkHealth();
}

async function test() {
  await save();
  const endpoint = $("endpoint").value.trim() || DEFAULT_ENDPOINT;
  const token = $("token").value.trim();
  try {
    const response = await fetch(`${endpoint}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-XHSOPS-TOKEN": token },
      body: JSON.stringify({
        url: "https://edith.xiaohongshu.com/api/test",
        body: JSON.stringify({ test: true, from: "popup" }),
        page: "popup",
        ts: Date.now()
      })
    });
    $("status").textContent = response.ok ? "测试成功，服务端已收到" : `测试失败：HTTP ${response.status}`;
    $("status").className = response.ok ? "ok" : "bad";
  } catch (error) {
    $("status").textContent = `测试失败：${error}`;
    $("status").className = "bad";
  }
}

$("save").addEventListener("click", save);
$("test").addEventListener("click", test);
$("open").addEventListener("click", () => {
  const endpoint = $("endpoint").value.trim() || DEFAULT_ENDPOINT;
  chrome.tabs.create({ url: endpoint });
});

load();

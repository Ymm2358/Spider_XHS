# xhs-ops bridge 插件

把小红书页面已经加载的接口响应复制一份，送到本机的 `xhs-ops` 服务。
不额外发请求，不修改页面行为，不读取 DOM。

## 安装（夸克 / Chrome / Edge 通用）

1. 启动本地服务：

   ```
   cd E:\xhs-ops
   .\.venv\Scripts\python.exe -m xhsops serve
   ```

   终端会打印 token，例如 `插件 token：xxxxx`。也可以直接看 `data\token.txt`。

2. 打开扩展管理页：

   - 夸克：地址栏输入 `quark://extensions`
   - Chrome / Edge：`chrome://extensions`

3. 打开右上角「开发者模式」，点「加载已解压的扩展程序」，选择本目录 `E:\xhs-ops\extension`。

4. 点插件图标，把 token 填进去，点「保存」，再点「测试发送」。
   看到「测试成功」说明链路通了。

5. 打开 `xiaohongshu.com`，搜索任意关键词，正常往下刷。
   再点插件图标，应该能看到「已发送 N 条」。

## 验证

- 本地页面：<http://127.0.0.1:8787>
- 原始数据：`data\raw\extension\日期\`
- 服务端日志：启动服务的那个终端窗口

## 常见问题

**加载时报 manifest 错误**
夸克对 `world: "MAIN"` 的支持可能不完整。把 `manifest.json` 里第一段 content_scripts 的 `"world": "MAIN"` 删掉再试；如果还不行，换 Chrome/Edge 加载。

**弹窗显示服务未启动**
本地服务没跑，或者端口被占用。确认 `python -m xhsops serve` 在运行。

**测试成功但刷页面没有新数据**
说明页面没走 `fetch`/`XHR`（可能用了别的传输方式）。把浏览器控制台里 Network 面板的请求类型发出来，再调整注入方式。

**数据太多**
`inject.js` 里 `MAX_BYTES = 150000`，超过就丢弃，避免把大响应塞进消息通道。

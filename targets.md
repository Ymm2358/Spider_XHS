# 项目目标

把小红书的数据、写稿、发布整合成一个本地工具，一个人用。

不是平台，不做多用户，不做注册登录。最终形态是一个双击就能开的窗口：账号、采集、内容库、写稿、发布、数据，全在一个界面里。

完整技术决策见 `ARCHITECTURE.md`。

# 路线

复用 `XHS_ALL_IN_ONE` 的后端，自建前端，签名层用本项目的 `vendor/spider_xhs`。

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 搬后端：`backend/app` → `server/engine`，替换签名层 | 完成 |
| P1 | 去认证：本地固定用户，删掉登录页 | 完成 |
| P2 | 单库：合并 notes 表，从 raw 重放历史数据 | 未开始 |
| P3 | 前端外壳：React + Vite + Tailwind，路由和布局 | 完成 |
| P4 | 页面：账号（完成）、采集、内容库、写稿、概览 | 进行中 |
| P5 | 打包：单进程托管前端 + `start.bat` | 未开始 |

已完成的基础（在 P0 之前就已经能跑）：

- 采集与指标：`xhsops/`，SQLite、快照、蓝海指数、日报
- 报告导出：PDF + 分享图，本机浏览器无头渲染
- 浏览器插件：被动采集、限流、白名单、断线队列
- 签名层：`vendor/spider_xhs`，2026-10-22 版
- 扫码登录：`xhsops login`

# 当前进度

- 后端已接入，去掉了认证，`/api/health` 和 `/api/accounts` 可用
- 前端外壳完成，账号页已接真实接口
- 采集号「不吃月饼饼」（id=1）已绑定，状态 active
- 发布账号暂停：创作者二维码授权到千帆，Cookie 导入缺 CAS/DS，先手工发布

# 当前目标

用账号 1 跑一次真实采集（`POST /api/xhs/crawl/search-notes`），确认入库，然后做内容库页。

# 已知取舍

- 上游文件一律放 `vendor/spider_xhs/`，不手改，用 `scripts/sync_upstream.ps1` 整层替换，补丁放 `patches/`
- 主号不参与工具内采集，避免风控；发布手工
- 小红书不挂代理；GitHub 需要代理，两者分开
- 自己的代码在 `xhsops/`、`server/`、`web/`、`extension/`，永远不碰 vendor

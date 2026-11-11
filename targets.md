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
| P4 | 六个页面：账号、采集、内容库、写稿、发布、概览 | 未开始 |
| P5 | 打包：单进程托管前端 + `start.bat` | 未开始 |

已完成的基础（在 P0 之前就已经能跑）：

- 采集与指标：`xhsops/`，SQLite、快照、蓝海指数、日报
- 报告导出：PDF + 分享图，本机浏览器无头渲染
- 浏览器插件：被动采集、限流、白名单、断线队列
- 签名层：`vendor/spider_xhs`，2026-10-22 版
- 扫码登录：`xhsops login`

# 当前进度

- 验证过 `XHS_ALL_IN_ONE` 后端能用我们的签名层启动，111 个接口，JWT 注册登录可用
- 前端技术栈已定：React 19 + Vite + Tailwind，不用 Ant Design
- 当前阻塞：`.env` 里的 Cookie 已过期，脚本采集不可用；插件采集不受影响

# 当前目标

从 P0 开始：把后端搬进 `server/engine`，改导入前缀，替换签名层，确认 `/api/health` 能起。

# 已知取舍

- 上游文件一律放 `vendor/spider_xhs/`，不手改，用 `scripts/sync_upstream.ps1` 整层替换
- 主号只做被动采集，主动采集留给小号
- 小红书不挂代理；GitHub 需要代理，两者分开
- 自己的代码在 `xhsops/`、`server/`、`web/`、`extension/`，永远不碰 vendor

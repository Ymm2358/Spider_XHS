# 架构决策

> 最后更新：2026-11-11
> 这份文档是给下一个 session 的交接说明。开工前先读完，再动代码。

## 一句话

把小红书数据、写稿、发布整合成一个本地工具：单进程后端 + 自建前端，一个人用，不要登录。

## 已定的决策

| 项 | 决定 | 理由 |
|---|---|---|
| 整体形态 | 一个本地工具，不是平台 | 自己用，不需要多用户 |
| 后端 | 复用 `XHS_ALL_IN_ONE` 的 `backend/app` | 111 个接口已写完，采集/发布/调度都现成 |
| 签名层 | 用本项目的 `vendor/spider_xhs` | 上游 2026-10-22 版，能过当前风控；它自带的 8 月版会 461/406 |
| 前端 | **React 19 + Vite + Tailwind**，自建组件 | 完全控制视觉，不用 Ant Design |
| 认证 | **去掉**，本地固定单用户 | 它的 OAuth2 声明和 JSON 接口不匹配，登录窗本来就进不去 |
| 进程 | 单进程、单端口、单 SQLite | 不要 8000 + 8787 两个服务 |
| 图表 | Recharts 或 ECharts | 都行，跟着 React 走 |
| 打包 | FastAPI 托管前端构建产物 + `start.bat` | 双击启动，不装服务 |

前端技术栈是用户明确选的：**React + Vite + Tailwind，不用 Ant Design**。不要再提议 AntD、Element、MUI。

## 目标结构

```
xhs-ops/
├── server/
│   ├── main.py              单进程入口：挂 engine + local 路由，托管前端
│   ├── engine/              从 XHS_ALL_IN_ONE 的 backend/app 迁入
│   │   ├── api/             账号、采集、内容库、草稿、发布、任务、分析
│   │   ├── models/          SQLAlchemy 模型
│   │   ├── services/        业务逻辑与调度
│   │   ├── adapters/xhs/    调用 apis / xhs_utils 的适配层
│   │   └── core/            配置、数据库、依赖
│   ├── local/               本项目自己的接口
│   │   ├── ingest.py        浏览器插件数据入口
│   │   ├── advice.py        指标 + persona 建议
│   │   └── export.py        PDF / 分享图
│   └── auth.py              本地固定用户，替代 JWT
├── web/                     自建前端（React + Vite + Tailwind）
│   ├── src/
│   │   ├── pages/           概览、账号、采集、内容库、写稿、发布、设置
│   │   ├── components/      自建组件，不引第三方 UI 库
│   │   └── lib/api.ts       统一请求封装
│   └── package.json
├── vendor/spider_xhs/       签名层（不手改）
├── extension/               浏览器插件（被动采集）
├── xhsops/                  现有数据层，保留
├── data/                    一个 SQLite + 原始归档
└── start.bat                启动
```

## 迁移步骤

### P0 搬后端

- 把 `XHS_ALL_IN_ONE` 的 `backend/app` 复制成 `server/engine`
- 全局替换导入前缀：`backend.app.` → `server.engine.`
- 删掉它自带的 `apis/`、`xhs_utils/`、`static/`，改用 `vendor/spider_xhs`
- 验收：`python -m server.main` 能起，`/api/health` 返回 ok

### P1 去认证

- `server/engine/core/deps.py` 里的 `get_current_user` 改成返回本地固定用户
- 启动时自动建一个 `local` 用户（id=1），不暴露注册/登录接口
- 前端没有登录页
- 验收：不带 token 直接调 `/api/accounts` 返回 200

### P2 单库（已定：合并成一套）

**决定：以 engine 的 `notes` 表为准，扩展字段，历史数据从 `data/raw` 重放，不做 SQL 对拷。**

原因：两边都有 `notes` 表但字段完全不同，SQLite 里同名表不能共存；而我们的原始响应都归档在 `data/raw/`，重放比写迁移脚本更可靠。

字段映射（engine 现有 → 需要补的）：

| 我们的字段 | engine 现状 | 处理 |
|---|---|---|
| `note_id` | 有 | 加唯一索引 `(platform, note_id)` |
| `title` | 有 | 直接用 |
| `desc` | `content` | 直接用 |
| `author_id` | 无 | 新增 `author_id` |
| `author_nick` | `author_name` | 直接用 |
| `author_fans` | 无 | 新增 `author_fans` |
| `liked/collected/comment/share` | 无 | 新增四个整数字段 |
| `publish_ts` | 无 | 新增 `publish_ts`（epoch 秒） |
| `publish_text` | 无 | 新增 `publish_text` |
| `note_type` | 无 | 新增 |
| `image_count` | 无 | 新增 |
| `url` | 无 | 新增 |
| `keyword` | 无 | 新增 |
| `cover_url` | `note_assets` | 保留 assets，同时冗余一列方便列表页 |
| `tags` | `note_tags` 关联 | 用关联表，不存 JSON |
| `first_seen/last_seen` | `created_at` | 新增 `last_seen`，`first_seen` 用 `created_at` |
| 快照 | 无 | 新增 `note_snapshots` 表（note_id, ts, liked, collected, comment, share） |

执行顺序：

1. 在 `server/engine/models/note.py` 加字段和 `NoteSnapshot` 模型
2. 生成一个 alembic 迁移（新增列 + 唯一索引 + 新表）
3. 写 `server/local/replay.py`：读 `data/raw/`，走 engine 的入库 service，不直接写 SQL
4. 校验：重放后 `notes` 行数 ≥ 1675，随机抽 20 条对比 `liked/collected/comment` 与旧库一致
5. 旧库 `data/xhs.db` 改名归档，不再写入

注意：`xhsops/store.py` 目前是裸 sqlite3，P2 之后要么改成 SQLAlchemy 读 engine 的库，要么只保留只读查询。不要在同一个库里维护两套 notes。

### P3 前端外壳

- Vite + React + Tailwind，路由：`/`、`/accounts`、`/collect`、`/library`、`/drafts`、`/publish`、`/settings`
- 先只做布局和导航，每页放占位
- `lib/api.ts` 封装 fetch，错误统一提示
- 验收：`npm run dev` 能打开，切换路由不报错

### P4 接页面

按这个顺序，每页做完能独立验收：

1. 账号：列表、扫码/ Cookie 导入、健康状态
2. 采集：关键词搜索、结果入库、插件数据列表
3. 内容库：卡片/列表、筛选、标签
4. 写稿：选素材 → agent 生成 → 编辑 → 存草稿
5. 发布：选草稿 → 预览 → 发布/定时
6. 概览：关键数字和趋势

### P5 打包

- `web` 构建产物由 FastAPI 托管
- `start.bat` 一键启动并打开浏览器
- 可选 pywebview 套桌面窗口

## 接口约定

engine 的接口保持原样，路径不变（`/api/accounts`、`/api/xhs/...`）。
本项目新增的接口统一放在 `/api/local/`：

| 接口 | 用途 |
|---|---|
| `POST /api/local/ingest` | 插件数据入库 |
| `GET /api/local/stats` | 插件数据量、最近采集 |
| `GET /api/local/advice` | 基于指标和 persona 的选题建议 |
| `POST /api/local/export` | 生成 PDF / 分享图 |

## 已知风险

- **它的签名层已过期**：必须用 `vendor/spider_xhs`，不要用仓库自带的 `apis/`。
- **它没有 LICENSE 文件**，README 写 MIT 但仓库里没有。自己用没问题，不要分发。
- **它的迁移脚本和模型耦合**：搬过来时先跑一次空库迁移，确认 alembic 链完整。
- **`XHS_ALL_IN_ONE` 最后提交是 2026-08**：上游 SDK 更新后，它的适配层可能需要跟着改，改动集中在 `server/engine/adapters/xhs/`。
- **Cookie 会过期**：`xhsops login` 扫码续期，engine 的账号健康检查也要能提示。

## 当前进度（2026-11-11）

已完成：

- `xhsops` 数据层：采集、指标、日报、PDF/PNG、扫码登录、插件接收服务
- `vendor/spider_xhs`：上游 2026-10-22 版，doctor 可用（Cookie 过期时停在登录态）
- 浏览器插件：被动采集、限流、白名单、断线队列
- 验证过 `XHS_ALL_IN_ONE` 后端可以用我们的签名层启动，111 个接口，JWT 注册登录可用

未开始：

- P0 搬后端
- P1 去认证
- P3 前端外壳

## 临时文件

- `data/tmp/xhs-all-in-one/`：验证用的克隆，可随时删除
- `data/tmp/` 下的测试账号和库：一次性，不提交

## 关键命令

```
.venv\Scripts\python -m xhsops doctor          # 检查 Cookie 和签名
.venv\Scripts\python -m xhsops serve           # 插件接收服务
.venv\Scripts\python -m xhsops export          # 出 PDF / 分享图
```

新 session 接手时，先读 `issue.md` 和 `targets.md`，再从 P0 开始。

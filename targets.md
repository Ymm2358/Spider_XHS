# 项目目标

把小红书的数据接进本地 agent，让它每天给出「今天做什么内容」的可执行建议，而不是只给一堆热榜。

不是复刻 Spider_XHS 的全部接口。直播、私信、蒲公英、千帆都不做，只保留 PC 端采集和创作者平台发布。

# 分阶段计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 打通运行时：Cookie 登录态、签名、搜索接口、doctor 自检 | 完成 |
| P1 | 采集与入库：搜索三档、SQLite、快照、原始 JSON 归档、批处理超时隔离 | 完成 |
| P2 | 指标与日报：加权互动、log 空间稳健 z、蓝海指数、方向对比、brief.json | 完成初版 |
| P3 | Agent 接入：xhs-ops skill、xhs-analyst agent、`/daily` 出 advice.md | 完成 |
| P4 | 自动化：run_daily.ps1、sync_upstream.ps1、Windows 计划任务、上游同步 PR | 脚本已写，计划任务未配 |
| P5 | 成稿闭环：选候选 → dsh 写标题正文 → 人工发布 | 未开始 |
| P6 | 静态看板：`xhsops report --html`，单文件可离线看 | 未开始 |
| P7 | 自动发布（可选，默认关闭） | 未开始 |

# 当前进度

- 已采集 1270 条笔记，覆盖 5 个方向、17 个关键词，原始响应归档在 `data/raw/`。
- `doctor` 四步全通过：`.env`、Cookie 完整性、`user/me`、搜索接口。
- `brief.json` 已能输出方向对比、关键词蓝海榜、起量笔记。
- `xhs-analyst` 已跑通一次完整产出：3 条重点 + 7 条备选，写入 `reports/2026-11-10/advice.md`，19 条证据的 note_id 和 url 全部回验存在。
- 当前结论：城市漫步、数码体验蓝海指数最高；摄影、游戏供给最密，泛教程没有位置。
- PR 已开：https://github.com/Ymm2358/Spider_XHS/pull/1（`feat/p0-runtime` → `master`）。

# 当前目标

1. 解决作者粉丝数拿不到的问题。现在 `get_user_info` 会触发 40001 安全验证，`novice_viral_rate` 全是 null，素人爆款这条判断线等于没有。
2. 把 `run_daily.ps1` 挂进 Windows 计划任务，先跑通无人值守 3 天。
3. 把分支推上 GitHub，走一次 `feat/p0-runtime` → `main` 的 PR，确认流程可用。

# 已知取舍

- 上游 `apis/`、`xhs_utils/` 保持原样，业务代码只在 `xhsops/`。同步上游用 `git merge upstream/master`，不改上游文件，避免冲突。
- 采集用小号 Cookie，发布才用主号。主号登录态不参与采集。
- 小红书不挂代理。GitHub 需要代理，两者分开。

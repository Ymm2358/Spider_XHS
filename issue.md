# 当前问题

## 阻塞

### 1. 作者粉丝数受风控影响，只能低频补

`get_user_info` 走的是 `user/otherinfo`，比其他接口敏感。连续调用会返回 461/471，上游 `risk_qr_verify` 会打印二维码并轮询 180 秒等扫码。这不是登录态问题——Cookie 有效，`user/me` 和搜索都正常；461/471 是请求级的风控校验，和 Cookie 是两套东西。

之前 80 个作者全部失败，有两个叠加原因：
1. 上游 `xhs_utils/xhs_core/ssk.py` 依赖 `cryptography`，而 `requirements.txt` 没列，`risk_qr_verify` 一 import 就崩；
2. 紧接着密集请求触发了 40001「为了您的账号安全」，二维码 init 被防重放拒绝。

现状：补上依赖、把间隔放到 1.5–3 秒后，20/20 成功，52 秒跑完。说明不是硬封，是频率问题。

已做：`enrich` 默认不弹二维码（`disable_risk_verify`），触发风控时直接失败，避免卡 180 秒；需要扫码时加 `--verify`。

待观察：连续多天低频补（每天 50–100 个）能否把 `fans_known` 攒起来。

### 2. GitHub 推送的网络问题（已解决）

之前 `git push` 走 `127.0.0.1:7892`，代理关闭时无法连接。实测直连 `github.com:443` 可用，已清掉仓库里的 `http.proxy` 配置，现在推送不需要代理。

注意：`gh` 会把仓库识别成上游 `cv-cat/Spider_XHS`（因为有 `upstream` remote），建 PR 时必须显式带 `--repo Ymm2358/Spider_XHS`。

## 待解决

- **计划任务尚未注册**。`schtasks /Create` 在当前会话返回「拒绝访问」，需要管理员权限。用 `scripts/install_task.ps1` 在提权 PowerShell 里跑一次即可。
- **低互动关键词的 z 值仍偏大**。已给 log 空间 scale 加 0.35 下限并截断到 ±20，但 `日常记录`、`周末日常` 这类中位互动接近 0 的关键词，z 值仍不可与其他方向横向比较。考虑改成同方向内比较，或直接改用绝对互动分位。
- **城市漫步样本不足**。3 个关键词里 `城市探索` 返回 0 条，`城市漫步` 21 条，方向指标主要靠 `citywalk` 撑着。需要换词或扩大 limit。
- **`get_homefeed_recommend` 返回空 data**。接口通但无内容，怀疑参数需要先用 `get_homefeed_all_channel` 拿种子。不影响当前流程，暂不处理。
- **`get_note_info` 的返回结构**比搜索多出 `desc`、`time`、`tag_list`，可以用它补全发布时间的缺失（当前 5% 笔记 `publish_ts` 为空），但会多一次请求，暂缓。

## 已解决

- `cryptography` 缺失导致所有走风控校验的接口在 import 阶段崩：已加入 `requirements-xhsops.txt` 并安装。
- `batch` 超时杀不干净：venv 的 `python.exe` 会再起一个真实 python，只杀父进程时管道不关，`communicate` 一直等。改成 `taskkill /F /T /PID` 杀进程树。
- 上游 loguru 每个失败都打完整 traceback，批量跑时刷屏：CLI 里 `logger.remove()`。
- `--json` 只能放在子命令前：现在前后都能用。
- 首次 z 值算出 1186：改成 log1p 空间 + scale 下限 + 截断。
- 被强杀的 run 一直挂 `running`：`start_run` 时把超过 6 小时的 running 标记为 aborted。

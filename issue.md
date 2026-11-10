# 当前问题

## 阻塞

### 1. 作者粉丝数拿不到，素人爆款率恒为 null

`get_user_info` 在连续调用后会返回 `40001 为了您的账号安全，请退出应用重新操作`，上游 `risk_qr_verify` 会弹出二维码并要求扫码，最长等 180 秒。批量补 80 个作者时，前 2 个成功后全部失败。

影响：`brief.json` 里 `fans_known = 0`，`novice_viral_rate` 全为 null，agent 无法判断「爆款是不是素人做出来的」。

已做：`enrich` 连续 3 次 40001 自动停，避免空跑；日报里保留 `—`，agent 约定禁止据此排序。

待定方案：
- 降频到每天 5-10 个作者，长期积累；
- 或换不需要该接口的替代信号（例如作者在样本里的历史表现）；
- 或接受缺失，把素人判断降级为「作者是否只出现过一次」。

### 2. GitHub 推送需要代理

`git push` 走 `127.0.0.1:7892`，代理关闭时无法连接。本地提交不受影响。

处理：推送前把代理打开，或改 `git config http.proxy` 指向新端口。

## 待解决

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

---
name: xhs-ops
description: 需要采集小红书关键词笔记、补作者粉丝数或生成选题日报时使用。
---

# xhs-ops

## 什么时候用
- 要判断一个选题方向近期有没有起量笔记。
- 要给主号找可复用的角度，需要真实笔记做证据。
- 要更新本地笔记库、粉丝数或日报。
- 不负责登录、发布、账号管理。

## 命令
只使用下面这些参数，不要自行扩展。

```bash
python -m xhsops doctor [--keyword 摄影] [--limit 20] [--dump]
python -m xhsops collect --keyword 关键词 [--sorts 0,2,1] [--limit 40] [--json]
python -m xhsops batch --direction 方向名|all [--timeout 180] [--json]
python -m xhsops enrich --limit 60
python -m xhsops brief [--days 7] [--json]
python -m xhsops status [--json]
```

所有命令都支持顶层 `--json`。采集类命令先看 `ok`、`errors`、计数；`brief --json` 直接输出分析对象。不要从自然语言输出里猜结果。

## 典型顺序
1. `doctor`：确认 Cookie、签名、搜索接口都能用。失败就停。
2. `batch --direction ...`：按方向批量采集；也可以 `collect --keyword ...` 单跑一个词。
3. `enrich`：补作者粉丝数。没有这一步，`novice_viral_rate` 会是 null。
4. `brief --days 7`：生成日报和 `brief.json`。
5. `status`：看库存、最近任务和失败原因。

采集量不够时先看 `status` 的 `recent_runs`，不要直接重跑全部关键词。

## 数据位置
- `xhsops/`：业务代码，改逻辑只改这里。
- `apis/`、`xhs_utils/`：上游 Spider_XHS，保持原样。
- `data/xhs.db`：SQLite。`notes` 笔记，`note_snapshots` 互动快照，`authors` 作者，`runs` 任务记录。
- `reports/日期/brief.md`：给人看的日报。
- `reports/日期/brief.json`：稳定契约，agent 只读这个。
- `config/keywords.yml`：方向、关键词、focus、采集档位。
- `config/weights.yml`：互动权重、爆款阈值、素人阈值、蓝海参数。
- `config/competitors.yml`：对标账号和主号。
- `.env`：`XHS_PC_COOKIE` 等本地凭据。

## 失败判断
| 现象 | 判断 | 处理 |
|---|---|---|
| 461 / 471 | 风控拦截，常见于签名或设备指纹过期 | 停采，不要连续重试；检查上游 `apis/`、`xhs_utils/` 是否最新 |
| -100 / 401 | 登录态失效，Cookie 过期 | 重新登录，更新 `.env` 的 `XHS_PC_COOKIE` |
| `doctor` 返回 1 | Cookie 缺失或不完整 | 补 `a1=`、`web_session=` |
| `doctor` 返回 2 | `user/me` 不通 | 按报错区分风控或 Cookie |
| `doctor` 返回 3 | 搜索接口失败 | 先处理风控，再确认关键词和限额 |

返回 0 但结果为 0 条，不等于成功采集。看 `status` 和 `runs.message`。

# 当前问题

## 阻塞

- **`.venv` 缺少 `cryptography`**
  `get_user_info` 等接口会走 `risk_qr_verify` → `apis/xhs_pc_login_apis.py` → `xhs_utils/xhs_core/ssk.py`，在 import 阶段直接抛 `ModuleNotFoundError: No module named 'cryptography'`。
  影响：凡触发风控校验的接口全部失败，返回 `(False, "No module named 'cryptography'", None)`。
  处理：`pip install cryptography`，或确认 `requirements-xhsops.txt` 是否漏列该依赖。

- **`get_homefeed_recommend` 返回空 data**
  调用后得到 `{"code": 0, "success": true, "data": {}, "msg": ""}`，接口通但无内容。
  待查：是参数组合（`category` / `cursor_score` / `refresh_type` / `note_index`）不对，还是需要先调 `get_homefeed_all_channel` 拿 `cursor_score` 种子。

## 待确认

- `search_note` 首次调用曾返回空 `data`，重试后正常返回 52KB 结果。怀疑 `search_id` 生成或首次握手时机不稳定，需要复现确认。

## 已解决

- 外部导入 cookie 调用接口：`XHSPcAuth.from_cookie(cookie_str)` + `XHS_Apis(auth).bootstrap()` 实测可用。
  - `get_user_me` 返回真实账号（`red_id=18989042813`，昵称 `zzz`，`user_id=68b6873300000000190136bb`）
  - `search_note("咖啡")` 正常返回笔记列表
  - `get_homefeed_all_channel` 正常返回频道列表

# 项目目标

`E:\xhs-ops` 基于 Spider_XHS，目标是把小红书 PC 端、创作者平台、蒲公英、千帆的接口全部封装成可直接调用的 Python API，签名参数（a1 / web_id / b1 / websectiga / sec_poison_id / gid / x-s / x-t / x-s-common / x-b3-traceid / x-xray-traceid / x-rap-param / search_id / request_id / sign / q-signature）全部透明处理，上层只关心业务数据。

# 计划

1. 登录态接入：扫码登录、手机验证码登录、**外部 cookie 导入**三种方式对齐同一套 auth 对象。
2. 签名栈自洽：Python 只做参数编排，所有加密/签名逻辑集中在 `xhs_utils/*/js/`，通过 Node 运行时执行，不在 Python 里重复实现。
3. 接口覆盖：PC 端采集（首页、用户、笔记、搜索、评论、消息）+ 创作者平台（发布、作品管理）+ 蒲公英 + 千帆。
4. 业务层：`xhsops/` 提供采集、归一化、指标、报表、CLI。

# 当前进度

- 签名栈完整可用，PC 端与创作者平台各有独立实现（`xhs_utils/xhs_pc`、`xhs_utils/xhs_creator`）。
- cookie 导入路径已验证：`XHSPcAuth.from_cookie()` 能解析 cookie、拉起 Node 运行时、`bootstrap()` 自动拿到 `user_id`。
- 已实测通过：`get_user_me`、`search_note`、`get_homefeed_all_channel`。
- 已知缺陷见 `issue.md`。

# 当前目标

修掉 `cryptography` 缺失导致的接口中断，让 `get_user_info` 一类走风控校验的接口恢复；同时确认 `get_homefeed_recommend` 的空返回是参数问题还是接口变更。

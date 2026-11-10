"""上游 Spider_XHS 的唯一耦合点。

规则：
- 只有这个文件 import apis/ 和 xhs_utils/。
- 上游方法签名变化时，只改这里，业务层不受影响。
- 这里不做任何重试或降级，失败原样抛出，交给调用方决定。
"""

from __future__ import annotations

from typing import Any, Optional

from ..config import pc_cookie, proxies


class UpstreamError(RuntimeError):
    """上游返回 success=False。保留原始 message，便于区分 cookie 失效与签名失效。"""


def build_pc_auth(cookie: Optional[str] = None, proxy: Optional[dict] = None):
    """构造 PC 端登录态。from_cookie 内部会调用 user/me 完成 bootstrap。"""
    from xhs_utils.xhs_pc import XHSPcAuth

    return XHSPcAuth.from_cookie(
        cookie or pc_cookie(),
        proxies=proxy if proxy is not None else proxies(),
    )


def build_pc_api(cookie: Optional[str] = None, proxy: Optional[dict] = None):
    """构造 PC 端 API 客户端，鉴权材料已就绪。"""
    from apis.xhs_pc_apis import XHS_Apis

    return XHS_Apis(build_pc_auth(cookie, proxy))


def build_creator_api(cookie: Optional[str] = None, proxy: Optional[dict] = None):
    """构造创作者平台 API 客户端，发布与已发布列表用。"""
    from apis.xhs_creator_apis import XHS_Creator_Apis
    from xhs_utils.xhs_creator import XHSCreatorAuth
    from ..config import creator_cookie

    auth = XHSCreatorAuth.from_cookie(
        cookie or creator_cookie(),
        proxies=proxy if proxy is not None else proxies(),
    )
    return XHS_Creator_Apis(auth).bootstrap()


def unwrap(result: Any) -> Any:
    """把上游的 (success, message, data) 三元组拆成 data，失败则抛 UpstreamError。"""
    if not isinstance(result, tuple) or len(result) != 3:
        return result
    success, message, data = result
    if not success:
        raise UpstreamError(str(message or "上游返回 success=False"))
    return data


def disable_risk_verify(api) -> None:
    """批量任务里不弹二维码。

    上游遇到 461/471 会调 risk_qr_verify，默认行为是打印二维码并轮询 180 秒。
    批量补作者时这会让整轮卡死，而且验证通过的收益很低，所以默认直接返回 False，
    让调用方立刻拿到失败结果。需要扫码时用 enrich --verify。
    """
    api.risk_qr_verify = lambda *args, **kwargs: False

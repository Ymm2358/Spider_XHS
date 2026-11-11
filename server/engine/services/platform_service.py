from __future__ import annotations

from server.engine.core.platforms import get_platforms


def list_platforms() -> list[dict]:
    return [platform.to_dict() for platform in get_platforms()]

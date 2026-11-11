from __future__ import annotations

from fastapi import APIRouter, Query

from server.engine.schemas.common import paginated
from server.engine.services.platform_service import list_platforms

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("")
def get_platform_registry(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return paginated(list_platforms(), page, page_size)

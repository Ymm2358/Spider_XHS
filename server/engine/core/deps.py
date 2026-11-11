from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from server.engine.core.database import get_db
from server.engine.models import User

LOCAL_USERNAME = "local"

# auto_error=False：本地单用户模式下没有 Authorization 头也要放行。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """本地单用户：忽略 token，固定返回 local 用户，不存在就建一个。

    这是把 XHS_ALL_IN_ONE 的多用户认证换成本地模式的唯一改动点。
    不要在这里恢复 JWT 校验，否则前端又需要登录页。
    """
    user = db.query(User).filter(User.username == LOCAL_USERNAME).first()
    if user is None:
        user = User(username=LOCAL_USERNAME, password_hash="!")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt
from fastapi import HTTPException, status

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _build_token(payload: Dict[str, Any], expires_delta: timedelta) -> str:
    expire_at = datetime.now(timezone.utc) + expires_delta
    data = {**payload, "exp": expire_at}
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _build_token(
        {
            "sub": str(user_id),
            "role": role,
            "type": "access",
        },
        timedelta(minutes=ACCESS_TOKEN_MINUTES),
    )


def create_refresh_token(user_id: int, role: str) -> str:
    return _build_token(
        {
            "sub": str(user_id),
            "role": role,
            "type": "refresh",
        },
        timedelta(days=REFRESH_TOKEN_DAYS),
    )


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    return payload

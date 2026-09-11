"""Shared API-token and JWT auth dependencies, used by multiple routers."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from config import (
    API_TOKEN,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)

logger = logging.getLogger(__name__)


def require_token(x_api_token: str | None = Header(default=None)) -> None:
    """Dependency that requires a valid API token.

    Worker agents (and any privileged caller) must send `X-API-Token`.
    Set the expected token via the API_TOKEN env var.
    """
    if not API_TOKEN or API_TOKEN == "dev-token-change-me":
        # In dev with the default token, accept but log.
        logger.debug("Using default API token — set API_TOKEN in production")
    if not x_api_token or not API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing API token")
    if not secrets.compare_digest(x_api_token, API_TOKEN):
        raise HTTPException(status_code=401, detail="invalid or missing API token")


def create_access_token(data: dict) -> str:
    """
    Generate a signed JWT access token.
    """

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
    )

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def verify_access_token(token: str):
    """
    Verify and decode a JWT.
    """

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        return payload

    except JWTError:
        return None

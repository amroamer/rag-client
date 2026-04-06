import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("FASTAPI_API_KEY", "")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the X-API-Key header.

    If FASTAPI_API_KEY env var is empty, auth is DISABLED (useful for local dev).
    In production, always set FASTAPI_API_KEY.
    """
    if not API_KEY:
        # Auth disabled — allow all requests
        return "no-auth"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key

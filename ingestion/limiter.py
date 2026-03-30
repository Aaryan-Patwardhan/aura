from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import Request

def api_key_func(request: Request):
    return request.headers.get("X-API-Key", get_remote_address(request))

limiter = Limiter(key_func=api_key_func, default_limits=["100/minute"])

from slowapi import Limiter
from slowapi.util import get_remote_address

def api_key_func(req):
    return req.headers.get("X-API-Key", get_remote_address(req))

limiter = Limiter(key_func=api_key_func, default_limits=["100/minute"])

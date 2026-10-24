"""
HTTP Test Client executing actual ASGI requests against FastAPI app.
Provides requests-like API: get, post, put, delete with real HTTP header, JWT and middleware parsing.
"""
import asyncio
from typing import Optional, Dict, Any
import httpx
from app.main import app

class AppTestClient:
    def __init__(self, fastapi_app=None, base_url: str = "http://testserver"):
        self.app = fastapi_app or app
        self.base_url = base_url

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        async def _run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app),
                base_url=self.base_url
            ) as client:
                return await client.request(method, url, **kwargs)
        return asyncio.run(_run())

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

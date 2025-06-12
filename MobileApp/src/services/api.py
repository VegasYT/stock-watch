import httpx

from state import session
from app.config import BASE_URL
from services.auth_service import refresh_access_token


async def api_request(
    method: str,
    endpoint: str,
    json: dict | None = None,
    params: dict | None = None,
    headers: dict | None = None,
    page=None,
    retry=True,
):
    all_headers = headers.copy() if headers else {}
    if session.jwt_token:
        all_headers["Authorization"] = f"Bearer {session.jwt_token}"

    url = f"{BASE_URL}{endpoint}"

    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, json=json, params=params, headers=all_headers, timeout=7)

        if resp.status_code == 401 and retry:
            result = await refresh_access_token(page=page)
            if result is None:
                if page:
                    page.go("/login")
                return None
                
            if result.get("ok"):
                return await api_request(method, endpoint, json, params, headers, page, retry=False)
            elif result.get("redirect") and page:
                page.go("/login")
                return None

        return resp

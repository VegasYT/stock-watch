import httpx

from app.config import BASE_URL
from state import session
from services.token_storage import save as save_tokens


async def login_user(email: str, password: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=5
            )
            if response.status_code == 200:
                return {"ok": True, "data": response.json()}
            else:
                return {"ok": False, "data": response.json()}
        except httpx.RequestError as e:
            return {"ok": False, "data": {"detail": str(e)}}


async def register_user(email: str, nickname: str, password: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "nickname": nickname, "password": password},
            timeout=5,
        )
        return {"ok": response.status_code == 200, "data": response.json()}


async def refresh_access_token(page=None) -> dict:
    if not session.refresh_token:
        print("🔒 Нет refresh_token — требуется переход на /login")
        session.jwt_token = None
        return {"ok": False, "redirect": True}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/auth/refresh",
                json={"token": session.refresh_token},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                session.jwt_token     = data["access_token"]
                session.refresh_token = data["refresh_token"]

                if page is not None:
                    await save_tokens(page, {
                        "jwt": session.jwt_token,
                        "refresh": session.refresh_token,
                    })

                print("🔁 Access token обновлён")
                return {"ok": True}

    except Exception as e:
        print("❌ Ошибка при refresh:", e)
        return {"ok": False, "redirect": True}

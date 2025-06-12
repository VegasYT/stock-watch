import httpx

from state import session
from app.config import BASE_URL


async def try_register_push():
    if session.push_registered:
        return           # уже отправляли

    if session.jwt_token and session.onesignal_id:
        await send_onesignal_id_to_server(session.onesignal_id)
        session.push_registered = True


async def send_onesignal_id_to_server(player_id: str | None):
    if not player_id:
        print("[OneSignal] ❌ ID не получен")
        return
    if not session.jwt_token:
        print("[OneSignal] ❌ Нет access_token")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/users/push/register",
            headers={"Authorization": f"Bearer {session.jwt_token}"},
            json={"player_id": player_id},
            timeout=5,
        )
    print(f"[OneSignal] 🔁 /users/push/register → {resp.status_code}")

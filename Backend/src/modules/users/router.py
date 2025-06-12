from fastapi import APIRouter, HTTPException, Request, status, Depends
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.database import get_async_session
from src.core.dependencies import get_current_user_id
from src.modules.users.service import UserService
from src.modules.users.schemas import OneSignalTokenIn, User, UserUpdate
from src.core.config import settings


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    service = UserService(session)
    try:
        return await service.get_user_by_id(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=list[User])
async def list_users(session: AsyncSession = Depends(get_async_session)):
    service = UserService(session)
    return await service.list_users()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    service = UserService(session)
    await service.delete_user(user_id)
    await session.commit()
    return None


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    service = UserService(session)
    try:
        updated_user = await service.update_user(user_id, user_update)
        await session.commit()
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    

@router.post("/push/register")
async def register_onesignal_token(
    data: OneSignalTokenIn,
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_current_user_id),
):
    print(f"player_id {data.player_id}")
    service = UserService(session)
    await service.register_onesignal_token(user_id, data.player_id)
    await session.commit()
    return {"status": "ok"}


@router.post("/push/test")
async def send_test_push(
    session: AsyncSession = Depends(get_async_session),
    user_id: int = Depends(get_current_user_id),
):
    # Получение player_id из базы
    query = text("SELECT player_id FROM onesignal_tokens WHERE user_id = :user_id")
    result = await session.execute(query, {"user_id": user_id})
    player_id = result.scalar_one_or_none()
    if not player_id:
        raise HTTPException(status_code=404, detail="player_id not found")

    async with httpx.AsyncClient() as client:
        # Получение subscription_id через OneSignal API v2
        url = f"https://api.onesignal.com/apps/{settings.PROJECT_ID}/users/by/onesignal_id/{player_id}"
        headers = {"Authorization": f"Bearer {settings.ONESIGNAL_API_KEY}"}
        user_response = await client.get(url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get subscription_id")

        user_data = user_response.json()
        subscriptions = user_data.get("subscriptions")
        if not subscriptions:
            raise HTTPException(status_code=404, detail="No subscriptions found")

        subscription_id = subscriptions[0]["id"]

        # Отправка push через API v2
        push_url = "https://api.onesignal.com/notifications?c=push"
        push_headers = {
            "Authorization": f"Bearer {settings.ONESIGNAL_API_KEY}",
            "Content-Type": "application/json"
        }
        push_body = {
            "app_id": settings.PROJECT_ID,
            "include_subscription_ids": [subscription_id],
            "headings": {"en": "Test Push"},
            "contents": {"en": "This is a test push notification"}
        }

        push_response = await client.post(push_url, headers=push_headers, json=push_body)

        if push_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Push send failed")

    return {"status": "ok", "push_id": push_response.json().get("id")}

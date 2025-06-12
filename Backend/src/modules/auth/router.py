from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from src.modules.auth.schemas import RefreshRequest, TokenPair
from src.core.database import get_async_session
from src.modules.auth.service import AuthService
from src.modules.users.repository import UserRepository
from src.modules.users.schemas import UserRequestAdd, UserRequestLogin
from src.core.dependencies import UserIdDep


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register_user(
    data: UserRequestAdd,
    session: AsyncSession = Depends(get_async_session),
):
    auth_service = AuthService(session)
    user = await auth_service.register_user(data)
    return {"status": "OK", "user_id": user.id}


@router.post("/login")
async def login_user(
    data: UserRequestLogin,
    session: AsyncSession = Depends(get_async_session),
):
    auth_service = AuthService(session)
    token_pair = await auth_service.login_user(data.email, data.password)
    return token_pair


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
):
    auth_service = AuthService(session)
    return await auth_service.refresh_tokens(data.token)


@router.get("/me")
async def get_me(
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    repo = UserRepository(session)
    user = await repo.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

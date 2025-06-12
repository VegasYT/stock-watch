from typing import Annotated
 
from fastapi import Depends, HTTPException, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.modules.auth.service import AuthService
from src.core.database import get_async_session


class PaginationParams(BaseModel):
    page_size: Annotated[int | None, Query(None, ge=1, lt=30, description="Кол-во элементов на странице")]
    page_number: Annotated[int | None, Query(1, ge=1, description="Номер страницы")]


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_async_session),
) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    auth_service = AuthService(session)
    payload = auth_service.decode_token(token)

    if "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return payload["user_id"]


UserIdDep = Annotated[int, Depends(get_current_user_id)]
PaginationDep = Annotated[PaginationParams, Depends()]
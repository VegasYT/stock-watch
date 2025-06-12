from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from src.core.database import get_async_session
from src.core.dependencies import PaginationDep, UserIdDep
from src.modules.portfolio.service import PortfolioService
from src.modules.portfolio.schemas import PortfolioItemChangeOut, PortfolioItemCreate, PortfolioItemDetailedOut, PortfolioItemInfoOut, PortfolioItemOut, PortfolioItemPatchRequest, PortfolioItemUpdate


router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/", response_model=list[PortfolioItemDetailedOut])
async def list_portfolio_items(
    user_id: UserIdDep,
    pagination: PaginationDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = PortfolioService(session)
    # await asyncio.sleep(1)
    return await service.get_all(
        user_id=user_id,
        skip=(pagination.page_number - 1) * (pagination.page_size or 12),
        limit=pagination.page_size or 12
    )


# @router.get("/{portfolio_id}", response_model=PortfolioItemDetailedOut)
# async def get_portfolio_item(
#     portfolio_id: int,
#     user_id: UserIdDep,
#     session: AsyncSession = Depends(get_async_session),
# ):
#     service = PortfolioService(session)
#     try:
#         return await service.get_one(portfolio_id, user_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))


@router.post("/", response_model=PortfolioItemOut, status_code=status.HTTP_201_CREATED)
async def add_portfolio_item(
    data: PortfolioItemCreate,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = PortfolioService(session)
    result = await service.create(data, user_id)
    return result


@router.patch("/{portfolio_id}", response_model=PortfolioItemOut)
async def update_portfolio_item(
    portfolio_id: int,
    data: PortfolioItemPatchRequest,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = PortfolioService(session)
    try:
        result = await service.update(portfolio_id, data, user_id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
    portfolio_id: int,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = PortfolioService(session)
    await service.delete(portfolio_id, user_id)
    await session.commit()
    return None


@router.get("/{portfolio_id}/info", response_model=PortfolioItemInfoOut)
async def get_portfolio_item_info(
    portfolio_id: int,
    pagination: PaginationDep,
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = PortfolioService(session)
    try:
        return await service.get_item_info(
            portfolio_id=portfolio_id,
            user_id=user_id,
            skip=(pagination.page_number - 1) * (pagination.page_size or 20),
            limit=pagination.page_size or 20,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.core.dependencies import PaginationDep, UserIdDep
from src.modules.stocks.service import StockService
from src.modules.stocks.schemas import StockOut, StockSearchOut, StockUpdate


router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/", response_model=list[StockOut])
async def list_stocks(
    user_id: UserIdDep,
    pagination: PaginationDep,
    session: AsyncSession = Depends(get_async_session),
):
    service = StockService(session)
    return await service.get_all(
        skip=(pagination.page_number - 1) * (pagination.page_size or 10),
        limit=pagination.page_size or 10
    )


@router.get("/search", response_model=list[StockSearchOut])
async def search_stocks(
    user_id: UserIdDep,
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_async_session),
):
    service = StockService(session)
    results = await service.search_stocks(q)
    return results


@router.get("/{stock_id}", response_model=StockOut)
async def get_stock(
    user_id: UserIdDep,
    stock_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    service = StockService(session)
    try:
        return await service.get_one(stock_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{stock_id}", response_model=StockOut)
async def update_stock(
    user_id: UserIdDep,
    stock_id: int,
    data: StockUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = StockService(session)
    try:
        updated = await service.update(stock_id, data)
        await session.commit()
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(
    user_id: UserIdDep,
    stock_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    service = StockService(session)
    await service.delete(stock_id)
    await session.commit()
    return None


@router.post("/parse-stocks-moex")
async def pars_stocks_moex(
    user_id: UserIdDep,
    session: AsyncSession = Depends(get_async_session)
):
    service = StockService(session)
    count = await service.pars_stocks_moex()
    return {"status": "ok", "synced": count}


@router.post("/recalculate-colors")
async def recalc_colors(
    user_id: UserIdDep,
    symbol: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session)
):
    service = StockService(session)
    count = await service.recalculate_dominant_color(symbol)
    return {"status": "ok", "updated": count}

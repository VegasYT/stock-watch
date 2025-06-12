from fastapi import APIRouter, Body, Depends, HTTPException, Query
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import UserIdDep, get_current_user_id
from src.core.database import get_async_session
from src.modules.stock_prices.schemas import StockPriceCreate, StockPriceHistoryResponse, StockPriceOut
from src.modules.stock_prices.service import StockPriceService

router = APIRouter(prefix="/prices", tags=["Stock Prices"])


@router.post("/", response_model=StockPriceOut)
async def add_price(
    user_id: UserIdDep,
    data: StockPriceCreate,
    session: AsyncSession = Depends(get_async_session),
):
    service = StockPriceService(session)
    return await service.add_price(data)


@router.get("/latest/{stock_id}", response_model=StockPriceOut)
async def get_latest_price(
    user_id: UserIdDep,
    stock_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    service = StockPriceService(session)
    return await service.get_latest(stock_id)


@router.get("/history/{stock_id}", response_model=StockPriceHistoryResponse)
async def get_price_history(
    stock_id: int,
    ser_id: UserIdDep,
    days: int = 30,
    count: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    service = StockPriceService(session)
    return await service.get_dynamic_aggregated_history(stock_id, days, count)


@router.post("/sync")
async def sync_prices(
    user_id: UserIdDep,
    board: str = Query(...),
    from_date: str | None = Query(None, description="Формат: YYYY-MM-DD"),
    till_date: str | None = Query(None, description="Формат: YYYY-MM-DD"),
    symbol: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session)
):
    service = StockPriceService(session)
    count = await service.sync_from_moex(board, from_date, till_date, symbol)
    return {"status": "ok", "synced": count}

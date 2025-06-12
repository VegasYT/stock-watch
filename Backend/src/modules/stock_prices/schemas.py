from pydantic import BaseModel
from datetime import datetime


class StockPriceBase(BaseModel):
    stock_id: int
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    value: float | None = None


class StockPriceCreate(StockPriceBase):
    pass


class StockPriceOut(StockPriceBase):
    # id: int
    pass


class StockPriceHistoryResponse(BaseModel):
    data: list[StockPriceOut]
    change: float
    change_rub: float
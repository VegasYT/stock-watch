from pydantic import BaseModel


class StockBase(BaseModel):
    symbol: str
    name: str
    board: str


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    symbol: str | None = None
    name: str | None = None
    board: str | None = None


class StockOut(StockBase):
    id: int
    dominant_color: str | None = None


class StockSearchOut(BaseModel):
    id: int
    symbol: str
    shortname: str | None

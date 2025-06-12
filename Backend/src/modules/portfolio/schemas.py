from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TransactionIn(BaseModel):
    quantity: float
    price: float
    type: TransactionType
    timestamp: datetime


class TransactionUpdateIn(BaseModel):
    id: int
    quantity: float
    price: float
    type: TransactionType
    timestamp: datetime
    

class TransactionOut(TransactionIn):
    id: int
    portfolio_id: int = None
    symbol: str = None
    
    model_config = {
        "from_attributes": True
    }


class PortfolioItemBase(BaseModel):
    stock_id: int
    quantity: float


class PortfolioItemDB(PortfolioItemBase):
    user_id: int


class PortfolioItemCreate(PortfolioItemBase):
    transactions: list[TransactionIn] = []


class PortfolioItemUpdate(BaseModel):
    quantity: Optional[float] = None


class PortfolioItemPatchRequest(BaseModel):
    quantity: Optional[float] = None
    add_transactions: Optional[list[TransactionIn]] = []
    delete_transaction_ids: Optional[list[int]] = []
    update_transactions: Optional[list[TransactionUpdateIn]] = []


class PortfolioItemOut(PortfolioItemBase):
    id: int
    user_id: int


class PortfolioItemDetailedOut(BaseModel):
    id: int
    user_id: int
    stock_id: int
    quantity: float
    added_at: datetime

    symbol: str
    shortname: str
    name: str | None = None
    isin: str | None = None
    emitent_title: str | None = None

    price: float | None = None
    change: str = "0"
    change_rub: float = 0.0
    dominant_color: str | None = None
    # transactions: list[TransactionOut] = []
    last_10_closes: list[float] = []


class PortfolioItemInfoOut(BaseModel):
    # name: str | None = None
    # isin: str | None = None
    # emitent_title: str | None = None
    transactions: list[TransactionOut] = []
    total: int


class PortfolioItemChangeOut(BaseModel):
    change: str
    change_rub: float
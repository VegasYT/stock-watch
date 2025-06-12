from pydantic import BaseModel, Field
from datetime import datetime


class AlertBase(BaseModel):
    stock_id: int
    condition: str = Field(..., pattern="^(above|below)$")
    value: float


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_active: bool | None = None
    triggered_at: datetime | None = None


class AlertOut(AlertBase):
    id: int
    is_active: bool
    triggered_at: datetime | None
    created_at: datetime
    symbol: str | None = None

    class Config:
        from_attributes = True

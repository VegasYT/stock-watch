from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy import ForeignKey, UniqueConstraint, String
from datetime import datetime
from enum import Enum

from src.core.database import Base


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"
    __table_args__ = (UniqueConstraint('user_id', 'stock_id'),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    transactions: Mapped[list["PortfolioTransaction"]] = relationship(
        back_populates="portfolio_item", cascade="all, delete-orphan"
    )


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_item_id: Mapped[int] = mapped_column(ForeignKey("portfolio_items.id", ondelete="CASCADE"))
    portfolio_item: Mapped["PortfolioItem"] = relationship(back_populates="transactions")
    quantity: Mapped[float]
    price: Mapped[float]
    type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
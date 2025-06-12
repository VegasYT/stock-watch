from sqlalchemy import Table, ForeignKey, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from src.core.database import Base


news_stocks = Table(
    "news_stocks",
    Base.metadata,
    Column("news_id", Integer, ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
    Column("stock_id", Integer, ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True),
)


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    published: Mapped[datetime] = mapped_column(nullable=False)
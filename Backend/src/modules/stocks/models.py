from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)  # из secid
    shortname: Mapped[str] = mapped_column(nullable=True)
    regnumber: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)
    isin: Mapped[str] = mapped_column(nullable=True)
    emitent_title: Mapped[str] = mapped_column(nullable=True)
    emitent_inn: Mapped[str] = mapped_column(nullable=True)
    emitent_okpo: Mapped[str] = mapped_column(nullable=True)
    board: Mapped[str] = mapped_column(nullable=True)  # из primary_boardid
    dominant_color: Mapped[str] = mapped_column(nullable=True)
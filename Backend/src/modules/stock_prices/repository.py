from sqlalchemy import select, func, cast, Date, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from datetime import date

from src.core.repository import BaseRepository
from src.modules.stock_prices.models import StockPrice
from src.modules.stock_prices.schemas import StockPriceOut


class StockPriceRepository(BaseRepository):
    model = StockPrice
    schema = StockPriceOut

    async def get_latest_by_stock(self, stock_id: int):
        stmt = (
            select(self.model)
            .filter_by(stock_id=stock_id)
            .order_by(self.model.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        obj = result.scalars().first()
        return self.schema.model_validate(obj, from_attributes=True) if obj else None

    async def get_history_by_stock(self, stock_id: int, limit: int = 100):
        stmt = (
            select(self.model)
            .filter_by(stock_id=stock_id)
            .order_by(self.model.date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self.schema.model_validate(obj, from_attributes=True) for obj in result.scalars().all()]

    async def exists(self, stock_id: int, date) -> bool:
        stmt = select(self.model).filter(
            and_(self.model.stock_id == stock_id, self.model.date == date)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def get_latest_map(self, stock_ids: list[int], per_stock: int = 2):
        stmt = (
            select(self.model)
            .where(self.model.stock_id.in_(stock_ids))
            .order_by(self.model.stock_id, self.model.date.desc())
        )
        result = await self.session.execute(stmt)
        prices = result.scalars().all()

        grouped = defaultdict(list)
        for p in prices:
            grouped[p.stock_id].append(p)
            if len(grouped[p.stock_id]) >= per_stock:
                continue

        return grouped
    
    async def bulk_upsert_prices(self, prices: list[StockPrice]) -> int:
        added = 0
        for p in prices:
            stmt = select(self.model).filter_by(stock_id=p.stock_id, date=p.date)
            result = await self.session.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                self.session.add(p)
                added += 1

        return added

    async def get_last_closes_map(self, stock_ids: list[int], n: int = 10) -> dict[int, list[float]]:
        stmt = (
            select(self.model)
            .where(self.model.stock_id.in_(stock_ids))
            .order_by(self.model.stock_id, self.model.date.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        from collections import defaultdict
        grouped = defaultdict(list)

        for row in rows:
            if len(grouped[row.stock_id]) < n:
                grouped[row.stock_id].append(row.close)

        return grouped

    async def get_prices_by_stock(self, stock_id: int, limit: int | None = None):
        stmt = (
            select(self.model)
            .where(self.model.stock_id == stock_id)
            .order_by(self.model.date.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_stock_and_date(self, stock_id: int, date: date) -> int:
        stmt = select(func.count()).where(
            self.model.stock_id == stock_id,
            cast(self.model.date, Date) == date
        )
        result = await self.session.execute(stmt)
        return result.scalar()

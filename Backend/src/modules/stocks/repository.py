from sqlalchemy import select, or_, func, update

from src.core.repository import BaseRepository
from src.modules.stocks.models import Stock
from src.modules.stocks.schemas import StockOut


class StockRepository(BaseRepository):
    model = Stock
    schema = StockOut

    async def get_by_ids(self, stock_ids: list[int]):
        stmt = select(self.model).where(self.model.id.in_(stock_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_many(self, stock_data: list[dict]):
        for data in stock_data:
            symbol = data.get("secid")
            stmt = select(self.model).filter_by(symbol=symbol)
            existing = await self.session.execute(stmt)
            stock = existing.scalars().first()

            values = {
                "shortname": data.get("shortname"),
                "regnumber": data.get("regnumber"),
                "name": data.get("name"),
                "isin": data.get("isin"),
                "emitent_title": data.get("emitent_title"),
                "emitent_inn": data.get("emitent_inn"),
                "emitent_okpo": data.get("emitent_okpo"),
                "board": data.get("primary_boardid"),
            }

            if stock:
                for key, value in values.items():
                    setattr(stock, key, value)
            else:
                self.session.add(self.model(symbol=symbol, **values))

    async def search_by_text(self, query: str):
        stmt = select(self.model).where(
            or_(
                func.lower(self.model.symbol).like(f"%{query.lower()}%"),
                func.lower(self.model.shortname).like(f"%{query.lower()}%")
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    

    async def update_color(self, symbol: str, color: str):
        stmt = (
            update(self.model)
            .where(self.model.symbol == symbol)
            .values(dominant_color=color)
        )
        await self.session.execute(stmt)
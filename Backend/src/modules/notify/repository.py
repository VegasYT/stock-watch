from sqlalchemy import select

from src.core.repository import BaseRepository
from src.modules.notify.models import Alert
from src.modules.stocks.models import Stock
from src.modules.notify.schemas import AlertOut


class AlertRepository(BaseRepository):
    model = Alert
    schema = AlertOut

    async def get_filtered(self, user_id: int, stock_id: int | None = None, page: int = 1, page_size: int = 20):
        query = (
            select(self.model, Stock.symbol)
            .join(Stock, Stock.id == self.model.stock_id)
            .filter(self.model.user_id == user_id)
        )
        if stock_id is not None:
            query = query.filter(self.model.stock_id == stock_id)
        query = query.order_by(self.model.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        items = []
        for obj, symbol in result.all():
            # model_validate автоматически примет symbol, если он есть в AlertOut
            d = self.schema.model_validate(obj, from_attributes=True).dict()
            d['symbol'] = symbol
            items.append(self.schema(**d))
        return items
    
    async def create_alert(self, user_id: int, stock_id: int, condition: str, value: float):
        alert = self.model(
            user_id=user_id,
            stock_id=stock_id,
            condition=condition,
            value=value,
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def get_all_active(self):
        query = select(self.model).where(self.model.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_player_id(self, user_id: int) -> str | None:
        query = select(self.model.player_id).where(self.model.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

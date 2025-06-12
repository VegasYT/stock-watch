from sqlalchemy import select, delete,  func, insert, update
from sqlalchemy.orm import selectinload

from src.core.repository import BaseRepository
from src.modules.portfolio.models import PortfolioItem, PortfolioTransaction
from src.modules.portfolio.schemas import PortfolioItemOut


class PortfolioRepository(BaseRepository):
    model = PortfolioItem
    schema = PortfolioItemOut

    async def get_by_user(self, user_id: int, skip: int, limit: int):
        stmt = (
            select(self.model)
            .filter_by(user_id=user_id)
            .order_by(PortfolioItem.added_at.asc())
            .options(selectinload(PortfolioItem.transactions)) 
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_full_with_transactions(self, id: int):
        stmt = (
            select(self.model)
            .where(self.model.id == id)
            .options(selectinload(self.model.transactions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def add_transactions(self, transactions: list[PortfolioTransaction]):
        for tx in transactions:
            self.session.add(tx)

    async def delete_transactions(self, portfolio_id: int, transaction_ids: list[int]):
        await self.session.execute(
            delete(PortfolioTransaction).where(
                PortfolioTransaction.id.in_(transaction_ids),
                PortfolioTransaction.portfolio_item_id == portfolio_id
            )
        )

    async def bulk_update_transactions(self, portfolio_id: int, tx_list: list):
        for tx in tx_list:
            stmt = (
                update(PortfolioTransaction)
                .where(
                    PortfolioTransaction.id == tx.id,
                    PortfolioTransaction.portfolio_item_id == portfolio_id
                )
                .values(
                    quantity=tx.quantity,
                    price=tx.price,
                    type=tx.type.value,
                    timestamp=tx.timestamp
                )
            )
            await self.session.execute(stmt)
    
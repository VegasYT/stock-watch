from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
# from sqlalchemy import delete
from sqlalchemy import delete, update as sqlalchemy_update

from src.modules.portfolio.models import PortfolioTransaction
from src.modules.stock_prices.repository import StockPriceRepository
from src.modules.stocks.repository import StockRepository
from src.modules.portfolio.repository import PortfolioRepository
from src.modules.portfolio.schemas import PortfolioItemChangeOut, PortfolioItemDetailedOut, PortfolioItemInfoOut, PortfolioItemPatchRequest, PortfolioItemUpdate, PortfolioItemOut, PortfolioItemCreate, PortfolioItemDB, TransactionOut


class PortfolioService:
    def __init__(self, session: AsyncSession):
        self.repo = PortfolioRepository(session)
        self.stock_repo = StockRepository(session)
        self.price_repo = StockPriceRepository(session)

    async def get_all(self, user_id: int, skip: int, limit: int) -> list[PortfolioItemDetailedOut]:
        items = await self.repo.get_by_user(user_id, skip, limit)
        if not items:
            return []

        stock_ids = [i.stock_id for i in items]
        stocks = await self.stock_repo.get_by_ids(stock_ids)
        prices_by_stock = await self.price_repo.get_latest_map(stock_ids)
        closes_map = await self.price_repo.get_last_closes_map(stock_ids, n=10)

        stock_map = {s.id: s for s in stocks}
        output = []

        for item in items:
            stock = stock_map.get(item.stock_id)
            price_data = prices_by_stock.get(item.stock_id, [])
            price = price_data[0].close if price_data else None

            closes = closes_map.get(item.stock_id, [])

            change = "0"
            change_rub = 0.0
            if len(closes) >= 10 and closes[9]:
                latest = closes[0]
                tenth = closes[9]
                if tenth != 0:
                    delta = latest - tenth
                    percent = (delta / tenth) * 100
                    sign = "+" if percent > 0 else ""
                    change = f"{sign}{percent:.1f}%"
                    change_rub = round(delta * item.quantity, 2)

            output.append(PortfolioItemDetailedOut(
                id=item.id,
                user_id=item.user_id,
                stock_id=item.stock_id,
                quantity=item.quantity,
                # transactions=[TransactionOut.model_validate(t) for t in item.transactions],
                added_at=item.added_at,
                symbol=stock.symbol if stock else "",
                shortname=stock.shortname if stock else "",
                name=stock.name if stock else "",
                isin=stock.isin if stock else "",
                emitent_title=stock.emitent_title if stock else "",
                price=price,
                change=change,
                change_rub=change_rub,
                dominant_color=stock.dominant_color if stock else None,
                last_10_closes=closes,
            ))

        return output

    async def get_one(self, portfolio_id: int, user_id: int) -> PortfolioItemDetailedOut:
        item = await self.repo.get_full_with_transactions(portfolio_id)
        if not item or item.user_id != user_id:
            raise ValueError("Элемент не найден или не принадлежит пользователю")

        stocks = await self.stock_repo.get_by_ids([item.stock_id])
        stock = stocks[0] if stocks else None
        price_data = await self.price_repo.get_latest_by_stock(item.stock_id)
        closes = await self.price_repo.get_last_closes_map([item.stock_id], n=10)

        closes_list = closes.get(item.stock_id, [])

        change = "0"
        change_rub = 0.0
        if len(closes_list) >= 10 and closes_list[9]:
            delta = closes_list[0] - closes_list[9]
            percent = (delta / closes_list[9]) * 100
            sign = "+" if percent > 0 else ""
            change = f"{sign}{percent:.1f}%"
            change_rub = round(delta * item.quantity, 2)

        return PortfolioItemDetailedOut(
            id=item.id,
            user_id=item.user_id,
            stock_id=item.stock_id,
            quantity=item.quantity,
            added_at=item.added_at,
            symbol=stock.symbol if stock else "",
            shortname=stock.shortname if stock else "",
            name=stock.name if stock else "",
            isin=stock.isin if stock else "",
            emitent_title=stock.emitent_title if stock else "",
            price=price_data.close if price_data else None,
            change=change,
            change_rub=change_rub,
            transactions=[TransactionOut.model_validate(t) for t in item.transactions],
            last_10_closes=closes_list
        )
    
    async def create(self, data: PortfolioItemCreate, user_id: int) -> PortfolioItemOut:
        raw = data.model_dump(exclude={"transactions"})
        item_in = PortfolioItemDB(**raw, user_id=user_id)
        try:
            item = await self.repo.add(item_in)
            await self.repo.session.flush()  # получаем item.id без коммита

            for tx in data.transactions:
                tx_obj = PortfolioTransaction(
                    portfolio_item_id=item.id,
                    quantity=tx.quantity,
                    price=tx.price,
                    type=tx.type.value,
                    timestamp=tx.timestamp,
                )
                self.repo.session.add(tx_obj)

            await self.repo.session.commit()
            return await self.get_one(item.id, user_id)
        except IntegrityError as e:
            await self.repo.session.rollback()
            # Проверка по constraint name
            if "portfolio_items_user_id_stock_id_key" in str(e.orig):
                raise HTTPException(
                    status_code=409,
                    detail="Такой актив уже есть в вашем портфеле"
                )
            raise HTTPException(
                status_code=400,
                detail="Ошибка добавления актива"
            )

    async def update(self, portfolio_id: int, data: PortfolioItemPatchRequest, user_id: int) -> PortfolioItemOut:
        item = await self.get_one(portfolio_id, user_id)

        # Обновить количество
        if data.quantity is not None:
            await self.repo.edit(PortfolioItemUpdate(quantity=data.quantity), id=portfolio_id, is_patch=True)

        # Добавить новые транзакции
        if data.add_transactions:
            tx_objs = [
                PortfolioTransaction(
                    portfolio_item_id=portfolio_id,
                    quantity=tx.quantity,
                    price=tx.price,
                    type=tx.type.value,
                    timestamp=tx.timestamp,
                )
                for tx in data.add_transactions
            ]
            await self.repo.add_transactions(tx_objs)

        # Удалить транзакции по ID
        if data.delete_transaction_ids:
            await self.repo.delete_transactions(portfolio_id, data.delete_transaction_ids)

        # Обновить существующие транзакции
        if data.update_transactions:
            await self.repo.bulk_update_transactions(portfolio_id, data.update_transactions)

        await self.repo.session.commit()
        return await self.get_one(portfolio_id, user_id)

    async def delete(self, portfolio_id: int, user_id: int) -> None:
        item = await self.get_one(portfolio_id, user_id)
        await self.repo.delete(id=portfolio_id)


    async def get_item_info(self, portfolio_id: int, user_id: int, skip: int, limit: int) -> PortfolioItemInfoOut:
        """
        Возвращает информацию о сделках пользователя.

        Особое значение ``portfolio_id == -1`` означает «все активы пользователя».
        В этом режиме агрегируем все транзакции по *всем* позициям портфеля,
        сортируем их по дате (самые новые сверху) и применяем пагинацию.
        """

        # Режим «все активы»
        if portfolio_id == -1:
            items = await self.repo.get_by_user(user_id, skip=0, limit=10_000)
            all_tx = []
            portfolio_map = {}
            stock_ids = set()

            # Собираем все транзакции и маппинг portfolio_id -> stock_id
            for item in items:
                portfolio_map[item.id] = item.stock_id
                stock_ids.add(item.stock_id)
                all_tx.extend(item.transactions)

            # Получаем все нужные symbols за 1 запрос
            stocks = await self.stock_repo.get_by_ids(list(stock_ids))
            symbol_map = {s.id: s.symbol for s in stocks}

            all_tx.sort(key=lambda t: t.timestamp, reverse=True)
            total = len(all_tx)
            sliced = all_tx[skip: skip + (limit or 20)]

            # Расширяем TransactionOut, добавляя symbol
            enriched = []
            for t in sliced:
                stock_id = portfolio_map.get(t.portfolio_item_id)
                symbol = symbol_map.get(stock_id, "") if stock_id else ""
                tx_out = TransactionOut(
                    id=t.id,
                    portfolio_id=t.portfolio_item_id,
                    quantity=t.quantity,
                    price=t.price,
                    type=t.type,
                    timestamp=t.timestamp,
                )
                tx_out_dict = tx_out.model_dump()
                tx_out_dict["symbol"] = symbol
                enriched.append(tx_out_dict)

            return {
                "transactions": enriched,
                "total": total,
            }

        # Обычный режим (один актив)
        item = await self.repo.get_full_with_transactions(portfolio_id)
        if not item or item.user_id != user_id:
            raise ValueError("Элемент не найден или не принадлежит пользователю")

        total = len(item.transactions)
        sliced = item.transactions[skip: skip + limit]

        return PortfolioItemInfoOut(
            transactions=[
                TransactionOut(
                    id=t.id,
                    portfolio_id=t.portfolio_item_id,
                    quantity=t.quantity,
                    price=t.price,
                    type=t.type,
                    timestamp=t.timestamp,
                )
                for t in sliced
            ],
            total=total,
        )

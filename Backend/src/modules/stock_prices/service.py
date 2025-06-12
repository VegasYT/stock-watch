import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, date
from fastapi import HTTPException
# import requests
import httpx
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.modules.stock_prices.models import StockPrice
from src.modules.stocks.repository import StockRepository
from src.modules.stock_prices.repository import StockPriceRepository
from src.modules.stock_prices.schemas import StockPriceCreate, StockPriceHistoryResponse, StockPriceOut


class StockPriceService:
    def __init__(self, session: AsyncSession):
        self.stock_repo = StockRepository(session)
        self.repo = StockPriceRepository(session)
        self.session = session

    async def add_price(self, data: StockPriceCreate) -> StockPriceOut:
        if await self.repo.exists(data.stock_id, data.date):
            raise HTTPException(status_code=409, detail="Данные за эту дату уже существуют")

        obj = await self.repo.add(data)
        await self.repo.session.commit()
        return await self.repo.get_latest_by_stock(data.stock_id)

    async def get_latest(self, stock_id: int) -> StockPriceOut:
        result = await self.repo.get_latest_by_stock(stock_id)
        if not result:
            raise HTTPException(status_code=404, detail="Цена не найдена")
        return result

    async def get_dynamic_aggregated_history(self, stock_id: int, days: int, count: int) -> StockPriceHistoryResponse:
        from collections import defaultdict

        if days == 0:
            raw = await self.repo.get_prices_by_stock(stock_id)
        else:
            approx_working_days = int(days * 5 / 7)
            total_hours = approx_working_days * 17
            raw = await self.repo.get_prices_by_stock(stock_id, limit=total_hours)

        if not raw:
            return StockPriceHistoryResponse(data=[], change=0.0, change_rub=0.0)

        # Аггрегация по count — всегда, независимо от days
        group_size = max(1, len(raw) // count)
        grouped = defaultdict(list)
        for i, row in enumerate(raw):
            idx = i // group_size
            grouped[idx].append(row)

        aggregated = []
        for rows in grouped.values():
            if not rows:
                continue
            rows = list(reversed(rows))
            aggregated.append(StockPriceOut(
                stock_id=stock_id,
                date=rows[-1].date,
                open=rows[0].open,
                close=rows[-1].close,
                high=max(r.high for r in rows),
                low=min(r.low for r in rows),
                volume=sum(r.volume or 0 for r in rows),
                value=sum(r.value or 0 for r in rows)
            ))
        aggregated = list(reversed(aggregated))

        first_close = aggregated[0].close
        last_close = aggregated[-1].close
        change_rub = last_close - first_close
        change = (change_rub / first_close) * 100 if first_close else 0.0

        return StockPriceHistoryResponse(
            data=aggregated,
            change=round(change, 2),
            change_rub=round(change_rub, 2)
        )


    @staticmethod
    async def sync_from_moex(board: str, from_date: str | None, till_date: str | None, symbol: str | None = None) -> int:
        async with async_session_maker() as session:
            service = StockPriceService(session)
            stock_repo = service.stock_repo
            repo = service.repo

            stocks = await stock_repo.get_all()
            stocks = [s for s in stocks if s.board == board]
            if symbol:
                stocks = [s for s in stocks if s.symbol == symbol]

            if not stocks:
                return 0

            today = date.today()
            total = 0

            for stock in stocks:
                await asyncio.sleep(0.05)  # троттлинг

                count_today = await repo.count_by_stock_and_date(stock.id, today)
                if count_today >= 17:
                    print(f"[~] {stock.symbol} — уже {count_today} свечей, пропускаем")
                    continue

                actual_from = from_date
                actual_till = till_date or today.strftime("%Y-%m-%d")

                if not from_date:
                    latest = await repo.get_latest_by_stock(stock.id)
                    if latest:
                        actual_from = latest.date.strftime("%Y-%m-%d")
                    else:
                        one_month_ago = today - timedelta(days=30)
                        actual_from = one_month_ago.strftime("%Y-%m-%d")

                try:
                    prices = await service._fetch_prices_for_stock(
                        stock_id=stock.id,
                        symbol=stock.symbol,
                        board=board,
                        from_date=actual_from,
                        till_date=actual_till
                    )
                    added_count = await repo.bulk_upsert_prices(prices)
                    await session.commit()
                    total += added_count

                    if added_count > 0:
                        print(f"[✓] {stock.symbol} — добавлено {added_count} новых цен")
                    else:
                        print(f"[=] {stock.symbol} — новых цен нет")

                except Exception as e:
                    await session.rollback()
                    print(f"[!] Ошибка при обработке {stock.symbol}: {e}")
                    continue

            return total

    async def _fetch_prices_for_stock(self, stock_id: int, symbol: str, board: str, from_date: str, till_date: str) -> list[StockPrice]:
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{symbol}/candles.json"
        full_data = []

        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        till_dt = datetime.strptime(till_date, "%Y-%m-%d")
        step = timedelta(days=25)
        current = from_dt

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            while current <= till_dt:
                next_until = min(current + step, till_dt)
                params = {
                    "from": current.strftime("%Y-%m-%d"),
                    "till": next_until.strftime("%Y-%m-%d"),
                    "interval": 60,
                }

                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    columns = data.get("candles", {}).get("columns", [])
                    rows = data.get("candles", {}).get("data", [])

                    if not columns or not rows:
                        current = next_until + timedelta(days=1)
                        continue

                    idx = {col: i for i, col in enumerate(columns)}

                    for row in rows:
                        try:
                            begin = datetime.strptime(row[idx["begin"]], "%Y-%m-%d %H:%M:%S")
                            full_data.append(StockPrice(
                                stock_id=stock_id,
                                date=begin,
                                open=row[idx["open"]],
                                high=row[idx["high"]],
                                low=row[idx["low"]],
                                close=row[idx["close"]],
                                volume=row[idx["volume"]],
                                value=row[idx["value"]],
                            ))
                        except Exception as e:
                            print(f"[!] Ошибка при обработке свечи: {e}, строка: {row}")
                            continue

                except Exception as e:
                    print(f"[!] Ошибка запроса с {params['from']} по {params['till']}: {e}")

                current = next_until + timedelta(days=1)

        return full_data
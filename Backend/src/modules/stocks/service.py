import os, ctypes
CAIRO_DIR = r"C:\Program Files\GTK3-Runtime Win64\bin"
os.add_dll_directory(CAIRO_DIR)
ctypes.CDLL(os.path.join(CAIRO_DIR, "libcairo-2.dll"))

from PIL import Image
from io import BytesIO
from fastapi import requests
import httpx
import cairosvg

from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.stocks.repository import StockRepository
from src.modules.stocks.schemas import StockSearchOut, StockUpdate, StockOut


def get_dominant_color_hex(img: Image.Image) -> str:
    img = img.convert("RGB").resize((64, 64))
    pixels = list(img.getdata())
    by_color = {}
    for r, g, b in pixels:
        key = (r, g, b)
        by_color[key] = by_color.get(key, 0) + 1
    dominant = max(by_color, key=by_color.get)
    return '#%02x%02x%02x' % dominant


class StockService:
    def __init__(self, session: AsyncSession):
        self.repo = StockRepository(session)
        self.session = session


    async def get_all(self, skip: int, limit: int) -> list[StockOut]:
        all_stocks = await self.repo.get_all()
        return all_stocks[skip:skip+limit]


    async def get_one(self, stock_id: int) -> StockOut:
        stock = await self.repo.get_one_or_none(id=stock_id)
        if not stock:
            raise ValueError("Акция не найдена")
        return stock


    async def update(self, stock_id: int, data: StockUpdate) -> StockOut:
        await self.repo.edit(data, id=stock_id, is_patch=True)
        return await self.get_one(stock_id)


    async def delete(self, stock_id: int) -> None:
        await self.repo.delete(id=stock_id)


    async def pars_stocks_moex(self) -> int:
        url = "https://iss.moex.com/iss/securities.json"
        params = {
            "engine": "stock",
            "market": "shares",
            "is_trading": 1,
            "start": 0
        }

        all_rows = []
        while True:
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()

            columns = data["securities"]["columns"]
            rows = data["securities"]["data"]
            if not rows:
                break

            for row in rows:
                item = dict(zip(columns, row))
                secid = item.get("secid")
                if isinstance(secid, str) and not secid.startswith("RU0"):
                    all_rows.append(item)

            params["start"] += len(rows)

        await self.repo.upsert_many(all_rows)
        await self.session.commit()
        return len(all_rows)


    async def search_stocks(self, text: str) -> list[StockSearchOut]:
        stocks = await self.repo.search_by_text(text)

        # Фильтрация по TQBR
        filtered = [
            s for s in stocks
            if s.board == "TQBR" and (
                text.lower() in (s.symbol or "").lower() or
                text.lower() in (s.shortname or "").lower()
            )
        ]

        # Сортировка по релевантности (по позиции совпадения)
        def relevance(stock):
            symbol_pos = (stock.symbol or "").lower().find(text.lower())
            name_pos = (stock.shortname or "").lower().find(text.lower())
            symbol_pos = symbol_pos if symbol_pos >= 0 else 999
            name_pos = name_pos if name_pos >= 0 else 999
            return min(symbol_pos, name_pos), stock.id

        sorted_results = sorted(filtered, key=relevance)

        return [
            StockSearchOut(id=s.id, symbol=s.symbol, shortname=s.shortname)
            for s in sorted_results[:6]
        ]


    async def recalculate_dominant_color(self, symbol: str | None = None) -> int:
        stocks = await self.repo.get_all()
        if symbol:
            stocks = [s for s in stocks if s.symbol == symbol]
        updated = 0
        async with httpx.AsyncClient() as client:
            for stock in stocks:
                url = f"https://finrange.com/storage/companies/logo/svg/MOEX_{stock.symbol}.svg"
                try:
                    r = await client.get(url)
                    r.raise_for_status()

                    # конвертация SVG → PNG
                    png_bytes = cairosvg.svg2png(bytestring=r.content)
                    img = Image.open(BytesIO(png_bytes))
                    color = get_dominant_color_hex(img)

                    await self.repo.update_color(stock.symbol, color)
                    updated += 1
                except Exception as e:
                    print(f"[!] Ошибка обработки {stock.symbol}: {e}")
        await self.session.commit()
        return updated
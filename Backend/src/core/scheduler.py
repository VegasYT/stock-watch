from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import logging

from src.modules.stock_prices.service import StockPriceService
from src.modules.notify.service import AlertService
from src.core.database import async_session_maker


MOSCOW = pytz.timezone("Europe/Moscow")

scheduler = AsyncIOScheduler(timezone=MOSCOW)


async def sync_tqbr_prices():
    now = datetime.now(MOSCOW)
    logging.info(f"[{now}] Старт синхронизации TQBR")

    async with async_session_maker() as session:
        price_service = StockPriceService(session)
        await price_service.sync_from_moex(board="TQBR", from_date=None, till_date=None)

        # После обновления цен проверяем алерты
        alert_service = AlertService(session)
        await alert_service.check_all()

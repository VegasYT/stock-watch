from fastapi import HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stocks.repository import StockRepository
from src.modules.notify.repository import AlertRepository
from src.modules.notify.schemas import AlertCreate, AlertUpdate
from src.modules.stock_prices.repository import StockPriceRepository
from src.modules.stocks.models import Stock
from src.modules.users.repository import OneSignalTokenRepository
from src.core.config import settings


class AlertService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AlertRepository(session)
        self.price_repo = StockPriceRepository(session)
        self.onesignal_repo = OneSignalTokenRepository(session)
        self.stock_repo = StockRepository(session)

    # === CRUD ===
    async def create_alert(self, user_id: int, data: AlertCreate):
        stock = await self.price_repo.get_one_or_none(id=data.stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="Актив не найден")

        # Проверка на дублирующий алерт
        exists = await self.repo.get_one_or_none(
            user_id=user_id,
            stock_id=data.stock_id,
            condition=data.condition,
            value=data.value,
        )
        if exists:
            raise HTTPException(status_code=409, detail="Такой алерт уже существует")

        # alert_in = self.repo.model(
        #     user_id=user_id,
        #     stock_id=data.stock_id,
        #     condition=data.condition,
        #     value=data.value,
        # )
        # self.session.add(alert_in)
        # await self.session.commit()
        # await self.session.refresh(alert_in)

        return await self.repo.create_alert(user_id, data.stock_id, data.condition, data.value)
        # return alert_in

    async def list_alerts(self, user_id: int, stock_id: int | None = None, page: int = 1, page_size: int = 20):
        return await self.repo.get_filtered(user_id, stock_id, page, page_size)

    async def deactivate(self, alert_id: int, user_id: int):
        await self.repo.edit(AlertUpdate(is_active=False), id=alert_id, user_id=user_id)

        await self.session.commit()

    # === Фоновая проверка ===
    async def check_all(self):
        """Проверяем все активные алерты, отправляем push и деактивируем сработавшие."""
        alerts = await self.repo.get_all_active()

        for alert in alerts:
            latest = await self.price_repo.get_latest_by_stock(alert.stock_id)
            if not latest:
                continue

            is_triggered = (
                (alert.condition == "above" and latest.close >= alert.value) or
                (alert.condition == "below" and latest.close <= alert.value)
            )
            if not is_triggered:
                continue

            # print(f"stock_id {alert.stock_id}")
            success = await self._send_push(alert.user_id, alert.stock_id, latest.close)
            if success:
                await self.repo.edit(AlertUpdate(is_active=False, triggered_at=latest.date), id=alert.id)
                await self.session.commit()

    # === Internal === 
    async def _send_push(self, user_id: int, stock_id: int, price: float) -> bool:
        # Получить player_id
        player_id = await self.onesignal_repo.get_player_id(user_id)
        if not player_id:
            return False

        async with httpx.AsyncClient() as client:
            # Получить subscription_id по player_id
            url = f"https://api.onesignal.com/apps/{settings.PROJECT_ID}/users/by/onesignal_id/{player_id}"
            headers = {"Authorization": f"Bearer {settings.ONESIGNAL_API_KEY}"}
            resp = await client.get(url, headers=headers)

            # print(f"settings.PROJECT_ID {settings.PROJECT_ID}")
            # print(f"resp.text {resp.text}")
            if resp.status_code != 200:
                return False

            subs = resp.json().get("subscriptions") or []
            # ❗ Берём только активный subscription
            sub_id = next((s["id"] for s in subs if s.get("enabled")), None)
            if not sub_id:
                return False

            # Получаем тикер по stock_id
            symbol = await self.stock_repo.get_symbol_by_id(stock_id)
            if not symbol:
                symbol = f"id {stock_id}"

            text_ru = f"Цена актива {symbol} достигла {price}₽"

            # Отправка push
            push_url = "https://api.onesignal.com/notifications?c=push"
            push_headers = {
                "Authorization": f"Bearer {settings.ONESIGNAL_API_KEY}",
                "Content-Type": "application/json",
            }
            body = {
                "app_id": settings.PROJECT_ID,
                "include_subscription_ids": [sub_id],
                "headings": {"ru": "Сработал алерт", "en": "Price Alert"},
                "contents": {"ru": text_ru, "en": text_ru},
                "ttl": 3600  # ⏳ гарантирует доставку, если оффлайн
            }

            result = await client.post(push_url, headers=push_headers, json=body)
            # print(result.status_code, result.text)
            return result.status_code < 400

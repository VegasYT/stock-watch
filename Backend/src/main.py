# ngrok http --url=fit-frequently-sturgeon.ngrok-free.app 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
import uvicorn
from contextlib import asynccontextmanager
from apscheduler.triggers.cron import CronTrigger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.database import engine, Base
from src.core.scheduler import scheduler, sync_tqbr_prices
from src.modules.users.router import router as router_users
from src.modules.auth.router import router as router_auth
from src.modules.stocks.router import router as router_stocks
from src.modules.portfolio.router import router as router_portfolio
from src.modules.stock_prices.router import router as router_prices
from src.modules.notify.router import router as router_alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # >>> Секция старта
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Запускаем APScheduler: каждый час с 6:00 до 23:00 по МСК
    scheduler.add_job(sync_tqbr_prices, CronTrigger(hour="6-23", minute=0, second=10))
    scheduler.start()

    yield

    # >>> Секция остановки (если что-то нужно закрывать при остановке)
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)


security = HTTPBearer()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="StockWatch API",
        version="1.0.0",
        description="API для управления пользователями, акциями и портфелем",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation.setdefault("security", []).append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi


app.include_router(router_auth)
app.include_router(router_users)
app.include_router(router_stocks)
app.include_router(router_portfolio)
app.include_router(router_prices)
app.include_router(router_alerts)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, port=8000)

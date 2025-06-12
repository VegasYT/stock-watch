from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


# Создание асинхронного движка
engine = create_async_engine(
    settings.DB_URL,
    # echo=True,
)

# Создание асинхронной сессии
async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

# Базовый класс для всех моделей
class Base(DeclarativeBase):
    pass

# Зависимость для FastAPI роутеров
async def get_async_session():
    async with async_session_maker() as session:
        yield session

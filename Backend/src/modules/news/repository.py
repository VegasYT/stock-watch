from core.repository import BaseRepository
from .models import News
from .schemas import NewsSchema


class NewsRepository(BaseRepository):
    model = News
    schema = NewsSchema

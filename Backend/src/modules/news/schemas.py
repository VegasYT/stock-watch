from pydantic import BaseModel
from datetime import datetime


class NewsSchema(BaseModel):
    id: int
    title: str
    content: str
    source: str
    published: datetime

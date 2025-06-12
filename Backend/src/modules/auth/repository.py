from datetime import datetime
from sqlalchemy import delete, select

from src.modules.auth.models import RefreshToken


class AuthRepository:
    def __init__(self, session):
        self.session = session

    async def set_refresh_token(self, user_id: int, token: str, expires_at: datetime):
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        refresh = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.session.add(refresh)
        await self.session.commit()

    async def get_refresh_token_by_token(self, token: str):
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalars().first()

    async def delete_refresh_token(self, token_obj):
        await self.session.delete(token_obj)
        await self.session.commit()

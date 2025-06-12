from datetime import datetime
from typing import Optional
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.core.repository import BaseRepository
from src.modules.users.models import OneSignalToken, User as UserModel
from src.modules.users.schemas import User, UserWithHashedPassword


class UserRepository(BaseRepository):
    model = UserModel
    schema = User  # Основная схема без пароля

    async def get_user_with_hashed_password(self, email: EmailStr) -> Optional[UserWithHashedPassword]:
        query = select(self.model).filter_by(email=email)
        result = await self.session.execute(query)

        obj = result.scalars().one_or_none()
        if obj is None:
            return None

        return UserWithHashedPassword.model_validate(obj, from_attributes=True)


class OneSignalTokenRepository(BaseRepository):
    model = OneSignalToken
    schema = None

    async def upsert(self, user_id: int, player_id: str):
        stmt = (
            insert(self.model)
            .values(user_id=user_id, player_id=player_id)
            .on_conflict_do_update(
                index_elements=[self.model.user_id],
                set_={"player_id": player_id, "updated_at": datetime.utcnow()}
            )
        )
        await self.session.execute(stmt)

    async def get_player_id(self, user_id: int) -> str | None:
        query = select(self.model.player_id).where(self.model.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

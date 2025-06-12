from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.users.repository import OneSignalTokenRepository, UserRepository
from src.modules.users.schemas import User, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.onesignal_repo = OneSignalTokenRepository(session)

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.repo.get_one_or_none(id=user_id)
        return user

    async def list_users(self) -> list[User]:
        return await self.repo.get_all()

    async def delete_user(self, user_id: int) -> None:
        await self.repo.delete(id=user_id)

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        await self.repo.edit(user_update, id=user_id, is_patch=True)
        updated_user = await self.get_user_by_id(user_id)
        return updated_user
    
    async def register_onesignal_token(self, user_id: int, player_id: str):
        await self.onesignal_repo.upsert(user_id, player_id)
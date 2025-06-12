from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt

from src.modules.auth.models import RefreshToken
from src.modules.auth.schemas import TokenPair
from src.modules.auth.repository import AuthRepository
from src.core.config import settings
from src.modules.users.repository import UserRepository
from src.modules.users.schemas import (
    UserRequestAdd,
    UserAdd,
    UserWithHashedPassword,
    User,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.auth_repo = AuthRepository(session)

    def _hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)


    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)


    def _create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    

    def _create_refresh_token(self, user_id: int) -> tuple[str, datetime]:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        data = {"user_id": user_id, "exp": expire.timestamp()}
        token = jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, expire


    def _decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, key=settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Срок действия токена истёк")
        except (jwt.DecodeError, jwt.InvalidTokenError):
            raise HTTPException(status_code=401, detail="Невалидный токен")


    async def register_user(self, data: UserRequestAdd) -> User:
        existing = await self.repo.get_one_or_none(email=data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

        try:
            hashed_pwd = self._hash_password(data.password)
            user_in = UserAdd(
                email=data.email,
                nickname=data.nickname,
                hashed_password=hashed_pwd,
            )
            user = await self.repo.add(user_in)
            await self.session.commit()
            return user
        except IntegrityError as e:
            await self.session.rollback()
            # Можно распарсить текст ошибки чтобы отличать email/nickname
            if 'ix_users_nickname' in str(e.orig):
                raise HTTPException(status_code=400, detail="Пользователь с таким ником уже существует")
            if 'ix_users_email' in str(e.orig):
                raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
            raise HTTPException(status_code=400, detail="Ошибка регистрации (дублирование)")


    def decode_token(self, token: str) -> dict:
        return self._decode_token(token)


    async def login_user(self, email: str, password: str) -> TokenPair:
        user = await self.repo.get_user_with_hashed_password(email)
        if not user or not self._verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")

        access_token = self._create_access_token({"user_id": user.id})
        refresh_token, expires_at = self._create_refresh_token(user.id)

        # await self._store_refresh_token(user.id, refresh_token, expires_at)
        await self.auth_repo.set_refresh_token(user.id, refresh_token, expires_at)

        return TokenPair(access_token=access_token, refresh_token=refresh_token)


    async def refresh_tokens(self, token: str) -> TokenPair:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token истёк")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Невалидный refresh token")

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Некорректный payload")

        # existing = await self.session.execute(
        #     select(RefreshToken).where(RefreshToken.token == token)
        # )
        # token_obj = existing.scalars().first()
        token_obj = await self.auth_repo.get_refresh_token_by_token(token)
        if not token_obj:
            raise HTTPException(status_code=401, detail="Токен не найден или отозван")

        # Удалим старый токен
        # await self.session.delete(token_obj)
        await self.auth_repo.delete_refresh_token(token_obj)

        new_access = self._create_access_token({"user_id": user_id})
        new_refresh, new_exp = self._create_refresh_token(user_id)
        # await self._store_refresh_token(user_id, new_refresh, new_exp)
        await self.auth_repo.set_refresh_token(user_id, new_refresh, new_exp)

        return TokenPair(access_token=new_access, refresh_token=new_refresh)
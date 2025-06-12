import re
from pydantic import BaseModel, EmailStr, field_validator


class UserRequestLogin(BaseModel):
    email: EmailStr
    password: str


class UserRequestAdd(BaseModel):
    email: EmailStr
    nickname: str
    password: str

    @field_validator("nickname")
    def validate_nickname(cls, v):
        if len(v) < 3:
            raise ValueError("Ник должен быть не короче 3 символов")
        if len(v) > 16:
            raise ValueError("Ник должен быть не длиннее 16 символов")
        if not re.fullmatch(r"[A-Za-z0-9]+", v):
            raise ValueError("Ник должен содержать только латинские буквы и цифры, без пробелов и спецсимволов")
        return v

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")
        if len(v) > 32:
            raise ValueError("Пароль должен быть не длиннее 32 символов")
        return v


class UserAdd(BaseModel):
    email: EmailStr
    nickname: str
    hashed_password: str


class User(BaseModel):
    id: int
    email: EmailStr
    nickname: str


class UserWithHashedPassword(User):
    hashed_password: str


class UserUpdate(BaseModel):
    nickname: str | None = None


class OneSignalTokenIn(BaseModel):
    player_id: str

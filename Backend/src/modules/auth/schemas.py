from pydantic import BaseModel, EmailStr, field_validator


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    token: str

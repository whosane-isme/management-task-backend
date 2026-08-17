from pydantic import BaseModel, EmailStr, HttpUrl


class GoogleIdentityClaims(BaseModel):
    sub: str
    email: EmailStr
    email_verified: bool
    name: str | None = None
    picture: HttpUrl | None = None
    hd: str | None = None

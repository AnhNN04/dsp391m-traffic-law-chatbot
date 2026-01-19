from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Dữ liệu nhận từ Client khi đăng ký
class UserCreate(BaseModel):
    email: EmailStr
    # FIX: Giới hạn độ dài password từ 6 đến 72 ký tự
    password: str = Field(..., min_length=6, max_length=72)
    full_name: Optional[str] = None

# Dữ liệu nhận từ Client khi đăng nhập
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Dữ liệu trả về cho Client (không bao gồm password)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool

# Dữ liệu trả về khi login thành công
class Token(BaseModel):
    access_token: str
    token_type: str
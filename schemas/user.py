from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from schemas.role import RoleResponse

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role_id: int
    is_active: bool = True

class UserCreate(UserBase):
    password: str  # Plain password, sẽ được hash

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # Plain password nếu muốn đổi

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleResponse] = None
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class UserSearchParams(BaseModel):
    keyword: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 10

# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
    permissions: List[str] = []

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    permissions: List[str] = []

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
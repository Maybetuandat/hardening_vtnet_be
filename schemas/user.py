
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., max_length=50, description="Username for login")
    email: EmailStr = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User last name")
    role: str = Field(default="user", description="User role")
    is_active: bool = Field(default=True, description="User active status")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="User password")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50, description="Username for login")
    email: Optional[EmailStr] = Field(None, description="User email address")
    first_name: Optional[str] = Field(None, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User last name")
    role: Optional[str] = Field(None, description="User role")
    is_active: Optional[bool] = Field(None, description="User active status")
    password: Optional[str] = Field(None, min_length=6, description="User password")

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

class UserSearchParams(BaseModel):
    keyword: Optional[str] = Field(None, description="Search keyword for username or full name")
    role: Optional[str] = Field(None, description="Filter by user role")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")

# Auth schemas
class LoginRequest(BaseModel):
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type (Bearer)")
    user: UserResponse = Field(..., description="User information")

class TokenData(BaseModel):
    username: Optional[str] = Field(None, description="Username from token")
    user_id: Optional[int] = Field(None, description="User ID from token")
    role: Optional[str] = Field(None, description="User role from token")
    permissions: List[str] = Field(default=[], description="User permissions list")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")

class UserResponseFromDcim(BaseModel):
    id : int
    username: str
    first_name : str
    last_name : str
    email: str
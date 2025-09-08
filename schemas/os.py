from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OsBase(BaseModel):
    version: str = Field(..., max_length=255, description="Tên máy chủ")

class OsCreate(OsBase):
    pass
class OsUpdate(OsBase):
    pass
class OsResponse(OsBase):
    id: int = Field(..., description="ID của hệ điều hành")
    create_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")
    class Config:
        from_attributes = True
class OsListResponse(BaseModel):
    os: list[OsResponse]
    total: int = Field(..., description="Tổng số hệ điều hành")
    page: int = Field(..., description="Trang hiện tại")
    page_size: int = Field(..., description="Số mục trên mỗi trang")
    total_pages: int = Field(..., description="Tổng số trang")
class OsSearchParams(BaseModel):
    keyword: Optional[str] = Field(None, max_length=255, description="Tên hệ điều hành để tìm kiếm")
    page: int = Field(1, ge=1, description="Trang hiện tại")
    size: int = Field(10, ge=1, le=100, description="Số mục trên mỗi trang")
    
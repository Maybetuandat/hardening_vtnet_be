from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OsBase(BaseModel):
    name: str = Field(..., max_length=255, description="Operating system name")
    display: str = Field(..., max_length=255, description="Operating system display name")
    type : Optional[int]= Field(None, description="Operating system type")
class OsCreate(OsBase):
    pass

class OsUpdate(OsBase):
    pass

class OsResponse(OsBase):
    id: int = Field(..., description="Operating system ID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Update time")
    
    class Config:
        from_attributes = True

class OsListResponse(BaseModel):
    os: list[OsResponse]
    total: int = Field(..., description="Total number of operating systems")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

class OsSearchParams(BaseModel):
    keyword: Optional[str] = Field(None, max_length=255, description="Operating system name to search")
    page: int = Field(1, ge=1, description="Current page")
    size: int = Field(10, ge=1, le=100, description="Number of items per page")

class OsResponseFromDcim(BaseModel):
    id : int 
    name : str
    display : str
    type : int
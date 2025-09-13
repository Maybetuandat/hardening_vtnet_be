from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[str] = None  

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[str] = None

class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RoleListResponse(BaseModel):
    roles: List[RoleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class RoleSearchParams(BaseModel):
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 10
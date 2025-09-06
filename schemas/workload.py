from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


from schemas.rule import RuleCreate


class WorkLoadBase(BaseModel):
    name : str = Field(..., max_length=100, description="Tên của workload")
    description: Optional[str] = Field(None, description="Mô tả về workload")
    os_id: int = Field(..., description="ID của hệ điều hành")
class WorkLoadCreate(WorkLoadBase):
    pass
class WorkLoadUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Tên của workload")
    description: Optional[str] = Field(None, description="Mô tả về workload")
    os_id: Optional[int] = Field(None, description="ID của hệ điều hành")
class WorkLoadResponse(WorkLoadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    os_version: Optional[str] = Field(None, description="Phiên bản hệ điều hành")
    class Config:
        from_attributes = True
class WorkLoadListResponse(BaseModel):
    workloads: List[WorkLoadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    class Config:
        from_attributes = True  # cho phep map du lieu tu orm sang doi tuong 
class WorkLoadSearchParams(BaseModel):
    keyword: Optional[str] = None
    status: Optional[bool] = None
    workload_id: Optional[int] = None
    page: int = 1
    page_size: int = 10




class WorkloadWithRulesRequest(BaseModel):
    workload: WorkLoadCreate
    rules: List[RuleCreate]
    

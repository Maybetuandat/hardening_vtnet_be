from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


from schemas.rule import RuleCreate


class WorkLoadBase(BaseModel):
    name: str = Field(..., max_length=100, description="Workload name")
    description: Optional[str] = Field(None, description="Workload description")
    os_id: int = Field(..., description="Operating system ID")


class WorkLoadCreate(WorkLoadBase):
    pass


class WorkLoadUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Workload name")
    description: Optional[str] = Field(None, description="Workload description")
    os_id: Optional[int] = Field(None, description="Operating system ID")


class WorkLoadResponse(WorkLoadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    os_name: Optional[str] = Field(None, description="Operating system name")

    class Config:
        from_attributes = True


class WorkLoadListResponse(BaseModel):
    workloads: List[WorkLoadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True  # allows mapping data from ORM to object


class WorkLoadSearchParams(BaseModel):
    keyword: Optional[str] = None
    status: Optional[bool] = None
    workload_id: Optional[int] = None
    page: int = 1
    page_size: int = 10


class WorkloadWithRulesRequest(BaseModel):
    workload: WorkLoadCreate
    rules: List[RuleCreate]
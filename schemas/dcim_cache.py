from typing import Optional
from pydantic import BaseModel


class CacheClearRequest(BaseModel):
    
    instance_id: Optional[int] = None  


class CacheClearResponse(BaseModel):
    
    success: bool = True
    message: str
    deleted_keys: int
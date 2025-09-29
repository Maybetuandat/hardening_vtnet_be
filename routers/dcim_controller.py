from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from schemas.dcim_cache import CacheClearRequest, CacheClearResponse
from schemas.instance import InstanceListRequest, InstanceListResponseFromDcim
from services.dcim_service import DCIMService

router = APIRouter(prefix="/api/dcim", tags=["DCIM"])


def get_dcim_service() -> DCIMService:
    """Dependency để inject DCIMService"""
    return DCIMService()


@router.get("/instances", response_model=InstanceListResponseFromDcim)
def get_instances(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    use_cache: bool = Query(True, description="Use Redis cache"),
    dcim_service: DCIMService = Depends(get_dcim_service)
):
 
    try:
        request = InstanceListRequest(
            page=page,
            page_size=page_size,
            use_cache=use_cache
        )
        
        result = dcim_service.get_instances(request)
        
        if result is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to fetch instances from DCIM"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache", response_model=CacheClearResponse)
def clear_cache(
    instance_id: Optional[int] = Query(None, description="Instance ID to clear cache (None = clear all)"),
    dcim_service: DCIMService = Depends(get_dcim_service)
):
    """
    Xóa cache của DCIM
    
    **Parameters:**
    - **instance_id**: ID của instance cần xóa cache (None = xóa tất cả)
    
    **Examples:**
    - Clear all: `DELETE /api/dcim/cache`
    - Clear specific: `DELETE /api/dcim/cache?instance_id=123`
    """
    try:
        request = CacheClearRequest(instance_id=instance_id)
        result = dcim_service.clear_cache(request)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



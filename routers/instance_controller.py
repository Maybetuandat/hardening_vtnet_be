from http import server
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from config.config_database import get_db

from schemas.instance import InstanceCreate, InstanceListResponse, InstanceResponse, InstanceSearchParams

from services.instance_service import InstanceService
from utils.auth import require_admin, require_user

router = APIRouter(prefix="/api/servers", tags=["Servers"])


def get_instance_service(db: Session = Depends(get_db)) -> InstanceService:
    return InstanceService(db)



@router.get("/", response_model=InstanceListResponse)
def get_instances(
    keyword: Optional[str] = Query(None, description="keyword"),
    workload_id: Optional[int] = Query(None, description="ID workload"),
    status: Optional[bool] = Query(None, description="server search status"),
    page: int = Query(1, ge=1, description="Page"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    instance_service: InstanceService = Depends(get_instance_service),
    current_user = Depends(require_user())
):
    
    try:
        if(current_user.role == 'admin'):
            search_params = InstanceSearchParams(
                keyword=keyword,
                workload_id=workload_id,
                status=status,
                page=page,
                size=page_size
            )
        else:

            search_params = InstanceSearchParams(
                keyword=keyword,
                workload_id=workload_id,
                status=status,
                page=page,
                size=page_size,
                user_id= current_user.id
            )
        return instance_service.search_instances(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}", response_model=InstanceResponse)
def get_instance_by_id(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
    current_user = Depends(require_user())
):
    
    try:
        if current_user.role == 'admin':
            instance = instance_service.get_instance_by_id(instance_id)
        else:
            instance = instance_service.get_instance_by_id_and_user(instance_id, current_user.id)
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        return instance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/assign-workload", status_code=200)
def assign_instances_to_workload(
    workload_id: int,
    instance_ids: List[int],
    instance_service: InstanceService = Depends(get_instance_service),
    current_user = Depends(require_user())  
):
    try:
        result = instance_service.assign_instances_to_workload(
            workload_id=workload_id,
            instance_ids=instance_ids
        )
        
        return {
            "success": True,
            "message": f"Assigned {result['assigned_count']} instances to workload successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error assigning instances: {str(e)}"
        )
@router.delete("/remove-workload", status_code=200)
def remove_instances_from_workload(
    workload_id: int,
    instance_ids: List[int],
    instance_service: InstanceService = Depends(get_instance_service),
    current_user = Depends(require_user())
):
    
    try:
        result = instance_service.remove_workload_from_instances(
            workload_id=workload_id,
            instance_ids=instance_ids
        )
        
        return {
            "success": True,
            "message": f"Removed workload from {result} instances successfully",
            "data": {
                "workload_id": workload_id,
                "removed_count": result
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing workload: {str(e)}"
        )


@router.get("/workload/{workload_id}", response_model=InstanceListResponse)
def get_instances_by_workload(
    workload_id: int,
    page: int = Query(1, ge=1, description="Page"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    instance_service: InstanceService = Depends(get_instance_service),
    current_user = Depends(require_user())
):
    """
    Lấy danh sách instances được gán cho workload
    """
    try:
        search_params = InstanceSearchParams(
            workload_id=workload_id,
            page=page,
            size=page_size
        )
        return instance_service.search_instances(search_params)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching instances: {str(e)}"
        )
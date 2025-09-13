from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from config.config_database import get_db
from services.role_service import RoleService
from services.auth_service import get_current_user_dependency, require_admin
from models.user import User
from schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, 
    RoleListResponse, RoleSearchParams
)

router = APIRouter(prefix="/api/roles", tags=["Roles"])

def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)

@router.get("", response_model=RoleListResponse)
async def search_roles(
    keyword: Optional[str] = Query(None, description="Search keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_user_dependency)
):
    """Search roles with pagination"""
    try:
        search_params = RoleSearchParams(
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        return role_service.search_roles(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=List[RoleResponse])
async def get_all_roles(
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get all roles (no pagination)"""
    try:
        return role_service.get_all_roles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(
    role_id: int,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get role by ID"""
    try:
        role = role_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(require_admin())
):
    """Create new role (admin only)"""
    try:
        return role_service.create_role(role_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(require_admin())
):
    """Update role (admin only)"""
    try:
        updated_role = role_service.update_role(role_id, role_data)
        if not updated_role:
            raise HTTPException(status_code=404, detail="Role not found")
        return updated_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(require_admin())
):
    """Delete role (admin only)"""
    try:
        success = role_service.delete_role(role_id)
        if not success:
            raise HTTPException(status_code=404, detail="Role not found")
        return {"success": True, "message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
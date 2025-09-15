# routers/user_controller.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from config.config_database import get_db
from services.user_service import UserService
from models.user import User
from schemas.user import (
    UserCreate, UserUpdate, UserResponse, 
    UserListResponse, UserSearchParams,
    ChangePasswordRequest
)
from utils.auth import get_current_user_dependency, require_admin, require_user

router = APIRouter(prefix="/api/users", tags=["Users"])

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@router.get("/", response_model=UserListResponse)
async def search_users(
    keyword: Optional[str] = Query(None, description="Search keyword"),
    role: Optional[str] = Query(None, description="Role filter (admin/user)"),
    is_active: Optional[bool] = Query(None, description="Active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin())  # Only admin can read
):
    """Search users with pagination"""
    try:
        search_params = UserSearchParams(
            keyword=keyword,
            role=role,
            is_active=is_active,
            page=page,
            page_size=page_size
        )
        return user_service.search_users(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# me for current user
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_dependency),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user info"""
    try:
        return user_service._convert_to_response(current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# id for admin to get any user
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin())  # Only admin can read
):
    """Get user by ID"""
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin())  # Only admin can create
):
    """Create new user (admin only)"""
    try:
        return user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user_dependency)
):
    """Update user (admin or user themselves)"""
    try:
        # Check permission: admin or user themselves
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=403, 
                detail="No permission to update this user"
            )
        
        # Only admin can change role
        if user_data.role and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admin can change user role"
            )
        
        updated_user = user_service.update_user(user_id, user_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin())  # Only admin can delete
):
    """Delete user (admin only)"""
    try:
        # Don't allow admin to delete themselves
        if current_user.id == user_id:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete yourself"
            )
        
        success = user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user_dependency)
):
    """Change current user password"""
    try:
        success = user_service.change_password(current_user.id, password_data)
        if success:
            return {"success": True, "message": "Password changed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to change password")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
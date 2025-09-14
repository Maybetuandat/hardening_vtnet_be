# routers/auth_controller.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config_database import get_db
from services.auth_service import AuthService
from models.user import User
from schemas.user import LoginRequest, LoginResponse, UserResponse
from utils.auth import get_auth_service, get_current_user_dependency

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login and get JWT token"""
    return auth_service.login(login_data)

@router.post("/refresh-token")
async def refresh_token(
    current_user: User = Depends(get_current_user_dependency),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh JWT token"""
    try:
        new_token = auth_service.refresh_token(current_user)
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "message": "Token refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_dependency)
):
    """Get current user info from token"""
    from services.user_service import UserService
    # Temporarily create UserService for convert
    user_service = UserService(None)  # db will not be used in convert
    return user_service._convert_to_response(current_user)
@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user_dependency)
):
    """Logout (client should delete token)"""
    return {
        "success": True,
        "message": "Logged out successfully. Please delete token on client side."
    }
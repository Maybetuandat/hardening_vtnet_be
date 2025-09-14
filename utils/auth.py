# utils/auth.py
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config.config_database import get_db
from services.auth_service import AuthService
from models.user import User

security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get AuthService instance"""
    return AuthService(db)

def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current user"""
    auth_service = AuthService(db)
    return auth_service.get_current_user(credentials)

def get_current_active_user(
    current_user: User = Depends(get_current_user_dependency)
) -> User:
    """FastAPI dependency to get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled"
        )
    return current_user

def require_admin() -> Callable:
    """Decorator to require admin role"""
    def admin_checker(
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db)
    ) -> User:
        auth_service = AuthService(db)
        if not auth_service.is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    
    return admin_checker

def require_user() -> Callable:
    
    def user_checker(
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db)
    ) -> User:
        auth_service = AuthService(db)
        if not auth_service.is_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User access required"
            )
        return current_user
    
    return user_checker
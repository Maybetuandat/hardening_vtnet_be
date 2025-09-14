# utils/auth.py
from typing import Callable, Optional # Import Optional
from fastapi import Depends, HTTPException, status, Query # Import Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config.config_database import get_db
from services.auth_service import AuthService
from models.user import User

security = HTTPBearer(auto_error=False) # Đặt auto_error=False để chúng ta có thể xử lý lỗi thủ công

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get AuthService instance"""
    return AuthService(db)

def get_current_user_dependency(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), # Có thể không có credentials từ header
    token_from_query: Optional[str] = Query(None, alias="token", description="JWT token from query parameter"), # Thêm query parameter token
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current user.
    Prioritizes Authorization header, then falls back to 'token' query parameter.
    """
    auth_service = AuthService(db)
    
    # Ưu tiên token từ Authorization header
    if credentials:
        print("Debug: Authenticating from Authorization Header.")
        return auth_service.get_current_user(credentials)
    
    # Nếu không có từ header, thử từ query parameter
    if token_from_query:
        print("Debug: Authenticating from Query Parameter 'token'.")
        # Tạo một đối tượng HTTPAuthorizationCredentials giả lập
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_from_query)
        return auth_service.get_current_user(mock_credentials)
    
    # Nếu không có token từ cả hai nguồn
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated: Missing JWT token",
        headers={"WWW-Authenticate": "Bearer"},
    )

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
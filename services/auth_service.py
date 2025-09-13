# services/auth_service.py
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.user_service import UserService
from services.role_service import RoleService
from schemas.user import LoginRequest, LoginResponse, TokenData
from models.user import User

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # Nên đặt trong environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.role_service = RoleService(db)
    
    def login(self, login_data: LoginRequest) -> LoginResponse:
        """Login user và return JWT token"""
        try:
            # Authenticate user
            user = self.user_service.authenticate_user(login_data.username, login_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Username hoặc password không đúng",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get user permissions
            permissions = self.role_service.get_role_permissions(user.role_id)
            
            # Create access token
            access_token = self._create_access_token(
                data={
                    "sub": user.username,
                    "user_id": user.id,
                    "role": user.role.name if user.role else None,
                    "permissions": permissions
                }
            )
            
            # Convert user to response
            user_response = self.user_service._convert_to_response(user)
            
            return LoginResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
                permissions=permissions
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đăng nhập: {str(e)}"
            )
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> User:
        """Verify JWT token và return current user"""
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token không hợp lệ",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            token_data = TokenData(
                username=username,
                user_id=user_id,
                role=payload.get("role"),
                permissions=payload.get("permissions", [])
            )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = self.user_service.dao.get_by_username(token_data.username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User không tồn tại",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User đã bị vô hiệu hóa",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    def check_permission(self, user: User, required_permission: str) -> bool:
        """Kiểm tra user có permission cần thiết không"""
        if not user.role:
            return False
        
        permissions = self.role_service.get_role_permissions(user.role_id)
        return required_permission in permissions
    
    def check_permissions(self, user: User, required_permissions: List[str]) -> bool:
        """Kiểm tra user có tất cả permissions cần thiết không"""
        if not user.role:
            return False
        
        user_permissions = self.role_service.get_role_permissions(user.role_id)
        return all(perm in user_permissions for perm in required_permissions)
    
    def check_role(self, user: User, required_role: str) -> bool:
        """Kiểm tra user có role cần thiết không"""
        if not user.role:
            return False
        
        return user.role.name == required_role
    
    def is_admin(self, user: User) -> bool:
        """Kiểm tra user có phải admin không"""
        return self.check_role(user, "admin")
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Tạo JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def refresh_token(self, user: User) -> str:
        """Refresh JWT token cho user"""
        permissions = self.role_service.get_role_permissions(user.role_id)
        
        return self._create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role.name if user.role else None,
                "permissions": permissions
            }
        )


# Dependency functions for FastAPI
from config.config_database import get_db

def get_auth_service(db: Session) -> AuthService:
    return AuthService(db)

def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency để lấy current user"""
    auth_service = AuthService(db)
    return auth_service.get_current_user(credentials)

def get_current_active_user(
    current_user: User = Depends(get_current_user_dependency)
) -> User:
    """FastAPI dependency để lấy current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User đã bị vô hiệu hóa"
        )
    return current_user

def require_permission(permission: str):
    """Decorator để yêu cầu permission cụ thể"""
    def permission_checker(
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db)
    ):
        auth_service = AuthService(db)
        if not auth_service.check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Không có quyền '{permission}'"
            )
        return current_user
    
    return permission_checker

def require_role(role: str):
    """Decorator để yêu cầu role cụ thể"""
    def role_checker(
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db)
    ):
        auth_service = AuthService(db)
        if not auth_service.check_role(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần role '{role}'"
            )
        return current_user
    
    return role_checker

def require_admin():
    """Decorator để yêu cầu admin role"""
    return require_role("admin")
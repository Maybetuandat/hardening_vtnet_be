# services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from config.setting_jwt import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from services.user_service import UserService
from models.user import User
from schemas.user import LoginRequest, LoginResponse

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
    
    def login(self, login_data: LoginRequest) -> LoginResponse:
        """Login and create JWT token"""
        # Authenticate user
        user = self.user_service.authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
      
        
        # Create access token (options: expired time can be customized :  minutes)
        access_token = self._create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role
            }
        )
        
        # Convert user to response
        user_response = self.user_service._convert_to_response(user)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        # Get user from database
        user_model = self.user_service.dao.get_by_username(username)
        if not user_model or not user_model.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_model
    
    def is_admin(self, user: User) -> bool:
        
        return user.role == "admin"
    
    def is_user(self, user: User) -> bool:
        
        return user.role in ["user", "admin"]  
    
    def refresh_token(self, user: User) -> str:
        return self._create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role
            }
        )
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    
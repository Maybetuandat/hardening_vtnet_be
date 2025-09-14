
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import math
from passlib.context import CryptContext

from dao.user_dao import UserDAO
from models.user import User
from schemas.user import (
    UserCreate, UserUpdate, UserResponse, 
    UserListResponse, UserSearchParams,
    ChangePasswordRequest
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.dao = UserDAO(db)
    
    def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        if user_id <= 0:
            return None
        
        user = self.dao.get_by_id(user_id)
        if user:
            return self._convert_to_response(user)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        user = self.dao.get_by_username(username)
        if user:
            return self._convert_to_response(user)
        return None
    
    def search_users(self, search_params: UserSearchParams) -> UserListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        
        skip = (page - 1) * page_size
        
        users, total = self.dao.search_users(
            keyword=search_params.keyword,
            role=search_params.role,
            is_active=search_params.is_active,
            skip=skip,
            limit=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        user_responses = [self._convert_to_response(user) for user in users]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        try:
            self._validate_user_create_data(user_data)
            
            # Check if username exists
            if self.dao.check_username_exists(user_data.username):
                raise ValueError(f"Username '{user_data.username}' already exists")
            
            # Check if email exists
            if self.dao.check_email_exists(user_data.email):
                raise ValueError(f"Email '{user_data.email}' already exists")
            
            # Hash password
            hashed_password = self._hash_password(user_data.password)
            
            user_dict = user_data.dict(exclude={'password'})
            user_dict['password_hash'] = hashed_password
            
            user_model = User(**user_dict)
            
            created_user = self.dao.create(user_model)
            self.db.commit()
            
            return self._convert_to_response(created_user)
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[UserResponse]:
        try:
            if user_id <= 0:
                return None
            
            existing_user = self.dao.get_by_id(user_id)
            if not existing_user:
                return None
            
            # Check username uniqueness
            if user_data.username and self.dao.check_username_exists(user_data.username, exclude_id=user_id):
                raise ValueError(f"Username '{user_data.username}' already exists")
            
            # Check email uniqueness
            if user_data.email and self.dao.check_email_exists(user_data.email, exclude_id=user_id):
                raise ValueError(f"Email '{user_data.email}' already exists")
            
            # Update fields
            update_dict = user_data.dict(exclude_unset=True, exclude={'password'})
            
            for field, value in update_dict.items():
                setattr(existing_user, field, value)
            
            # Update password if provided
            if user_data.password:
                existing_user.password_hash = self._hash_password(user_data.password)
            
            updated_user = self.dao.update(existing_user)
            self.db.commit()
            
            return self._convert_to_response(updated_user)
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def delete_user(self, user_id: int) -> bool:
        try:
            if user_id <= 0:
                return False
            
            success = self.dao.delete(user_id)
            if success:
                self.db.commit()
            
            return success
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def change_password(self, user_id: int, password_data: ChangePasswordRequest) -> bool:
        try:
            user = self.dao.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Verify current password
            if not self._verify_password(password_data.current_password, user.password_hash):
                raise ValueError("Current password is incorrect")

            # Update password
            user.password_hash = self._hash_password(password_data.new_password)
            self.dao.update(user)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.dao.get_by_username(username)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        return user
    
    def _validate_user_create_data(self, user_data: UserCreate):
        if not user_data.username or not user_data.username.strip():
            raise ValueError("Username cannot be empty")
        
        if not user_data.email or not user_data.email.strip():
            raise ValueError("Email cannot be empty")
        
        if not user_data.password or len(user_data.password) < 6:
            raise ValueError("Password must be at least 6 characters")
        
        if len(user_data.username.strip()) > 50:
            raise ValueError("Username cannot exceed 50 characters")
        
        if user_data.role and user_data.role not in ["admin", "user"]:
            raise ValueError("Role must be 'admin' or 'user'")
    
    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def _convert_to_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
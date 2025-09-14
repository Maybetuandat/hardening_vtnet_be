
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import Optional, List, Tuple
from models.user import User

class UserDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def search_users(
        self,
        keyword: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[User], int]:
        query = self.db.query(User)
        
        filters = []
        
        if keyword:
            search_filter = or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
                User.full_name.ilike(f"%{keyword}%")
            )
            filters.append(search_filter)
        
        if role:
            filters.append(User.role == role)
        
        if is_active is not None:
            filters.append(User.is_active == is_active)
        
        if filters:
            query = query.filter(and_(*filters))
        
        total = query.count()
        users = query.order_by(User.created_at).offset(skip).limit(limit).all()
        
        return users, total
    
    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
    
    def update(self, user: User) -> User:
        user.updated_at = func.now()
        self.db.flush()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.flush()
            return True
        return False
    
    def check_username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(User).filter(User.username == username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
    
    def check_email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(User).filter(User.email == email)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
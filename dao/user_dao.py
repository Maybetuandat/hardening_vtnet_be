from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import Optional, List, Tuple
from models.user import User
from models.role import Role

class UserDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(User.email == email).first()
    
    def get_all_with_role(self) -> List[User]:
        return self.db.query(User).options(joinedload(User.role)).order_by(User.username).all()
    
    def search_users(
        self,
        keyword: Optional[str] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[User], int]:
        query = self.db.query(User).options(joinedload(User.role))
        
        filters = []
        
        if keyword:
            search_filter = or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
                User.full_name.ilike(f"%{keyword}%")
            )
            filters.append(search_filter)
        
        if role_id is not None:
            filters.append(User.role_id == role_id)
        
        if is_active is not None:
            filters.append(User.is_active == is_active)
        
        if filters:
            query = query.filter(and_(*filters))
        
        total = query.count()
        users = query.order_by(User.username).offset(skip).limit(limit).all()
        
        return users, total
    
    def get_active_users(self, skip: int = 0, limit: int = 10) -> Tuple[List[User], int]:
        query = self.db.query(User).options(joinedload(User.role)).filter(User.is_active == True)
        total = query.count()
        users = query.order_by(User.username).offset(skip).limit(limit).all()
        return users, total
    
    def get_users_by_role(self, role_id: int) -> List[User]:
        return self.db.query(User).options(joinedload(User.role)).filter(
            and_(User.role_id == role_id, User.is_active == True)
        ).order_by(User.username).all()
    
    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
    
    def update(self, user: User) -> User:
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
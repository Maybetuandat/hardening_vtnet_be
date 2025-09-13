from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Tuple
from models.role import Role

class RoleDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name).first()
    
    def get_all(self) -> List[Role]:
        return self.db.query(Role).order_by(Role.name).all()
    
    def search_roles(self, keyword: Optional[str] = None, skip: int = 0, limit: int = 10) -> Tuple[List[Role], int]:
        query = self.db.query(Role)
        
        if keyword:
            search_filter = or_(
                Role.name.ilike(f"%{keyword}%"),
                Role.description.ilike(f"%{keyword}%")
            )
            query = query.filter(search_filter)
        
        total = query.count()
        roles = query.order_by(Role.name).offset(skip).limit(limit).all()
        
        return roles, total
    
    def create(self, role: Role) -> Role:
        self.db.add(role)
        self.db.flush()
        self.db.refresh(role)
        return role
    
    def update(self, role: Role) -> Role:
        self.db.flush()
        self.db.refresh(role)
        return role
    
    def delete(self, role_id: int) -> bool:
        role = self.get_by_id(role_id)
        if role:
            self.db.delete(role)
            self.db.flush()
            return True
        return False
    
    def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Role).filter(Role.name == name)
        if exclude_id:
            query = query.filter(Role.id != exclude_id)
        return query.first() is not None
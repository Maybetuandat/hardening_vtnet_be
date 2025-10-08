# dao/fix_request_dao.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.fix_request import FixRequest


class FixRequestDAO:
    """Data Access Object cho FixRequest"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, fix_request: FixRequest) -> FixRequest:
        """Tạo fix request mới"""
        self.db.add(fix_request)
        self.db.commit()
        self.db.refresh(fix_request)
        return fix_request
    
    def get_by_id(self, request_id: int) -> Optional[FixRequest]:
        """Lấy fix request theo ID"""
        return self.db.query(FixRequest).filter(FixRequest.id == request_id).first()
    
    def get_all(self, status: Optional[str] = None) -> List[FixRequest]:
        """Lấy tất cả fix requests, có thể filter theo status"""
        query = self.db.query(FixRequest)
        
        if status:
            query = query.filter(FixRequest.status == status)
        
        return query.order_by(desc(FixRequest.created_at)).all()
    
    def get_by_user(self, username: str, status: Optional[str] = None) -> List[FixRequest]:
        """Lấy fix requests của user"""
        query = self.db.query(FixRequest).filter(FixRequest.created_by == username)
        
        if status:
            query = query.filter(FixRequest.status == status)
        
        return query.order_by(desc(FixRequest.created_at)).all()
    
    def get_by_instance(self, instance_id: int, status: Optional[str] = None) -> List[FixRequest]:
        """Lấy fix requests của instance"""
        query = self.db.query(FixRequest).filter(FixRequest.instance_id == instance_id)
        
        if status:
            query = query.filter(FixRequest.status == status)
        
        return query.order_by(desc(FixRequest.created_at)).all()
    
    def get_by_rule_result(self, rule_result_id: int) -> List[FixRequest]:
        """Lấy fix requests của rule result"""
        return self.db.query(FixRequest).filter(
            FixRequest.rule_result_id == rule_result_id
        ).order_by(desc(FixRequest.created_at)).all()
    
    def has_pending_request_for_rule_result(self, rule_result_id: int) -> bool:
        """Kiểm tra xem rule result đã có pending request chưa"""
        return self.db.query(FixRequest).filter(
            FixRequest.rule_result_id == rule_result_id,
            FixRequest.status == "pending"
        ).first() is not None
    
    def update(self, fix_request: FixRequest) -> FixRequest:
        """Cập nhật fix request"""
        self.db.commit()
        self.db.refresh(fix_request)
        return fix_request
    
    def delete(self, fix_request: FixRequest) -> bool:
        """Xóa fix request"""
        try:
            self.db.delete(fix_request)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
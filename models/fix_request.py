from sqlalchemy import Column, Integer, String, DateTime, Text, JSON

from datetime import datetime

from config.config_database import Base



class FixRequest(Base):
    __tablename__ = "fix_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_result_id = Column(Integer, nullable=False, index=True)
    instance_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="pending")  # pending, approved, rejected, executing, completed, failed
    
    # Người tạo request
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Admin xác nhận
    admin_id = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    admin_comment = Column(Text, nullable=True)
    
    # Thực thi
    executed_at = Column(DateTime, nullable=True)
    execution_result = Column(JSON, nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    
    
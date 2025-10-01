

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.config_database import Base


class RuleChangeRequest(Base):
    __tablename__ = "rule_change_requests"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workload_id = Column(Integer, ForeignKey("workloads.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=True) 
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    request_type = Column(String(20), nullable=False) 
    old_value = Column(JSON, nullable=True) 
    new_value = Column(JSON, nullable=False) 
    status = Column(String(20), default='pending', nullable=False)  
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workload = relationship("Workload", backref="change_requests")
    rule = relationship("Rule", backref="change_requests")
    requester = relationship("User", foreign_keys=[user_id], backref="requested_changes")
    admin = relationship("User", foreign_keys=[admin_id], backref="processed_changes")
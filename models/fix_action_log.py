# models/fix_action_log.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from config.config_database import Base

class FixActionLog(Base):
    __tablename__ = "fix_action_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    rule_result_id = Column(Integer, nullable=False)
    compliance_result_id = Column(Integer, nullable=False)
    rule_name = Column(String(500), nullable=True)
    old_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    command = Column(Text, nullable=True)
    execution_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    is_success = Column(Boolean, default=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<FixActionLog(id={self.id}, user={self.username}, rule_result_id={self.rule_result_id})>"
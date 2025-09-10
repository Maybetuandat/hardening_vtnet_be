from email import message
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, func, ForeignKey
from config.config_database import Base
from sqlalchemy.orm import relationship


class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    compliance_result_id = Column(Integer, ForeignKey("compliance_results.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False)
    status = Column(String(20), nullable=False)  
    # mô tả trạng thái của rule ( ví dụ khi hai output không khớp thì ghi là paramter mismatch)
    message = Column(Text, nullable=True)

    # chi tiết lỗi
    details_error = Column(Text, nullable=True)  
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    output = Column(JSON, nullable=True)  
    # Relationships
    compliance_result = relationship("ComplianceResult", back_populates="rule_results")
    rule = relationship("Rule", back_populates="rule_results")
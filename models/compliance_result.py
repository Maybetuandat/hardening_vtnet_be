from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, func, ForeignKey
from config.config_database import Base
from sqlalchemy.orm import relationship


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    name=Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="pending") 
    total_rules = Column(Integer, default=0)
    passed_rules = Column(Integer, default=0)
    failed_rules = Column(Integer, default=0)
    
    score = Column(Numeric(5, 2), default=0.00) 

    scan_date = Column(DateTime, default=func.now(), nullable=False)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    detail_error = Column(Text, nullable=True)
    # # Relationships
    instance = relationship("Instance", back_populates="compliance_results")

    rule_results = relationship("RuleResult", back_populates="compliance_result", cascade="all, delete-orphan")
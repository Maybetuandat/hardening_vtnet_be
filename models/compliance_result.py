from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func, ForeignKey
from config.config_database import Base
from sqlalchemy.orm import relationship


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    
    status = Column(String(20), nullable=False, default="pending") 
    total_rules = Column(Integer, default=0)
    passed_rules = Column(Integer, default=0)
    failed_rules = Column(Integer, default=0)
    score = Column(Integer, default=0)  # Percentage score
    scan_date = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    detail_error = Column(Text, nullable=True)
    # # Relationships
    server = relationship("Server", back_populates="compliance_results")
    
    rule_results = relationship("RuleResult", back_populates="compliance_result", cascade="all, delete-orphan")
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func, ForeignKey, JSON
from config.config_database import Base
from sqlalchemy.orm import relationship


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    security_standard_id = Column(Integer, ForeignKey("security_standards.id"), nullable=False)
    
    # Simple JSON parameter storage - can handle any parameter structure
    parameters = Column(JSON, nullable=True)  # Store all parameters as simple JSON
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    security_standard = relationship("SecurityStandard", back_populates="rules")
    rule_results = relationship("RuleResult", back_populates="rule")
    commands = relationship("Command", back_populates="rule")

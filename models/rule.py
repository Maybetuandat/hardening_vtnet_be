from click import command
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func, ForeignKey, JSON
from config.config_database import Base
from sqlalchemy.orm import relationship


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    workload_id = Column(Integer, ForeignKey("work_loads.id"), nullable=False)

    command=Column(Text, nullable=False)
    
    parameters = Column(JSON, nullable=True)  
    
    is_active = Column(String(100), nullable=False, default="active")
    created_at = Column(DateTime, default=func.now(), nullable=False) 
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    workload = relationship("WorkLoad", back_populates="rules")
    
    rule_results = relationship("RuleResult", back_populates="rule", cascade="all, delete-orphan")

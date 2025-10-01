from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func 
from config.config_database import Base
from sqlalchemy.orm import relationship


class WorkLoad(Base):  
    __tablename__ = "workloads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    os_id = Column(Integer, ForeignKey("os.id"), nullable=False, index=True)
    
    # Relationships
    os = relationship("Os", back_populates="workloads")
    rules = relationship("Rule", back_populates="workload", cascade="all, delete-orphan")
    instances = relationship("Instance", back_populates="workload")
    
    
    rule_change_requests = relationship(
        "RuleChangeRequest", 
        back_populates="workload", 
        cascade="all, delete-orphan",
        foreign_keys="[RuleChangeRequest.workload_id]"
    )
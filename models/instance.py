from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from config.config_database import Base


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, index=True)
    os_id = Column(Integer, ForeignKey("os.id"), nullable=False, index=True)
    name = Column(String(45), nullable=False, unique=True, index=True)   # ip address
    workload_id = Column(Integer, ForeignKey("work_loads.id"), nullable=True, index=True)
    instance_role = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Boolean, index=True, default=True, nullable=False) 
    ssh_port = Column(Integer, default=2222, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    
    
    #orm relationship
    workload = relationship("WorkLoad", back_populates="instances")
    compliance_results = relationship("ComplianceResult", back_populates="instance", cascade="all, delete-orphan")
    user = relationship("User", back_populates="instances")
    os = relationship("Os", back_populates="instances")
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from config.config_database import Base


class Server(Base):
    __tablename__ = "servers"

    # Core identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
   
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False, unique=True, index=True) 
    
    # # Workload relationship
    workload_id = Column(Integer, ForeignKey("work_loads.id"), nullable=False, index=True)
 
  
    os_version = Column(String(50), nullable=True)
    
   
    # Status
    status = Column(Boolean, index=True, default=True, nullable=False) 
    # SSH
    ssh_port = Column(Integer, default=22)
    ssh_user = Column(String(50), nullable=True)
    ssh_password = Column(String(255), nullable=True)

    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # # Relationships
    workload = relationship("WorkLoad", back_populates="servers")
   
    # compliance_results = relationship("ComplianceResult", back_populates="server")
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from config.config_database import Base


class Server(Base):
    __tablename__ = "servers"

    # Core identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    
    # Workload relationship
    workload_id = Column(Integer, ForeignKey("work_loads.id"), nullable=False, index=True)
 
  
    os_version = Column(String(50), nullable=True)
    
    # Hardware
    cpu_cores = Column(Integer, nullable=True)
    memory_gb = Column(Float, nullable=True)
    
   
    # Status
    status = Column(String(50), nullable=False, index=True)  # Fixed: nullable=False
    # SSH
    ssh_port = Column(Integer, default=22)
    ssh_user = Column(String(50), nullable=True)
    ssh_password = Column(String(255), nullable=True)

    # Audit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    workload = relationship("Workload", back_populates="servers")
   
    compliance_results = relationship("ComplianceResult", back_populates="server")
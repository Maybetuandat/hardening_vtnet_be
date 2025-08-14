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
    server_role = Column(String(50), nullable=True)
    
    # Operating System
    os_type = Column(String(50), nullable=False, index=True)
    os_name = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    
    # Hardware
    cpu_cores = Column(Integer, nullable=True)
    memory_gb = Column(Float, nullable=True)
    
    # Environment
    environment = Column(String(50), nullable=False, index=True)   # "production", "staging", "development"
    
    # Status
    status = Column(String(50), nullable=False, index=True)  # Fixed: nullable=False
    compliance_score = Column(Float, nullable=True)
    
    # SSH
    ssh_port = Column(Integer, default=22)
    ssh_key_id = Column(Integer, ForeignKey("ssh_keys.id"), nullable=True)
    
    # Audit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    workload = relationship("Workload", back_populates="servers")
    ssh_key = relationship("SshKey", back_populates="servers")
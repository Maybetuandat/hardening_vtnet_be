from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from config.config_database import Base


class Server(Base):
    __tablename__ = "servers"

   
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(45), nullable=False, unique=True, index=True) 
    workload_id = Column(Integer, ForeignKey("work_loads.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Boolean, index=True, default=True, nullable=False) 
    ssh_port = Column(Integer, default=22, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    workload = relationship("WorkLoad", back_populates="servers")
    compliance_results = relationship("ComplianceResult", back_populates="server", cascade="all, delete-orphan")
    user = relationship("User", back_populates="servers")
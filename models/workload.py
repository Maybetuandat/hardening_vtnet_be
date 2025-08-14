from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func 
from config.config_database import Base

from sqlalchemy.orm import relationship




class Workload(Base):
    __tablename__ = "work_loads"

   
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    workload_type = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    servers = relationship("Server", back_populates="workload")
    
  
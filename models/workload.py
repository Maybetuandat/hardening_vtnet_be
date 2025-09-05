from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func 
from config.config_database import Base

from sqlalchemy.orm import relationship




class WorkLoad(Base):
    __tablename__ = "work_loads"

   
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    servers = relationship("Server", back_populates="workload", cascade="all, delete-orphan")

    os_version = Column(String(50), nullable=False)
    rules = relationship("Rule", back_populates="workload", cascade="all, delete-orphan")

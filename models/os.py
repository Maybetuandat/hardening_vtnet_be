from venv import create
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func
from config.config_database import Base
from sqlalchemy.orm import relationship
class Os(Base):
    __tablename__ = "os"

    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False)
    display = Column(String(50), nullable=False)

    #orm relationship
    instances = relationship("Instance", back_populates="os")
    workloads = relationship("WorkLoad", back_populates="os")
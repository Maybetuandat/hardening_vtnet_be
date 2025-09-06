from venv import create
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func
from config.config_database import Base
from sqlalchemy.orm import relationship
class Os(Base):
    __tablename__ = "os"

    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(String(100), nullable=False, unique=True, index=True)
    create_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    workload = relationship("WorkLoad", back_populates="os", uselist=False)
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from config.config_database import Base
from sqlalchemy.orm import relationship


class SecurityStandard(Base):
    __tablename__ = "security_standards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    rules = relationship("Rule", back_populates="security_standard")
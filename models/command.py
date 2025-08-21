from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func, ForeignKey, JSON
from config.config_database import Base
from sqlalchemy.orm import relationship


class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False)
    os_version = Column(String(20), nullable=False, index=True, unique=True) 
    command_text = Column(Text, nullable=False)  # Ansible command or shell command
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    rule = relationship("Rule", back_populates="commands")

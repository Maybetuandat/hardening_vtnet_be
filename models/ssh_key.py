from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum

from config.config_database import Base




class SshKeyType(str, Enum):
    RSA = "rsa"
    ED25519 = "ed25519"
    ECDSA = "ecdsa"
    DSA = "dsa"

class SshKey(Base):
    __tablename__ = "ssh_keys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    key_type = Column(SQLEnum(SshKeyType), nullable=False)
    public_key = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)
    fingerprint = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


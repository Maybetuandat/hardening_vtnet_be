from sqlalchemy import DateTime, Table, Column, Integer, ForeignKey, func
from config.config_database import Base
from sqlalchemy.orm import relationship
class OsWorkload(Base):
    __tablename__ = "os_workload"

    workload_id = Column(Integer, ForeignKey("work_loads.id"), primary_key=True)
    os_id = Column(Integer, ForeignKey("os.id"), primary_key=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    workload = relationship("WorkLoad", back_populates="workload_os_links")
    os = relationship("Os", back_populates="workload_os_links")
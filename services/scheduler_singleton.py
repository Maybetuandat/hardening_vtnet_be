from typing import Optional
from sqlalchemy.orm import Session
from services.scheduler_service import SchedulerService


class SchedulerSingleton:
    _instance: Optional[SchedulerService] = None
    _initialized: bool = False
    
    @classmethod
    def get_instance(cls, db: Session = None) -> SchedulerService:
        """Lấy instance duy nhất của SchedulerService"""
        if cls._instance is None and db is not None:
            cls._instance = SchedulerService(db)
            cls._initialized = True
        
        if cls._instance is None:
            raise ValueError("SchedulerSingleton not initialized. Call get_instance(db) first.")
        
        # Update DB session nếu có - FIX: Dùng đúng attribute name
        if db is not None:
            cls._instance.db = db
            # SchedulerService có settings_dao, không phải dao
            from dao.setting_dao import SettingsDAO
            cls._instance.settings_dao = SettingsDAO(db)
        
        return cls._instance
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Kiểm tra đã khởi tạo chưa"""
        return cls._initialized
    
    @classmethod
    def start_scheduler(cls, db: Session):
        """Khởi tạo và start scheduler"""
        if not cls._initialized:
            instance = cls.get_instance(db)
            instance.start_scheduler()
            print("🕐 Singleton Scheduler started successfully!")
            return instance
        else:
            print("⚠️ Scheduler already initialized")
            return cls._instance
    
    @classmethod
    def stop_scheduler(cls):
        """Dừng scheduler"""
        if cls._instance:
            cls._instance.stop_scheduler()
            print("🛑 Singleton Scheduler stopped")
    
    @classmethod
    def reset(cls):
        """Reset instance (for testing)"""
        if cls._instance:
            cls._instance.stop_scheduler()
        cls._instance = None
        cls._initialized = False
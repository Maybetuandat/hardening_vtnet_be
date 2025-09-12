from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from models.setting import Settings



class SettingsDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, key: str) -> Optional[Settings]:
        return self.db.query(Settings).filter(Settings.key == key).first()

    def create_or_update(self, key: str, value: str, description: Optional[str] = None) -> Settings:
        setting = self.get_by_key(key)
        setting.updated_at = datetime.now()
        if setting:
            setting.value = value
            if description is not None:
                setting.description = description
        else:
            setting = Settings(
                key=key,
                value=value,
                description=description
            )
            self.db.add(setting)
        
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def update_value(self, key: str, value: str) -> Optional[Settings]:
        setting = self.get_by_key(key)
        setting.updated_at = datetime.now()
        if setting:
            setting.value = value
            self.db.commit()
            self.db.refresh(setting)
            return setting
        return None

    def get_scan_time(self) -> Optional[str]:
        setting = self.get_by_key("scan_schedule_time")
        return setting.value if setting else None

    def get_scan_enabled(self) -> bool:
        setting = self.get_by_key("scan_schedule_enabled")
        return setting.value.lower() == "true" if setting else False

    def set_scan_schedule(self, scan_time: str, is_enabled: bool) -> dict:
        
        
        self.create_or_update(
            key="scan_schedule_time",
            value=scan_time,
            description="Thời gian chạy scan tự động hàng ngày (HH:MM)"
        )
        
        
        self.create_or_update(
            key="scan_schedule_enabled", 
            value=str(is_enabled).lower(),
            description="Bật/tắt lịch scan tự động"
        )
        
        return {
            "scan_time": scan_time,
            "is_enabled": is_enabled
        }

    def get_scan_schedule(self) -> dict:
        
        scan_time = self.get_scan_time() or "00:00"
        is_enabled = self.get_scan_enabled()
        
        return {
            "scan_time": scan_time,
            "is_enabled": is_enabled
        }
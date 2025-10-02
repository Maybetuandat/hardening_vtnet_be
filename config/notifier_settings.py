

import logging
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class NotifierSettings(BaseSettings):
    """
    External Notifier Configuration
    
    Automatically loads from environment variables with EXTERNAL_NOTIFIER_ prefix
    """
    external_notifier_enabled: bool = Field(
        default=False,
        description="Enable/disable external notifications"
    )
    external_notifier_api_url: str = Field(
        default="",
        description="External chat API endpoint URL"
    )
    external_notifier_auth_token: str = Field(
        default="",
        description="Bearer token for API authentication"
    )
    external_notifier_channel_id: str = Field(
        default="",
        description="Target channel ID for notifications"
    )
    external_notifier_buffer_interval: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Buffer flush interval in seconds (5-300)"
    )
    
    class Config:
        env_file = ".env"
        extra = "allow"
        case_sensitive = False
    
    def is_valid(self) -> bool:
        """
        Validate configuration
        
        Returns:
            bool: True if all required fields are properly set
        """
        if not self.external_notifier_enabled:
            return False
        
        # Check required fields are non-empty
        required_fields = [
            self.external_notifier_api_url,
            self.external_notifier_auth_token,
            self.external_notifier_channel_id
        ]
        
        return all(field and field.strip() for field in required_fields)
    
    def __repr__(self) -> str:
        """Safe string representation (hides sensitive data)"""
        return (
            f"NotifierSettings("
            f"enabled={self.external_notifier_enabled}, "
            f"api_url={self.external_notifier_api_url or 'NOT_SET'}, "
            f"auth_token={'***' if self.external_notifier_auth_token else 'NOT_SET'}, "
            f"channel_id={self.external_notifier_channel_id or 'NOT_SET'}, "
            f"buffer_interval={self.external_notifier_buffer_interval}s"
            f")"
        )


# Singleton instance
_notifier_settings: NotifierSettings = None


def get_notifier_settings() -> NotifierSettings:
    """
    Get singleton instance of NotifierSettings
    
    Returns:
        NotifierSettings: Configuration loaded from .env
    """
    global _notifier_settings
    
    if _notifier_settings is None:
        _notifier_settings = NotifierSettings()
        
        # Log configuration status
        if _notifier_settings.is_valid():
            logger.info(f"✅ External notifier settings loaded: {_notifier_settings}")
        elif _notifier_settings.external_notifier_enabled:
            logger.warning(
                f"⚠️ External notifier is ENABLED but configuration is INVALID!\n"
                f"   Settings: {_notifier_settings}\n"
                f"   Please check your .env file."
            )
        else:
            logger.info("ℹ️ External notifier is disabled")
    
    return _notifier_settings


def reload_notifier_settings():
    """Force reload settings from .env (useful for testing)"""
    global _notifier_settings
    _notifier_settings = None
    return get_notifier_settings()
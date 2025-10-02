# config/notifier_settings.py

import logging
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class NotifierSettings(BaseSettings):
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
    
    @field_validator('external_notifier_api_url', 'external_notifier_auth_token', 'external_notifier_channel_id')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace"""
        stripped = v.strip() if v else v
        if v != stripped:
            logger.warning(f"⚠️ Whitespace detected and stripped from config value")
        return stripped
    
    class Config:
        env_file = ".env"
        extra = "allow"
        case_sensitive = False
    
    def is_valid(self) -> bool:
        if not self.external_notifier_enabled:
            return False
        
        required_fields = [
            self.external_notifier_api_url,
            self.external_notifier_auth_token,
            self.external_notifier_channel_id
        ]
        
        return all(field and field.strip() for field in required_fields)
    
    def __repr__(self) -> str:
        return (
            f"NotifierSettings("
            f"enabled={self.external_notifier_enabled}, "
            f"api_url={self.external_notifier_api_url or 'NOT_SET'}, "
            f"auth_token={'***' if self.external_notifier_auth_token else 'NOT_SET'}, "
            f"channel_id={self.external_notifier_channel_id or 'NOT_SET'}, "
            f"buffer_interval={self.external_notifier_buffer_interval}s"
            f")"
        )


_notifier_settings: NotifierSettings = None


def get_notifier_settings() -> NotifierSettings:
    global _notifier_settings
    
    if _notifier_settings is None:
        _notifier_settings = NotifierSettings()
        
        logger.info("="*70)
        logger.info("DEBUG: LOADING NOTIFIER SETTINGS FROM .env")
        logger.info(f"  enabled: {_notifier_settings.external_notifier_enabled}")
        logger.info(f"  api_url: '{_notifier_settings.external_notifier_api_url}'")
        logger.info(f"  api_url length: {len(_notifier_settings.external_notifier_api_url)}")
        logger.info(f"  auth_token: '{_notifier_settings.external_notifier_auth_token}'")
        logger.info(f"  auth_token length: {len(_notifier_settings.external_notifier_auth_token)}")
        logger.info(f"  channel_id: '{_notifier_settings.external_notifier_channel_id}'")
        logger.info(f"  channel_id length: {len(_notifier_settings.external_notifier_channel_id)}")
        logger.info(f"  buffer_interval: {_notifier_settings.external_notifier_buffer_interval}")
        logger.info(f"  is_valid(): {_notifier_settings.is_valid()}")
        
        # Check for hidden characters
        if _notifier_settings.external_notifier_auth_token:
            token_repr = repr(_notifier_settings.external_notifier_auth_token)
            logger.info(f"  auth_token repr: {token_repr}")
            
        if _notifier_settings.external_notifier_channel_id:
            channel_repr = repr(_notifier_settings.external_notifier_channel_id)
            logger.info(f"  channel_id repr: {channel_repr}")
        
        logger.info("="*70)
        
        if _notifier_settings.is_valid():
            logger.info("✅ External notifier settings validated successfully")
        elif _notifier_settings.external_notifier_enabled:
            logger.error("❌ External notifier is ENABLED but configuration is INVALID!")
        else:
            logger.info("ℹ️ External notifier is disabled")
    
    return _notifier_settings


def reload_notifier_settings():
    global _notifier_settings
    _notifier_settings = None
    return get_notifier_settings()
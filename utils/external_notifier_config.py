# utils/external_notifier_config.py

"""
Configuration wrapper for External Notifier

Acts as a bridge between NotifierSettings and the Worker
"""

import logging
from dataclasses import dataclass
from config.notifier_settings import get_notifier_settings

logger = logging.getLogger(__name__)


@dataclass
class ExternalNotifierConfig:
    """
    Configuration for external notifier worker
    
    This is a simplified wrapper around NotifierSettings
    """
    enabled: bool
    api_url: str
    auth_token: str
    channel_id: str
    buffer_interval: int = 30
    
    def is_valid(self) -> bool:
        """
        Check if config is valid for operation
        
        Returns:
            bool: True if all required fields are set and enabled
        """
        if not self.enabled:
            return False
        
        required_fields = [
            self.api_url,
            self.auth_token,
            self.channel_id
        ]
        
        return all(field and field.strip() for field in required_fields)
    
    def __repr__(self) -> str:
        """Safe string representation (hides auth token)"""
        return (
            f"ExternalNotifierConfig("
            f"enabled={self.enabled}, "
            f"api_url={self.api_url}, "
            f"auth_token={'***' if self.auth_token else 'None'}, "
            f"channel_id={self.channel_id}, "
            f"buffer_interval={self.buffer_interval}s"
            f")"
        )


def get_external_notifier_config() -> ExternalNotifierConfig:
    """
    Get configuration for external notifier
    
    Loads from NotifierSettings and converts to ExternalNotifierConfig
    
    Returns:
        ExternalNotifierConfig: Configuration object
    """
    settings = get_notifier_settings()
    
    config = ExternalNotifierConfig(
        enabled=settings.external_notifier_enabled,
        api_url=settings.external_notifier_api_url,
        auth_token=settings.external_notifier_auth_token,
        channel_id=settings.external_notifier_channel_id,
        buffer_interval=settings.external_notifier_buffer_interval
    )
    
    return config
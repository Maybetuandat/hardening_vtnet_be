
import logging
from dataclasses import dataclass
from config.notifier_settings import get_notifier_settings

logger = logging.getLogger(__name__)


@dataclass
class ExternalNotifierConfig:
    enabled: bool
    api_url: str
    auth_token: str
    channel_id: str
    buffer_interval: int = 30
    
def get_external_notifier_config() -> ExternalNotifierConfig:
    settings = get_notifier_settings()
    
    config = ExternalNotifierConfig(
        enabled=settings.external_notifier_enabled,
        api_url=settings.external_notifier_api_url,
        auth_token=settings.external_notifier_auth_token,
        channel_id=settings.external_notifier_channel_id,
        buffer_interval=settings.external_notifier_buffer_interval
    )
    
    return config
from pydantic_settings import BaseSettings


class NotifierSettings(BaseSettings):
    external_notifier_enabled: bool
    external_notifier_api_url: str
    external_notifier_auth_token: str
    external_notifier_channel_id: str
    external_notifier_buffer_interval: int

    class Config:
        env_file = ".env"
        extra = "allow"
        case_sensitive = False


def get_notifier_settings():
    return NotifierSettings()

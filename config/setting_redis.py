from typing import Optional
from pydantic_settings import BaseSettings


class RedisSettings(BaseSettings):
    
    REDIS_HOST: str 
    REDIS_PORT: int 
    REDIS_DB: int 
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool = True
    
    CACHE_BACKEND_KEY: str
    CACHE_DCIM_KEY: str
    CACHE_TTL_DCIM_INSTANCES: int
    CACHE_TTL_BACKEND_INSTANCES: int


    REDIS_CHANNEL_SCAN_REQUEST: str 
    REDIS_CHANNEL_SCAN_RESPONSE: str
    REDIS_CHANNEL_FIX_REQUEST: str
    REDIS_CHANNEL_FIX_RESPONSE: str 
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow" 
    def get_redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

def get_redis_settings():
    return RedisSettings()




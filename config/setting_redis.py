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

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow" 


def get_redis_settings():
    return RedisSettings()




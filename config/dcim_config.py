from pydantic_settings import BaseSettings


class DCIMSettings(BaseSettings):
    
    DCIM_BASE_URL: str 
    DCIM_TIMEOUT: int = 30  
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


def get_dcim_settings():
    return DCIMSettings()




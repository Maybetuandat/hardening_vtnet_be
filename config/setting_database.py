from typing import Optional
from pydantic_settings import BaseSettings


class SettingDatabase(BaseSettings):
    db_host: str 
    db_port: int 
    db_name: str 
    db_user: str 
    db_password: str 

   

    app_name: str = "Hardening VTNet BE"
    app_version: str = "1.0.0"
    app_description: str = "Backend for Hardening VTNet"
    debug: bool = True
    class Config:
        env_file= ".env"
        extra = "allow"
def get_settings():
    return SettingDatabase()
from pydantic import BaseModel


class InstanceRole(BaseModel):
    id: int
    name: str
    slug:str
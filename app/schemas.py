from datetime import time
from pydantic import BaseModel, Field
from typing import List, Optional

class CreateEnvironment(BaseModel):
    id: Optional[str]
    name: str
    description: str
    deleted: bool
    scan_start_time: time
    scan_terminate_time: time
    group: str
    active: bool

class CreateResource(BaseModel):
    id: Optional[str]
    environment: str
    resource_type: str
    ipv4: str
    ipv6: str
    console_username: str
    password: str
    port: int
    protocol: str
    name: str
    active: bool

class TestResource(BaseModel):    
    ipv4: Optional[str]
    ipv6: Optional[str]
    console_username: str
    password: str
    port: int
    protocol: str
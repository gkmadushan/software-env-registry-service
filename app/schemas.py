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
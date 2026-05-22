from pydantic import BaseModel
from typing import Optional

class UploadRequest(BaseModel):
    """Used internally after parsing uploaded files."""
    transactions_filename: str
    settlements_filename: str
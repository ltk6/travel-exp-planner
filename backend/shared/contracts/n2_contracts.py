from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class N2ImageInput(BaseModel):
    image: Optional[bytes] = Field(default=None, description="Raw bytes of the image to be processed.")

class N2ImageOutput(BaseModel):
    img_desc: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

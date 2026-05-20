from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class N5UserInput(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    img_desc: Optional[str] = ""

class N5LocationMetadata(BaseModel):
    name: Optional[str] = ""
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    coordinates: Optional[Dict[str, Optional[float]]] = None
    address: Optional[str] = None
    model_config = {"extra": "allow"}

class N5LocationItem(BaseModel):
    location_id: str
    metadata: Optional[N5LocationMetadata] = None
    model_config = {"extra": "allow"}

class N5Constraints(BaseModel):
    time_of_day: Optional[str] = "anytime"

class N5GenerateInput(BaseModel):
    user: N5UserInput = Field(default_factory=N5UserInput)
    locations: List[N5LocationItem] = Field(default_factory=list)
    constraints: Optional[N5Constraints] = Field(default_factory=N5Constraints)
    provider_override: Optional[str] = None


from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .n4_contracts import UserVectors

class UserInput(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    img_desc: Optional[str] = ""

class N6RankInput(BaseModel):
    user_input: UserInput = Field(default_factory=UserInput)
    user_vectors: UserVectors = Field(default_factory=UserVectors)
    activities: List[Dict[str, Any]] = Field(default_factory=list, description="List of raw activity dicts to rank.")
    top_k: int = Field(default=5)
    text_k: int = Field(default=0)
    tags_k: int = Field(default=0)

class RankedActivityItem(BaseModel):
    activity_id: Optional[str] = None
    location_id: Optional[str] = None
    score: float = Field(default=0.0)
    reason: Optional[str] = ""

class N6RankOutput(BaseModel):
    activities: List[RankedActivityItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

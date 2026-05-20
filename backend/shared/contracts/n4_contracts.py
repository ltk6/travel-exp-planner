from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UserVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N4RankInput(BaseModel):
    text_k: int = Field(default=0)
    tags_k: int = Field(default=0)
    user_vectors: UserVectors = Field(default_factory=UserVectors)
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="List of raw location dicts to rank.")
    top_k: int = Field(default=5)

class RankedLocationItem(BaseModel):
    location_id: Optional[str] = None
    score: float = Field(default=0.0)
    reason: Optional[str] = ""

class N4RankOutput(BaseModel):
    locations: List[RankedLocationItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class N1EmbedInput(BaseModel):
    text: str = Field(default="", description="The main text string to embed.")
    tags: List[str] = Field(default_factory=list, description="Associated categories/tags.")
    img_desc: str = Field(default="", description="Image description if present.")

class PreprocessedText(BaseModel):
    text: Optional[str] = ""
    aug_text: Optional[str] = ""
    aug_tags: Optional[str] = ""
    img_desc: Optional[str] = ""

class EmbedVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N1EmbedOutput(BaseModel):
    text_k: int = Field(default=0)
    tags_k: int = Field(default=0)
    preprocessed: PreprocessedText = Field(default_factory=PreprocessedText)
    vectors: EmbedVectors = Field(default_factory=EmbedVectors)
    metadata: Dict[str, Any] = Field(default_factory=dict)

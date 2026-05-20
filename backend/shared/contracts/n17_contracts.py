from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class N17FeedbackInput(BaseModel):
    user_input: Optional[str] = Field(default="", description="Original text prompt.")
    user_tags: List[str] = Field(default_factory=list, description="Original list of tags.")
    img_desc: Optional[str] = Field(default="", description="Original image description.")
    feedback_text: Optional[str] = Field(default="", description="The user feedback/correction text.")
    llm_chain: Optional[str] = Field(default=None, description="Model or chain override.")

class N17FeedbackOutput(BaseModel):
    refined_text: Optional[str] = ""
    refined_tags: List[str] = Field(default_factory=list)
    refined_img_desc: Optional[str] = ""
    explanation: Optional[str] = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

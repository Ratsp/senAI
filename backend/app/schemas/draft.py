from pydantic import BaseModel, Field

class DraftUpdatePayload(BaseModel):
    proposed_content: str = Field(..., min_length=1, description="The updated text content of the draft reply")

from pydantic import BaseModel, Field

class RespondPayload(BaseModel):
    reply_text: str | None = Field(default=None, description="The content of the reply or escalation details")
    escalate: bool = Field(..., description="Whether to escalate this email to human queue")

from typing import Literal
from pydantic import BaseModel, Field

class ContactStatusPayload(BaseModel):
    status: Literal["VIP", "Blocked", "Active", "Churned", "At Risk"] = Field(..., description="The contact's CRM status")

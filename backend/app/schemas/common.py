from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    error_code: str
    message: str
    detail: dict | str | None = None

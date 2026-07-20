from pydantic import BaseModel
from typing import Any


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Any = None
    total: int | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: int


class MessageResponse(BaseModel):
    message: str
    id: int | None = None

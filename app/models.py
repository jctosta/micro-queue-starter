from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID
    api_key: str


class TaskInput(BaseModel):
    data: dict[str, Any] = Field(..., description="Data to process in the GPU task")


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    result: Any | None = None


class BillingRecord(BaseModel):
    user_id: UUID
    task_id: UUID
    cost: float
    description: str

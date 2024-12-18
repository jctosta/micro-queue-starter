from typing import Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    api_key: str


class TaskInput(BaseModel):
    # @TODO: Replace the type of the data attribute with a Pydantic model that represents your requirements
    data: dict[str, Any] = Field(..., description="Data to process in the GPU task")


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    result: Optional[Any] = None


class BillingRecord(BaseModel):
    user_id: UUID
    task_id: UUID
    cost: float
    description: str

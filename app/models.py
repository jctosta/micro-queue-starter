from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID
    api_key: str


class TaskInput(BaseModel):
    kind: Literal["short", "long"] = Field(
        description="Picks the task, and so the queue it waits in"
    )
    # Capped below the Redis broker's visibility timeout (1 h by default): a
    # late-acked job still running after it would be handed to a second worker.
    duration_s: float = Field(
        ge=0, le=3000, description="How long the job keeps its GPU busy"
    )


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    result: Any | None = None


class BillingRecord(BaseModel):
    user_id: UUID
    task_id: UUID
    cost: float
    description: str

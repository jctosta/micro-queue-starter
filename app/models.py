from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class User(BaseModel):
    id: UUID
    api_key: str


SHORT_JOB_MAX_S = 60


class TaskInput(BaseModel):
    kind: Literal["short", "long"] = Field(
        description="Picks the task, and so the queue it waits in"
    )
    # Capped below the Redis broker's visibility timeout (1 h by default): a
    # late-acked job still running after it would be handed to a second worker.
    duration_s: float = Field(
        ge=0, le=3000, description="How long the job keeps its GPU busy"
    )

    @model_validator(mode="after")
    def short_jobs_are_short(self) -> Self:
        # A long job sent as "short" would pay the short price and hold up the
        # queue that exists to keep short jobs moving.
        if self.kind == "short" and self.duration_s > SHORT_JOB_MAX_S:
            raise ValueError(f"short jobs last at most {SHORT_JOB_MAX_S} s")
        return self


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    result: Any | None = None


class HealthResponse(BaseModel):
    redis: str
    queues: dict[str, int]


class BillingRecord(BaseModel):
    user_id: UUID
    task_id: UUID
    cost: float
    description: str

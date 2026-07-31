import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workflow import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.NEW
    client_id: uuid.UUID | None = None
    filing_request_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    """Full-field edit of a task (title/description/assignment/due date).
    Status changes go through PATCH /tasks/{id}/status instead, so drag-and-drop
    column moves and audit-relevant fields stay on separate, narrower endpoints."""
    title: str | None = None
    description: str | None = None
    client_id: uuid.UUID | None = None
    filing_request_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    due_date: datetime | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    firm_id: uuid.UUID | None
    client_id: uuid.UUID | None
    filing_request_id: uuid.UUID | None
    assigned_to_id: uuid.UUID | None
    due_date: datetime | None
    created_at: datetime


class KanbanBoard(BaseModel):
    """Tasks grouped by status, in the fixed column order the frontend board renders."""
    columns: dict[TaskStatus, list[TaskRead]]

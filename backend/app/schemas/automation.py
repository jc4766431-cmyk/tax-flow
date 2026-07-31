import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workflow import ReminderChannel


class ReminderCreate(BaseModel):
    filing_request_id: uuid.UUID
    days_before_deadline: int
    channel: ReminderChannel


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filing_request_id: uuid.UUID
    days_before_deadline: int
    channel: ReminderChannel
    sent_at: datetime | None
    cancelled: bool


class EscalationStatus(BaseModel):
    client_id: uuid.UUID
    client_name: str
    filing_request_id: uuid.UUID
    missing_categories: list[str]
    due_date: str | None
    days_overdue: int
    follow_ups_sent: int

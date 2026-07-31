import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    client_id: uuid.UUID
    recipient_id: uuid.UUID
    body: str
    attachment_document_id: uuid.UUID | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    client_id: uuid.UUID | None
    body: str
    attachment_document_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageRead]
    total: int
    page: int
    page_size: int

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.filing import FilingStage, FilingType


class FilingRequestCreate(BaseModel):
    client_id: uuid.UUID
    filing_type: FilingType
    period_label: str | None = None
    due_date: date | None = None
    assigned_accountant_id: uuid.UUID | None = None


class FilingAssignAccountant(BaseModel):
    """PATCH /filings/{id}/assign-accountant — sets/changes this specific
    filing's accountant, which may legitimately differ from the client's
    default (Client.assigned_accountant_id), e.g. a GST specialist handling
    this filing. Pass null to unassign."""

    assigned_accountant_id: uuid.UUID | None = None


class FilingStageUpdate(BaseModel):
    stage: FilingStage
    notes: str | None = None


class FilingStageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: FilingStage
    responsible_user_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class FilingRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    filing_type: FilingType
    stage: FilingStage
    assigned_accountant_id: uuid.UUID | None
    period_label: str | None
    due_date: date | None
    filed_date: date | None
    notes: str | None
    stage_history: list[FilingStageEventRead] = []

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole
    # Explicit, not defaulted to the caller's own firm — InviteService then
    # runs it through assert_firm_scoped the same way invoice_service.py's
    # create_invoice does with a loaded client's firm_id: a firm_admin
    # passing any firm other than their own gets a 403, only super_admin
    # may target an arbitrary firm.
    firm_id: uuid.UUID


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    firm_id: uuid.UUID
    role: UserRole
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    user_id: uuid.UUID
    firm_id: uuid.UUID
    company_name: str | None = None
    pan_number: str | None = None
    gstin: str | None = None
    assigned_accountant_id: uuid.UUID | None = None


class ClientQuickAdd(BaseModel):
    """POST /clients/quick-add — phone-first onboarding, additive to
    ClientCreate above (which stays exactly as-is, for the existing
    "complete profile after invite accepted" flow). See NEXT-PROMPT.md.
    firm_id is deliberately NOT here — the endpoint always uses the
    calling staff user's own firm_id, same as create_client's existing
    non-super-admin override."""

    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=30)
    company_name: str | None = None
    pan_number: str | None = None
    gstin: str | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    firm_id: uuid.UUID
    company_name: str | None
    pan_number: str | None
    gstin: str | None
    phone: str | None
    assigned_accountant_id: uuid.UUID | None
    # Computed from Client.has_portal_access (a @property, not a column) —
    # False for a quick-added client whose shadow User is still
    # is_active=False/no usable password, True once
    # POST /clients/{id}/invite-portal-access has been completed. Lets the
    # frontend decide whether to show the "Invite to web portal" button.
    has_portal_access: bool


class PaginatedClients(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    page_size: int

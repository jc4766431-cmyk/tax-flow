import uuid

from pydantic import BaseModel, ConfigDict


class ClientCreate(BaseModel):
    user_id: uuid.UUID
    firm_id: uuid.UUID
    company_name: str | None = None
    pan_number: str | None = None
    gstin: str | None = None
    assigned_accountant_id: uuid.UUID | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    firm_id: uuid.UUID
    company_name: str | None
    pan_number: str | None
    gstin: str | None
    assigned_accountant_id: uuid.UUID | None


class PaginatedClients(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    page_size: int

import uuid

from pydantic import BaseModel, ConfigDict


class FirmCreate(BaseModel):
    name: str
    legal_name: str | None = None
    tax_registration_number: str | None = None
    address: str | None = None


class FirmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_name: str | None
    tax_registration_number: str | None
    address: str | None
    is_active: bool

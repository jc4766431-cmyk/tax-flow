import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceStatus


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_amount: float


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    issue_date: date
    due_date: date
    line_items: list[InvoiceLineItem]
    tax_rate: float = 0
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    """Only DRAFT invoices may be edited — see invoice_service.py."""
    issue_date: date | None = None
    due_date: date | None = None
    line_items: list[InvoiceLineItem] | None = None
    tax_rate: float | None = None
    notes: str | None = None


class InvoiceMarkPaid(BaseModel):
    paid_at: date | None = None
    payment_reference: str | None = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    firm_id: uuid.UUID
    client_id: uuid.UUID
    invoice_number: str
    status: InvoiceStatus
    issue_date: date
    due_date: date
    paid_at: date | None
    line_items: list[dict]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    notes: str | None
    payment_reference: str | None
    razorpay_order_id: str | None

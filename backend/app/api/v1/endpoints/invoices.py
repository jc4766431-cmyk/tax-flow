import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.invoice import InvoiceStatus
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceMarkPaid,
    InvoiceRead,
    InvoiceUpdate,
)
from app.services.invoice_service import InvoiceService

# Firm-admin/accountant action, not client-facing — see HANDOFF §5.
router = APIRouter(
    prefix="/invoices", tags=["invoices"], dependencies=[Depends(require_admin)]
)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).create_invoice(payload, current_user)


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_id: uuid.UUID | None = Query(default=None),
    status_: InvoiceStatus | None = Query(default=None, alias="status"),
):
    return InvoiceService(db).list_invoices(current_user, client_id=client_id, status=status_)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).get_invoice(invoice_id, current_user)


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).update_invoice(invoice_id, payload, current_user)


@router.post("/{invoice_id}/send", response_model=InvoiceRead)
def send_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).send_invoice(invoice_id, current_user)


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceRead)
def mark_paid(
    invoice_id: uuid.UUID,
    payload: InvoiceMarkPaid,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).mark_paid(invoice_id, payload, current_user)


@router.post("/{invoice_id}/payment-order", response_model=InvoiceRead)
def create_payment_order(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a Razorpay Order for this invoice's total_amount (see
    InvoiceService.create_payment_order) — the returned invoice's
    razorpay_order_id is what a checkout flow would use to collect payment.
    Confirmed payment flips status to PAID automatically via
    app/api/v1/endpoints/razorpay_webhook.py, not this endpoint."""
    return InvoiceService(db).create_payment_order(invoice_id, current_user)


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InvoiceService(db).cancel_invoice(invoice_id, current_user)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    InvoiceService(db).delete_invoice(invoice_id, current_user)

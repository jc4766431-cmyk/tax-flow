"""
Business logic for client invoicing (HANDOFF.md §5). Staff-only (require_admin
at the router level — invoicing is a firm-admin/accountant action, not a
client-facing write). Firm-scoped like task_service.py/document_service.py.

No payment gateway: `mark_paid` is a manual staff action recording a
reference (bank transfer/UPI/cheque number), matching the reasoning in
models/billing.py's Subscription.payment_gateway_ref TODO.
"""
import datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate, InvoiceMarkPaid, InvoiceUpdate


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)

    def _get_or_404(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = self.invoices.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice

    def _get_client_or_404(self, client_id: uuid.UUID) -> Client:
        client = self.db.get(Client, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client

    def _compute_totals(self, line_items: list, tax_rate: float) -> tuple[float, float, float]:
        subtotal = sum(li.quantity * li.unit_amount for li in line_items)
        tax_amount = round(subtotal * (tax_rate / 100), 2)
        total = round(subtotal + tax_amount, 2)
        return round(subtotal, 2), tax_amount, total

    def _generate_number(self, firm_id: uuid.UUID) -> str:
        seq = self.invoices.next_sequence_for_firm(firm_id) + 1
        year = datetime.date.today().year
        return f"INV-{year}-{seq:04d}"

    def create_invoice(self, payload: InvoiceCreate, current_user: User) -> Invoice:
        client = self._get_client_or_404(payload.client_id)
        assert_firm_scoped(current_user, client.firm_id)

        subtotal, tax_amount, total = self._compute_totals(payload.line_items, payload.tax_rate)
        invoice = Invoice(
            firm_id=client.firm_id,
            client_id=client.id,
            invoice_number=self._generate_number(client.firm_id),
            status=InvoiceStatus.DRAFT,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            line_items=[li.model_dump() for li in payload.line_items],
            subtotal=subtotal,
            tax_rate=payload.tax_rate,
            tax_amount=tax_amount,
            total_amount=total,
            notes=payload.notes,
        )
        return self.invoices.create(invoice)

    def list_invoices(
        self,
        current_user: User,
        client_id: uuid.UUID | None = None,
        status: InvoiceStatus | None = None,
    ) -> list[Invoice]:
        from app.models.user import UserRole

        firm_id = None if current_user.role == UserRole.SUPER_ADMIN else current_user.firm_id
        return self.invoices.list(firm_id=firm_id, client_id=client_id, status=status)

    def get_invoice(self, invoice_id: uuid.UUID, current_user: User) -> Invoice:
        invoice = self._get_or_404(invoice_id)
        assert_firm_scoped(current_user, invoice.firm_id)
        return invoice

    def update_invoice(
        self, invoice_id: uuid.UUID, payload: InvoiceUpdate, current_user: User
    ) -> Invoice:
        invoice = self.get_invoice(invoice_id, current_user)
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=400, detail="Only draft invoices can be edited"
            )

        data = payload.model_dump(exclude_unset=True)
        if "line_items" in data and data["line_items"] is not None:
            invoice.line_items = [li.model_dump() if hasattr(li, "model_dump") else li for li in payload.line_items]
        for field in ("issue_date", "due_date", "notes"):
            if field in data and data[field] is not None:
                setattr(invoice, field, data[field])
        if "tax_rate" in data and data["tax_rate"] is not None:
            invoice.tax_rate = data["tax_rate"]

        # Recompute totals from the (possibly just-updated) stored line items.
        from app.schemas.invoice import InvoiceLineItem

        items = [InvoiceLineItem(**li) for li in invoice.line_items]
        subtotal, tax_amount, total = self._compute_totals(items, float(invoice.tax_rate))
        invoice.subtotal, invoice.tax_amount, invoice.total_amount = subtotal, tax_amount, total

        return self.invoices.save(invoice)

    def send_invoice(self, invoice_id: uuid.UUID, current_user: User) -> Invoice:
        invoice = self.get_invoice(invoice_id, current_user)
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Only draft invoices can be sent")
        invoice.status = InvoiceStatus.SENT
        return self.invoices.save(invoice)

    def mark_paid(
        self, invoice_id: uuid.UUID, payload: InvoiceMarkPaid, current_user: User
    ) -> Invoice:
        invoice = self.get_invoice(invoice_id, current_user)
        if invoice.status not in (InvoiceStatus.SENT, InvoiceStatus.OVERDUE):
            raise HTTPException(
                status_code=400, detail="Only sent/overdue invoices can be marked paid"
            )
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = payload.paid_at or datetime.date.today()
        invoice.payment_reference = payload.payment_reference
        return self.invoices.save(invoice)

    def cancel_invoice(self, invoice_id: uuid.UUID, current_user: User) -> Invoice:
        invoice = self.get_invoice(invoice_id, current_user)
        if invoice.status == InvoiceStatus.PAID:
            raise HTTPException(status_code=400, detail="Cannot cancel a paid invoice")
        invoice.status = InvoiceStatus.CANCELLED
        return self.invoices.save(invoice)

    def delete_invoice(self, invoice_id: uuid.UUID, current_user: User) -> None:
        invoice = self.get_invoice(invoice_id, current_user)
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Only draft invoices can be deleted")
        self.invoices.delete(invoice)

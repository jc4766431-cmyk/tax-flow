import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        return self.db.get(Invoice, invoice_id)

    def list(
        self,
        *,
        firm_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        status: InvoiceStatus | None = None,
    ) -> list[Invoice]:
        stmt = select(Invoice).order_by(Invoice.issue_date.desc())
        if firm_id is not None:
            stmt = stmt.where(Invoice.firm_id == firm_id)
        if client_id is not None:
            stmt = stmt.where(Invoice.client_id == client_id)
        if status is not None:
            stmt = stmt.where(Invoice.status == status)
        return list(self.db.scalars(stmt))

    def next_sequence_for_firm(self, firm_id: uuid.UUID) -> int:
        """Count of existing invoices for the firm, used to build
        "INV-<year>-<seq>" — see invoice_service.py."""
        return self.db.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.firm_id == firm_id)
        ) or 0

    def create(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def save(self, invoice: Invoice) -> Invoice:
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def delete(self, invoice: Invoice) -> None:
        self.db.delete(invoice)
        self.db.commit()

    def sum_paid_between(self, firm_id: uuid.UUID | None, period_start, period_end) -> float:
        stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at.between(period_start, period_end),
        )
        if firm_id is not None:
            stmt = stmt.where(Invoice.firm_id == firm_id)
        return float(self.db.scalar(stmt) or 0)

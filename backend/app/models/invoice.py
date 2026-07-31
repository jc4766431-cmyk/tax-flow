"""
Client invoicing — the firm billing *its own* clients (HANDOFF.md §5).
Distinct from app/models/billing.py's Plan/Subscription (which is the firm
paying TaxFlow) — do not conflate the two, per §5's own note.

Line items are stored as JSON on the invoice row rather than a child table:
invoices are edited as a whole (draft) then frozen once sent, so there's no
need to query/filter individual line items independently. Amounts are
Numeric(12, 2) INR, matching billing.py's Plan.price_per_seat_inr precision.

No payment gateway is wired up here, same as billing.py's Subscription —
`mark_paid` is a manual staff action (record a bank transfer/cheque/UPI
reference), not a webhook-driven state change.
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    client: Mapped["Client"] = relationship()

    # Human-facing sequential number, e.g. "INV-2026-0001" — unique per firm,
    # generated in invoice_service.py (max existing suffix + 1), not a DB
    # sequence, so it can stay firm-scoped ("INV-<firm-scoped-seq>").
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[date | None] = mapped_column(Date)

    # [{"description": str, "quantity": float, "unit_amount": float}, ...]
    # subtotal/tax/total are derived and stored (not recomputed on read) so
    # a sent invoice's amount is stable even if tax rate logic changes later.
    line_items: Mapped[list] = mapped_column(JSONB, default=list)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)  # percent, e.g. 18 for GST
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    notes: Mapped[str | None] = mapped_column(String(2000))
    payment_reference: Mapped[str | None] = mapped_column(String(255))

"""
Document upload, versioning, and AI-extraction metadata.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class DocumentStatus(str, enum.Enum):
    MISSING = "missing"
    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocumentCategory(str, enum.Enum):
    PAN_CARD = "pan_card"
    AADHAAR = "aadhaar"
    GST_REPORT = "gst_report"
    SALARY_SLIP = "salary_slip"
    INVESTMENT_PROOF = "investment_proof"
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    OTHER = "other"


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    client: Mapped["Client"] = relationship(back_populates="documents")

    filing_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filing_requests.id", ondelete="SET NULL")
    )

    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory), default=DocumentCategory.OTHER
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )

    original_filename: Mapped[str] = mapped_column(String(500))
    storage_key: Mapped[str] = mapped_column(String(1000))  # S3 object key
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    replaces_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # AI / OCR extraction results
    ocr_text: Mapped[str | None] = mapped_column(String)
    extracted_fields: Mapped[dict | None] = mapped_column(JSONB)
    extraction_confidence: Mapped[float | None] = mapped_column(Float)

    reviewer_comment: Mapped[str | None] = mapped_column(String(1000))


# Fixed checklist categories offered per filing, per the product spec. INVOICE and
# OTHER are valid document categories but are not part of the standard checklist —
# they're used for ad-hoc uploads outside the required-document flow.
CHECKLIST_CATEGORIES: list[DocumentCategory] = [
    DocumentCategory.PAN_CARD,
    DocumentCategory.AADHAAR,
    DocumentCategory.GST_REPORT,
    DocumentCategory.SALARY_SLIP,
    DocumentCategory.INVESTMENT_PROOF,
    DocumentCategory.BANK_STATEMENT,
]


class ChecklistItem(Base, UUIDMixin, TimestampMixin):
    """
    One required-document slot for a given filing (e.g. "PAN Card" for filing X).
    Seeded from CHECKLIST_CATEGORIES the first time a filing's checklist is viewed,
    then kept in sync with `status`/`fulfilling_document_id` as documents are
    uploaded, approved, or rejected against it.
    """
    __tablename__ = "checklist_items"
    __table_args__ = (
        UniqueConstraint("filing_request_id", "category", name="uq_checklist_item_filing_category"),
    )

    filing_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filing_requests.id", ondelete="CASCADE")
    )
    category: Mapped[DocumentCategory] = mapped_column(Enum(DocumentCategory), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.MISSING
    )
    fulfilling_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

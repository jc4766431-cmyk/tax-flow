"""
Engagement letter generation — closes the §5 "deliberately deferred" gap.

Renders a simple, real (not placeholder) engagement letter PDF for a client
using reportlab, stores it via the existing S3-compatible storage_service
(same bucket/key scheme as uploaded documents), and registers it as a
`Document` row (category=OTHER) so it shows up wherever a client/firm's
documents already do — no new model/migration needed.
"""
import io
import uuid
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.document import Document, DocumentCategory, DocumentStatus
from app.models.user import Firm, User
from app.repositories.document_repository import DocumentRepository
from app.services.storage_service import storage_service


def _render_pdf(firm: Firm, client: Client) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, _ = A4
    y = 27 * cm

    def line(text: str, size: int = 11, gap: float = 0.7):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(2 * cm, y, text)
        y -= gap * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Engagement Letter")
    y -= 1.2 * cm

    line(f"Date: {date.today().isoformat()}")
    line(f"Firm: {firm.legal_name or firm.name}")
    line(f"Client: {client.company_name or 'Client'}")
    if client.pan_number:
        line(f"PAN: {client.pan_number}")
    if client.gstin:
        line(f"GSTIN: {client.gstin}")
    y -= 0.5 * cm

    body = (
        f"This letter confirms the terms of engagement between {firm.legal_name or firm.name} "
        f"(\"the Firm\") and {client.company_name or 'the Client'} (\"the Client\") for the "
        "provision of accounting and tax compliance services. The Firm will prepare and file "
        "the Client's tax returns and related statutory filings based on information and "
        "documents supplied by the Client, and will notify the Client of outstanding items "
        "through the Firm's platform. The Client is responsible for the accuracy and "
        "completeness of information provided. This engagement may be terminated in writing "
        "by either party."
    )
    words = body.split()
    wrapped, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 > 95:
            wrapped.append(current)
            current = w
        else:
            current = f"{current} {w}".strip()
    if current:
        wrapped.append(current)
    for row in wrapped:
        line(row, size=10, gap=0.55)

    y -= 1 * cm
    line("_________________________", size=10)
    line("Authorized Signatory, Firm", size=10)
    y -= 0.5 * cm
    line("_________________________", size=10)
    line("Client Signature", size=10)

    c.showPage()
    c.save()
    return buf.getvalue()


def generate_engagement_letter(db: Session, current_user: User, client: Client) -> Document:
    firm = db.get(Firm, client.firm_id)
    pdf_bytes = _render_pdf(firm, client)

    filename = f"engagement-letter-{date.today().isoformat()}.pdf"
    storage_key = storage_service.build_storage_key(client.id, filename)
    storage_service.upload_bytes(storage_key, pdf_bytes, "application/pdf")

    document = Document(
        client_id=client.id,
        filing_request_id=None,
        category=DocumentCategory.OTHER,
        status=DocumentStatus.APPROVED,
        original_filename=filename,
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        uploaded_by_id=current_user.id,
    )
    return DocumentRepository(db).create(document)

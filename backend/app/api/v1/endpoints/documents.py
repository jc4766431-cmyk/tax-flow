import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.document import DocumentCategory, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    ChecklistItemRead,
    DocumentCreate,
    DocumentDownloadURL,
    DocumentRead,
    DocumentStatusUpdate,
    PaginatedDocuments,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/presigned-upload", response_model=PresignedUploadResponse)
def create_presigned_upload(
    payload: PresignedUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns an S3 presigned PUT URL; the client uploads bytes directly to S3,
    then calls POST /documents with the resulting storage_key."""
    return DocumentService(db).create_presigned_upload(current_user, payload)


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def register_document(
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Called after a successful S3 upload to create the Document row,
    schedule OCR (via FastAPI BackgroundTasks — runs after the response is
    sent, on this same instance; see app/worker/tasks.py), sync the
    filing's checklist, and notify the assigned accountant."""
    return DocumentService(db).register_document(current_user, payload, background_tasks)


@router.get("", response_model=PaginatedDocuments)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_id: uuid.UUID | None = Query(default=None),
    filing_request_id: uuid.UUID | None = Query(default=None),
    category: DocumentCategory | None = Query(default=None),
    status_: DocumentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Clients are always scoped to their own documents regardless of the
    client_id filter passed. Staff may filter by client_id/filing_request_id/status
    — status is what backs the admin review panel's "awaiting review" queue."""
    items, total = DocumentService(db).list_documents(
        current_user,
        client_id=client_id,
        filing_request_id=filing_request_id,
        category=category,
        status=status_,
        page=page,
        page_size=page_size,
    )
    return PaginatedDocuments(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{document_id}/status", response_model=DocumentRead,
              dependencies=[Depends(require_staff)])
def update_document_status(
    document_id: uuid.UUID,
    payload: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff-only: approve/reject/request re-upload. Writes an AuditLog entry,
    syncs the checklist item, and notifies the client."""
    return DocumentService(db).update_status(current_user, document_id, payload)


@router.get("/{document_id}/download-url", response_model=DocumentDownloadURL)
def get_download_url(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns a short-lived signed S3 GET URL rather than streaming the file
    through the API."""
    url, expires_in = DocumentService(db).get_download_url(current_user, document_id)
    return DocumentDownloadURL(download_url=url, expires_in_seconds=expires_in)


@router.get("/checklist/{filing_request_id}", response_model=list[ChecklistItemRead])
def get_checklist(
    filing_request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the fixed per-filing document checklist (PAN Card, Aadhaar, GST
    Reports, Salary Slips, Investment Proofs, Bank Statements), seeding it on
    first access and keeping status in sync with uploaded/reviewed documents."""
    return DocumentService(db).get_checklist(current_user, filing_request_id)

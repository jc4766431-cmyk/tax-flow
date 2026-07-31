"""
Business logic for the documents module: presigned S3 uploads, document
registration, the fixed per-filing checklist, and staff review/approval.
Kept separate from the API layer so it is independently unit-testable.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.client import Client
from app.models.document import ChecklistItem, Document, DocumentCategory, DocumentStatus
from app.models.filing import FilingRequest
from app.models.user import User, UserRole
from app.models.workflow import AuditLog, Notification, NotificationType
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentStatusUpdate,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.storage_service import (
    PRESIGNED_DOWNLOAD_EXPIRY_SECONDS,
    storage_service,
)
from app.worker.tasks import process_document_ocr


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)

    # --- Access control helpers ---------------------------------------

    def _get_client_or_404(self, client_id: uuid.UUID) -> Client:
        client = self.db.get(Client, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client

    def _assert_can_write(self, current_user: User, client: Client) -> None:
        """Clients may only act on their own record; staff may only act on a
        client within their own firm (firm-scoping gap from HANDOFF.md §2 —
        now closed)."""
        if current_user.role == UserRole.CLIENT:
            if client.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            assert_firm_scoped(current_user, client.firm_id)

    def _assert_can_read(self, current_user: User, document: Document) -> None:
        client = self.db.get(Client, document.client_id)
        if current_user.role == UserRole.CLIENT:
            if not client or client.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            assert_firm_scoped(current_user, client.firm_id if client else None)

    # --- Upload flow ----------------------------------------------------

    def create_presigned_upload(
        self, current_user: User, payload: PresignedUploadRequest
    ) -> PresignedUploadResponse:
        client = self._get_client_or_404(payload.client_id)
        self._assert_can_write(current_user, client)

        storage_key = storage_service.build_storage_key(client.id, payload.original_filename)
        upload_url = storage_service.generate_presigned_upload(storage_key, payload.mime_type)
        return PresignedUploadResponse(upload_url=upload_url, storage_key=storage_key)

    def register_document(self, current_user: User, payload: DocumentCreate) -> Document:
        """Called by the client after the S3 PUT succeeds, to create the DB row,
        enqueue OCR, sync the checklist, and notify the assigned accountant."""
        client = self._get_client_or_404(payload.client_id)
        self._assert_can_write(current_user, client)

        document = Document(
            client_id=payload.client_id,
            filing_request_id=payload.filing_request_id,
            category=payload.category,
            status=DocumentStatus.UPLOADED,
            original_filename=payload.original_filename,
            storage_key=payload.storage_key,
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            replaces_document_id=payload.replaces_document_id,
            uploaded_by_id=current_user.id,
        )
        if payload.replaces_document_id:
            previous = self.documents.get_by_id(payload.replaces_document_id)
            if previous:
                document.version = previous.version + 1

        document = self.documents.create(document)

        if payload.filing_request_id:
            self._sync_checklist_on_upload(payload.filing_request_id, payload.category, document)

        process_document_ocr.delay(str(document.id))

        if client.assigned_accountant_id:
            self.db.add(Notification(
                user_id=client.assigned_accountant_id,
                type=NotificationType.MISSING_DOCUMENT,
                title="Document uploaded",
                body=f"{client.company_name or 'A client'} uploaded {document.category.value}",
                link_url=f"/admin/clients/{client.id}",
            ))
            self.db.commit()

        return document

    def _sync_checklist_on_upload(
        self, filing_request_id: uuid.UUID, category: DocumentCategory, document: Document
    ) -> None:
        item = self.documents.get_checklist_item(filing_request_id, category)
        if item is None:
            return  # not part of the fixed checklist (e.g. INVOICE/OTHER) — nothing to sync
        item.status = DocumentStatus.UPLOADED
        item.fulfilling_document_id = document.id
        self.db.add(item)
        self.db.commit()

    # --- Listing / retrieval --------------------------------------------

    def list_documents(
        self,
        current_user: User,
        *,
        client_id: uuid.UUID | None,
        filing_request_id: uuid.UUID | None,
        category: DocumentCategory | None,
        status: DocumentStatus | None = None,
        page: int,
        page_size: int,
    ):
        firm_id: uuid.UUID | None = None
        if current_user.role == UserRole.CLIENT:
            # Clients are always scoped to their own client record, regardless of
            # what client_id they pass (or don't pass).
            own_client = self.db.query(Client).filter(Client.user_id == current_user.id).first()
            client_id = own_client.id if own_client else uuid.uuid4()  # no match -> empty result
        elif current_user.role != UserRole.SUPER_ADMIN:
            # Staff (firm_admin/accountant/reviewer) are scoped to their own
            # firm's documents regardless of client_id/filing_request_id
            # filters passed — closes the firm-scoping gap from HANDOFF.md §2.
            firm_id = current_user.firm_id

        return self.documents.list_documents(
            client_id=client_id,
            filing_request_id=filing_request_id,
            category=category,
            status=status,
            firm_id=firm_id,
            page=page,
            page_size=page_size,
        )

    def get_download_url(self, current_user: User, document_id: uuid.UUID):
        document = self.documents.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        self._assert_can_read(current_user, document)

        url = storage_service.generate_presigned_download(
            document.storage_key, filename=document.original_filename
        )
        return url, PRESIGNED_DOWNLOAD_EXPIRY_SECONDS

    # --- Staff review -----------------------------------------------------

    def update_status(
        self, current_user: User, document_id: uuid.UUID, payload: DocumentStatusUpdate
    ) -> Document:
        document = self.documents.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Router already enforces staff-only via require_staff; this adds the
        # firm-scoping layer so an accountant can only review their own
        # firm's documents, not any firm's (HANDOFF.md §2 gap — now closed).
        client = self.db.get(Client, document.client_id)
        self._assert_can_write(current_user, client) if client else None

        document.status = payload.status
        if payload.reviewer_comment is not None:
            document.reviewer_comment = payload.reviewer_comment
        document = self.documents.update(document)

        if document.filing_request_id:
            item = self.documents.get_checklist_item(document.filing_request_id, document.category)
            if item and item.fulfilling_document_id == document.id:
                item.status = payload.status
                self.db.add(item)

        self.db.add(AuditLog(
            actor_user_id=current_user.id,
            action="document.status_changed",
            resource_type="document",
            resource_id=str(document.id),
            metadata_json={"new_status": payload.status.value, "comment": payload.reviewer_comment},
        ))

        client = self.db.get(Client, document.client_id)
        if client:
            notif_type = (
                NotificationType.FILING_COMPLETED
                if payload.status == DocumentStatus.APPROVED
                else NotificationType.MISSING_DOCUMENT
            )
            self.db.add(Notification(
                user_id=client.user_id,
                type=notif_type,
                title=f"Document {payload.status.value}",
                body=payload.reviewer_comment or f"Your {document.category.value} was {payload.status.value}.",
            ))

        self.db.commit()
        self.db.refresh(document)
        return document

    # --- Checklist ----------------------------------------------------------

    def get_checklist(self, current_user: User, filing_request_id: uuid.UUID) -> list[ChecklistItem]:
        items = self.documents.seed_checklist(filing_request_id)
        # RBAC: a client may only view the checklist for their own filing;
        # staff may only view it for a filing belonging to their own firm
        # (super_admin exempt) — closes the same firm-scoping gap as the
        # rest of this module.
        if items:
            filing = self.db.get(FilingRequest, filing_request_id)
            client = self.db.get(Client, filing.client_id) if filing else None
            if current_user.role == UserRole.CLIENT:
                if not client or client.user_id != current_user.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            else:
                assert_firm_scoped(current_user, client.firm_id if client else None)
        return items

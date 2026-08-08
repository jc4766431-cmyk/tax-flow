"""
Business logic for the documents module: presigned S3 uploads, document
registration, the fixed per-filing checklist, and staff review/approval.
Kept separate from the API layer so it is independently unit-testable.
"""
import uuid

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.client import Client
from app.models.document import ChecklistItem, Document, DocumentCategory, DocumentStatus
from app.models.filing import FilingRequest, FilingStage, FilingStageEvent
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

    def register_document(
        self,
        current_user: User,
        payload: DocumentCreate,
        background_tasks: BackgroundTasks | None = None,
    ) -> Document:
        """Called by the client after the S3 PUT succeeds, to create the DB row,
        schedule OCR, sync the checklist, and notify the assigned accountant.

        `background_tasks` is optional so callers that don't have a live
        request in flight (e.g. whatsapp_service.py's inbound-media path,
        which runs from a webhook handler that already returns a fast 200
        before this would matter) can still call this without one — OCR is
        simply skipped in that case rather than run synchronously and risk
        blocking the webhook response. See app/worker/tasks.py's docstring
        for the no-separate-worker architecture this fits into.
        """
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
            self._maybe_advance_stage(
                filing_request_id=payload.filing_request_id,
                from_stage=FilingStage.REQUESTED,
                to_stage=FilingStage.DOCUMENTS_UPLOADED,
                required_statuses={
                    DocumentStatus.UPLOADED,
                    DocumentStatus.UNDER_REVIEW,
                    DocumentStatus.APPROVED,
                    DocumentStatus.REJECTED,
                },
                current_user=current_user,
                notes="Auto-advanced: all checklist documents uploaded",
            )

        if background_tasks is not None:
            background_tasks.add_task(process_document_ocr, str(document.id))

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
        # Ensure the checklist rows exist even if nobody has viewed
        # GET .../checklist yet (seed_checklist is idempotent) — otherwise a
        # client who uploads before staff ever opens the checklist tab would
        # silently never sync, and auto-stage-advancement below would never
        # see a complete checklist to advance on.
        self.documents.seed_checklist(filing_request_id)
        item = self.documents.get_checklist_item(filing_request_id, category)
        if item is None:
            return  # not part of the fixed checklist (e.g. INVOICE/OTHER) — nothing to sync
        item.status = DocumentStatus.UPLOADED
        item.fulfilling_document_id = document.id
        self.db.add(item)
        self.db.commit()

    # --- Filing stage auto-transitions ----------------------------------
    # Nothing else moves FilingRequest.stage automatically today — the only
    # other path is a staff member calling PATCH /filings/{id}/stage
    # directly. These two hooks close that gap for the two transitions that
    # are clearly derivable from checklist state; approval_required -> filed
    # -> completed stay manual/staff-driven.

    def _maybe_advance_stage(
        self,
        *,
        filing_request_id: uuid.UUID,
        from_stage: FilingStage,
        to_stage: FilingStage,
        required_statuses: set[DocumentStatus],
        current_user: User,
        notes: str,
    ) -> None:
        filing = self.db.get(FilingRequest, filing_request_id)
        if filing is None or filing.stage != from_stage:
            # Only advance from the exact expected stage — never regress a
            # filing that's already further along (e.g. a client re-upload
            # after rejection shouldn't knock it back from under_review to
            # documents_uploaded).
            return

        items = self.documents.list_checklist_items(filing_request_id)
        required_items = [item for item in items if item.required]
        if not required_items or any(item.status not in required_statuses for item in required_items):
            return

        filing.stage = to_stage
        self.db.add(filing)
        self.db.add(FilingStageEvent(
            filing_request_id=filing.id,
            stage=to_stage,
            responsible_user_id=current_user.id,
            notes=notes,
        ))
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
                if payload.status == DocumentStatus.APPROVED:
                    # Product-intent call (see HANDOFF.md gap #2): once every
                    # required checklist item is approved, under_review is
                    # treated as system-driven ("all docs are in, ready for
                    # staff review") rather than a separate manual "staff
                    # started working on it" signal. Revisit if that
                    # distinction turns out to matter.
                    self._maybe_advance_stage(
                        filing_request_id=document.filing_request_id,
                        from_stage=FilingStage.DOCUMENTS_UPLOADED,
                        to_stage=FilingStage.UNDER_REVIEW,
                        required_statuses={DocumentStatus.APPROVED},
                        current_user=current_user,
                        notes="Auto-advanced: all checklist documents approved",
                    )

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

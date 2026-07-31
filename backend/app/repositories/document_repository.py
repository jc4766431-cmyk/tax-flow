"""
Repository pattern: isolates SQLAlchemy queries from business logic (services).
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.document import CHECKLIST_CATEGORIES, ChecklistItem, Document, DocumentStatus
from app.models.filing import FilingRequest


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def list_documents(
        self,
        *,
        client_id: uuid.UUID | None = None,
        filing_request_id: uuid.UUID | None = None,
        category=None,
        status=None,
        firm_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        stmt = select(Document)
        if firm_id is not None:
            # Firm-scoping (staff): only documents belonging to a client in
            # this firm. Joins to Client rather than requiring a firm_id
            # column on Document itself, since Document doesn't carry one.
            stmt = stmt.join(Client, Client.id == Document.client_id).where(
                Client.firm_id == firm_id
            )
        if client_id is not None:
            stmt = stmt.where(Document.client_id == client_id)
        if filing_request_id is not None:
            stmt = stmt.where(Document.filing_request_id == filing_request_id)
        if category is not None:
            stmt = stmt.where(Document.category == category)
        if status is not None:
            stmt = stmt.where(Document.status == status)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = self.db.scalars(stmt).all()
        return items, total

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def update(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    # --- Checklist ---------------------------------------------------

    def get_checklist_item(
        self, filing_request_id: uuid.UUID, category
    ) -> ChecklistItem | None:
        stmt = select(ChecklistItem).where(
            ChecklistItem.filing_request_id == filing_request_id,
            ChecklistItem.category == category,
        )
        return self.db.scalar(stmt)

    def list_checklist_items(self, filing_request_id: uuid.UUID) -> list[ChecklistItem]:
        stmt = select(ChecklistItem).where(
            ChecklistItem.filing_request_id == filing_request_id
        )
        return list(self.db.scalars(stmt).all())

    def seed_checklist(self, filing_request_id: uuid.UUID) -> list[ChecklistItem]:
        """
        Ensures a ChecklistItem row exists for every fixed checklist category on
        this filing. Idempotent — safe to call on every GET of the checklist.
        """
        filing = self.db.get(FilingRequest, filing_request_id)
        if filing is None:
            return []

        existing = {item.category for item in self.list_checklist_items(filing_request_id)}
        created = False
        for category in CHECKLIST_CATEGORIES:
            if category not in existing:
                self.db.add(
                    ChecklistItem(
                        filing_request_id=filing_request_id,
                        category=category,
                        required=True,
                        status=DocumentStatus.MISSING,
                    )
                )
                created = True
        if created:
            self.db.commit()

        return self.list_checklist_items(filing_request_id)

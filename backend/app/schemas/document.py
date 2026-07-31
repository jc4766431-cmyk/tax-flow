import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentCategory, DocumentStatus


class PresignedUploadRequest(BaseModel):
    client_id: uuid.UUID
    original_filename: str
    mime_type: str


class PresignedUploadResponse(BaseModel):
    upload_url: str
    storage_key: str


class DocumentCreate(BaseModel):
    client_id: uuid.UUID
    filing_request_id: uuid.UUID | None = None
    category: DocumentCategory = DocumentCategory.OTHER
    storage_key: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    replaces_document_id: uuid.UUID | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    filing_request_id: uuid.UUID | None
    category: DocumentCategory
    status: DocumentStatus
    original_filename: str
    mime_type: str
    file_size_bytes: int
    version: int
    replaces_document_id: uuid.UUID | None
    uploaded_by_id: uuid.UUID
    extracted_fields: dict | None
    extraction_confidence: float | None
    reviewer_comment: str | None


class PaginatedDocuments(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int
    page_size: int


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus
    reviewer_comment: str | None = Field(default=None, max_length=1000)


class DocumentDownloadURL(BaseModel):
    download_url: str
    expires_in_seconds: int


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filing_request_id: uuid.UUID
    category: DocumentCategory
    required: bool
    status: DocumentStatus
    fulfilling_document_id: uuid.UUID | None

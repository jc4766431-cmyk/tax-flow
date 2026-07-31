import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped, get_current_user, require_staff
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User, UserRole
from app.schemas.client import ClientCreate, ClientRead, PaginatedClients
from app.schemas.document import DocumentRead
from app.services.engagement_letter_service import generate_engagement_letter

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=PaginatedClients)
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
    search: str | None = Query(default=None, description="Search by company name or PAN"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Client)
    # Firm-scoping: non-super-admin staff only ever see their own firm's clients.
    if current_user.role != UserRole.SUPER_ADMIN:
        stmt = stmt.where(Client.firm_id == current_user.firm_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where((Client.company_name.ilike(like)) | (Client.pan_number.ilike(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()

    return PaginatedClients(items=items, total=total or 0, page=page, page_size=page_size)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    data = payload.model_dump()
    # Firm-scoping: non-super-admin staff can only create clients in their own
    # firm — silently ignore/override whatever firm_id they passed. Only
    # super_admin (platform-level) may create a client under an arbitrary firm.
    if current_user.role != UserRole.SUPER_ADMIN:
        data["firm_id"] = current_user.firm_id
    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Clients may only view their own record.
    if current_user.role == UserRole.CLIENT and client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Staff may only view clients within their own firm (super_admin exempt).
    if current_user.role != UserRole.CLIENT:
        assert_firm_scoped(current_user, client.firm_id)

    return client


@router.post(
    "/{client_id}/engagement-letter",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_engagement_letter(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Generate an engagement letter PDF for a client and register it as a
    Document (category=OTHER), closing the section-5 "engagement letter
    generation" gap. Staff-only, firm-scoped (super_admin exempt)."""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    assert_firm_scoped(current_user, client.firm_id)

    document = generate_engagement_letter(db, current_user, client)
    db.commit()
    db.refresh(document)
    return document

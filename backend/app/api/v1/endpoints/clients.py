import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped, get_current_user, require_staff
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User, UserRole
from app.schemas.client import (
    ClientAssignAccountant,
    ClientCreate,
    ClientQuickAdd,
    ClientRead,
    PaginatedClients,
)
from app.schemas.document import DocumentRead
from app.schemas.invite import InviteRead
from app.services.engagement_letter_service import generate_engagement_letter
from app.services.invite_service import InviteService
from app.services.notification_channels import EmailSender
from app.services.whatsapp_service import WhatsAppService

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


@router.post("/quick-add", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def quick_add_client(
    payload: ClientQuickAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Phone-first client onboarding — see NEXT-PROMPT.md. Creates a
    backing "shadow" User (role=CLIENT, a random unusable password never
    issued to anyone, is_active=False, a placeholder @taxflow.internal
    email so User.email's NOT NULL/unique constraint never has to change)
    and the Client row in one transaction, then sends the first
    document-request message over WhatsApp. Every existing relationship,
    query, and RBAC check that assumes client.user exists keeps working
    completely unmodified — see NEXT-PROMPT.md's "why this design" section
    and whatsapp_service.py's module docstring.

    Staff-only, firm-scoped exactly like create_client above: a
    non-super-admin always creates the client in their own firm; there is
    no firm_id in the request payload to override.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        # A super_admin has no firm of their own to quick-add a client
        # into — same "no firm to fall back to" rule task_service's
        # create_task already applies for a client-less task by a
        # super_admin. Quick-add is a firm-staff action; super_admin
        # should use POST /clients (with an explicit firm_id) instead.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="super_admin has no firm to quick-add a client into",
        )

    normalized_phone = WhatsAppService.normalize_phone(payload.phone)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="A valid phone number is required")

    shadow_user = User(
        email=f"shadow+{uuid.uuid4().hex}@taxflow.internal",
        # Random, never issued to anyone, never usable to log in — login is
        # impossible until POST /auth/accept-client-invite (see
        # AuthService.activate_shadow_client) sets a real password AND
        # flips is_active below to True.
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        full_name=payload.name,
        role=UserRole.CLIENT,
        firm_id=current_user.firm_id,
        is_active=False,
    )
    db.add(shadow_user)
    db.flush()

    client = Client(
        user_id=shadow_user.id,
        firm_id=current_user.firm_id,
        phone=normalized_phone,
        company_name=payload.company_name,
        pan_number=payload.pan_number,
        gstin=payload.gstin,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    # Fire-and-forget-ish: send the first document-request message. Not
    # backgrounded via BackgroundTasks — this is a single outbound API
    # call (WhatsAppBusinessAPISender.send_text no-ops instantly when
    # unconfigured, same as everywhere else in this codebase that sends
    # a notification synchronously), not the multi-second OCR/media-
    # download work BackgroundTasks is used for elsewhere in this router.
    WhatsAppService(db).send_document_checklist_request(payload.phone, payload.name)

    return client


@router.post("/{client_id}/invite-portal-access", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def invite_portal_access(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Optional upgrade for a quick-added ("shadow user") client to real
    web-portal access — see NEXT-PROMPT.md step 4. Staff-only, firm-scoped.
    Sends the accept-invite link over WhatsApp (this client's whole
    relationship with the product so far has been WhatsApp, per
    NEXT-PROMPT.md — don't switch channels on them for this) and, if the
    client's User already has a real (non-placeholder) email by now, over
    email too.
    """
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    assert_firm_scoped(current_user, client.firm_id)

    if client.has_portal_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This client already has web portal access",
        )
    if not client.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This client has no phone number on file to send the invite to",
        )

    invite = InviteService(db).create_shadow_client_invite(client, current_user)
    db.commit()
    db.refresh(invite)

    link = f"{settings.FRONTEND_URL}/accept-client-invite?token={invite.token}"
    message = (
        f"Hi {client.user.full_name}, you can now set up full web portal "
        f"access to view your filings and documents anytime: {link} "
        f"(link expires in 7 days)"
    )
    WhatsAppService(db).sender.send_text(client.phone, message)
    if not client.user.email.endswith("@taxflow.internal"):
        EmailSender().send_text(client.user.email, message)

    return invite


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


@router.patch("/{client_id}/assign-accountant", response_model=ClientRead)
def assign_accountant(
    client_id: uuid.UUID,
    payload: ClientAssignAccountant,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Sets/changes a client's *default* accountant directly, independent of
    any filing — staff-only, firm-scoped same as other client mutations.

    This is deliberately a separate, explicit action from filing-level
    accountant assignment: creating/updating a filing with an
    assigned_accountant_id only backfills this field when it's still null
    (see filings.py), so it never silently overrides a default set here.
    Pass assigned_accountant_id: null to unassign.
    """
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    assert_firm_scoped(current_user, client.firm_id)

    if payload.assigned_accountant_id is not None:
        accountant = db.get(User, payload.assigned_accountant_id)
        if not accountant:
            raise HTTPException(status_code=404, detail="Accountant not found")
        if accountant.role == UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign a client-role user as an accountant",
            )
        if accountant.role != UserRole.SUPER_ADMIN and accountant.firm_id != client.firm_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Accountant must belong to the client's firm",
            )

    client.assigned_accountant_id = payload.assigned_accountant_id
    db.add(client)
    db.commit()
    db.refresh(client)
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

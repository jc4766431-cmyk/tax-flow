"""
WhatsApp-first client channel — inbound processing pipeline.

Per STRATEGY_REVIEW.md Phase 5 idea #1 / NEXT-PROMPT.md: WhatsApp is meant to
be *the* client-facing interface for document collection, not a reminder
bolt-on. A client should be able to reply to a document request with a photo
and get a confirmation, with zero login, ever. This module is the backend
half of that; the web dashboard widgets (§3d) are the secondary,
staff/browsing-focused surface.

Design constraints this was built against (see NEXT-PROMPT.md for the full
list):
  - `Client` has no `phone` column of its own — it's on `User` via
    `Client.user_id`. Matching is phone -> User -> Client.
  - Document creation reuses `DocumentService.register_document` rather than
    duplicating its RBAC/checklist-sync/notification logic — we act "as the
    client's own user" by loading `client.user` and passing it as
    `current_user`, which satisfies `DocumentService._assert_can_write`'s
    "clients may only act on their own record" check exactly, since it *is*
    their own record.
  - No real WhatsApp Business API credentials exist yet. Inbound webhook
    *shape* parsing and phone matching work today (testable with a synthetic
    payload); downloading real media and sending real replies do not, until
    `WHATSAPP_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID` are set — see
    `notification_channels.py`.
"""
import hashlib
import hmac
import logging
import re
import uuid

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.client import Client
from app.models.document import CHECKLIST_CATEGORIES, DocumentCategory
from app.models.user import User
from app.models.whatsapp import (
    WhatsAppInboundMessage,
    WhatsAppMessageType,
    WhatsAppProcessingStatus,
)
from app.schemas.document import DocumentCreate
from app.services.document_service import DocumentService
from app.services.notification_channels import (
    WhatsAppBusinessAPISender,
    WhatsAppNotConfiguredError,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

_MEDIA_TYPES = {WhatsAppMessageType.IMAGE, WhatsAppMessageType.DOCUMENT}

# Plain-language labels for the fixed checklist, used only for the outbound
# quick-add welcome message (NEXT-PROMPT.md step 2) — kept here rather than
# on the DocumentCategory enum itself since this wording is WhatsApp-copy
# specific, not a general-purpose display label.
_CHECKLIST_LABELS: dict[DocumentCategory, str] = {
    DocumentCategory.PAN_CARD: "PAN card",
    DocumentCategory.AADHAAR: "Aadhaar",
    DocumentCategory.GST_REPORT: "GST report",
    DocumentCategory.SALARY_SLIP: "salary slip",
    DocumentCategory.INVESTMENT_PROOF: "investment proof",
    DocumentCategory.BANK_STATEMENT: "bank statement",
}


class WhatsAppWebhookVerificationError(Exception):
    """Raised when Meta's GET verification handshake doesn't match our
    configured WHATSAPP_VERIFY_TOKEN."""


class WhatsAppSignatureVerificationError(Exception):
    """Raised when the `X-Hub-Signature-256` header on an inbound POST
    doesn't match the HMAC-SHA256 of the raw body, keyed with
    WHATSAPP_APP_SECRET. Only raised when WHATSAPP_APP_SECRET is actually
    configured — see verify_signature's docstring for the unconfigured case."""


def verify_signature(raw_body: bytes, signature_header: str | None) -> None:
    """Verifies Meta's `X-Hub-Signature-256: sha256=<hex>` header against the
    raw (unparsed) request body, keyed with WHATSAPP_APP_SECRET.

    Deliberately takes the *raw* bytes rather than a re-serialized dict —
    HMAC verification must run over the exact bytes Meta signed, and
    `json.dumps(request.json())` is not guaranteed to round-trip to the same
    bytes (key order, whitespace, unicode escaping can all differ).

    Same "no-op when unconfigured, don't fabricate trust" pattern as the rest
    of this module (see notification_channels.py): if WHATSAPP_APP_SECRET
    isn't set yet (no real Meta App exists — see NEXT-PROMPT.md), this logs a
    loud warning and returns without raising, rather than blocking every
    webhook delivery on a secret nobody has been given yet. Once
    WHATSAPP_APP_SECRET is set, verification is strictly enforced and any
    missing/mismatched signature raises.
    """
    if not settings.WHATSAPP_APP_SECRET:
        logger.warning(
            "[whatsapp] WHATSAPP_APP_SECRET is not set — skipping "
            "X-Hub-Signature-256 verification. This webhook currently trusts "
            "any POST body. Set WHATSAPP_APP_SECRET before exposing this "
            "endpoint on a real public URL."
        )
        return

    if not signature_header or not signature_header.startswith("sha256="):
        raise WhatsAppSignatureVerificationError(
            "missing or malformed X-Hub-Signature-256 header"
        )

    provided_digest = signature_header[len("sha256=") :]
    expected_digest = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    # Constant-time comparison — a naive `==` here would reintroduce a timing
    # side-channel, defeating the point of verifying the signature at all.
    if not hmac.compare_digest(provided_digest, expected_digest):
        raise WhatsAppSignatureVerificationError("signature mismatch")


class WhatsAppService:
    def __init__(self, db: Session):
        self.db = db
        self.sender = WhatsAppBusinessAPISender()

    # --- Staff-facing message log (admin UI) -----------------------------

    def list_messages(
        self,
        current_user: User,
        *,
        status_filter: WhatsAppProcessingStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WhatsAppInboundMessage], int]:
        """Backs the admin "WhatsApp" panel — a read view over the inbound
        log described in this module's docstring. Firm-scoped through the
        matched Client (rows with no matched client, i.e. UNMATCHED, are
        platform-level noise with nothing to scope by, so only SUPER_ADMIN
        sees those; firm staff see only rows matched to their own firm's
        clients)."""
        stmt = select(WhatsAppInboundMessage).order_by(
            WhatsAppInboundMessage.created_at.desc()
        )
        if current_user.role.value != "super_admin":
            stmt = stmt.join(Client, Client.id == WhatsAppInboundMessage.client_id).where(
                Client.firm_id == current_user.firm_id
            )
        if status_filter is not None:
            stmt = stmt.where(WhatsAppInboundMessage.processing_status == status_filter)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt).all())
        return items, total

    # --- Quick-add client onboarding (NEXT-PROMPT.md step 2) -------------

    def send_document_checklist_request(self, to_phone: str, client_name: str) -> None:
        """The first message a quick-added client gets — lists the fixed
        checklist categories in plain language and asks them to reply with
        photos, one at a time. One outbound call, not one per category.
        Reuses WhatsAppBusinessAPISender.send_text (self.sender) — no second
        WhatsApp-sending path. No-ops with a log line when
        WHATSAPP_ACCESS_TOKEN/WHATSAPP_PHONE_NUMBER_ID are unset, same as
        every other call through self.sender in this module.
        """
        items = ", ".join(_CHECKLIST_LABELS[c] for c in CHECKLIST_CATEGORIES)
        body = (
            f"Hi {client_name}, please reply here with photos of: {items} — "
            "send them one at a time and we'll confirm each."
        )
        self.sender.send_text(to_phone, body)

    # --- Meta's GET verification handshake ------------------------------

    def verify_webhook_challenge(
        self, mode: str | None, verify_token: str | None, challenge: str | None
    ) -> str:
        """Meta calls GET with hub.mode=subscribe, hub.verify_token=<what you
        configured in the App Dashboard>, hub.challenge=<random string it
        expects echoed back>. WHATSAPP_VERIFY_TOKEN is a value *we* choose
        (not something Meta issues) — it just has to match on both sides."""
        if (
            mode == "subscribe"
            and settings.WHATSAPP_VERIFY_TOKEN
            and verify_token == settings.WHATSAPP_VERIFY_TOKEN
            and challenge is not None
        ):
            return challenge
        raise WhatsAppWebhookVerificationError("hub.mode/hub.verify_token mismatch")

    # --- Phone <-> Client matching --------------------------------------

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Keeps only digits, then the last 10 — matches numbers regardless of
        a leading country code (+91, 0091, or none), since WhatsApp always
        sends E.164 (e.g. 919876543210) but `User.phone` may have been
        entered by staff in any local format. Indian mobile numbers are
        always 10 digits, which is why 10 is the fixed window rather than a
        config value — this is an India-first product per STRATEGY_REVIEW.md
        Phase 6, not a general-purpose phone normalizer."""
        digits = re.sub(r"\D", "", phone or "")
        return digits[-10:] if len(digits) >= 10 else digits

    def match_client(self, from_phone: str) -> Client | None:
        """Matches an inbound WhatsApp sender to a Client two ways, per
        NEXT-PROMPT.md step 3:
          1. Directly against Client.phone (quick-added clients — see
             app/api/v1/endpoints/clients.py's quick-add endpoint, the
             only writer of this column, always stored pre-normalized).
          2. The original join through User.phone (already-portal-
             registered clients whose phone happens to be set on their
             User row) — kept exactly as it was, not removed, so any
             match that worked before this change keeps working.
        Both are tried and the results de-duplicated by Client.id rather
        than short-circuiting on the first match, so a client who somehow
        matches both ways still counts as one unambiguous match, not two.
        """
        normalized = self.normalize_phone(from_phone)
        if not normalized:
            return None

        direct_matches = list(
            self.db.scalars(select(Client).where(Client.phone == normalized)).all()
        )
        user_join_matches = list(
            self.db.scalars(
                select(Client)
                .join(User, User.id == Client.user_id)
                .where(User.phone.isnot(None))
                .where(User.phone.like(f"%{normalized}"))
            ).all()
        )
        matches = list({c.id: c for c in direct_matches + user_join_matches}.values())

        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Two clients whose stored phone numbers share the same last-10
            # digits (extremely unlikely for real mobile numbers, but
            # possible with bad test/seed data) — refuse to guess.
            logger.warning(
                f"[whatsapp] phone match ambiguous for {from_phone!r} ({len(matches)} clients matched)"
            )
            return None
        return None

    # --- Webhook processing ----------------------------------------------

    def process_webhook_payload(
        self, payload: dict, background_tasks: BackgroundTasks | None = None
    ) -> list[WhatsAppInboundMessage]:
        """Parses Meta's Cloud API shape:
        {"entry": [{"changes": [{"value": {"messages": [...]}}]}]}
        Status-callback payloads (delivered/read receipts) and payloads with
        no `messages` key are valid Meta deliveries too — silently skipped,
        not an error.
        """
        results: list[WhatsAppInboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    results.append(self._process_single_message(msg, background_tasks))
        return results

    def _process_single_message(
        self, msg: dict, background_tasks: BackgroundTasks | None = None
    ) -> WhatsAppInboundMessage:
        wa_message_id = msg.get("id", "")

        existing = self.db.scalar(
            select(WhatsAppInboundMessage).where(
                WhatsAppInboundMessage.wa_message_id == wa_message_id
            )
        )
        if existing is not None:
            # Meta retries webhook deliveries on anything but a fast 200 —
            # idempotent no-op, not a duplicate document.
            return existing

        raw_type = msg.get("type", "unknown")
        try:
            message_type = WhatsAppMessageType(raw_type)
        except ValueError:
            message_type = WhatsAppMessageType.UNKNOWN

        from_phone = msg.get("from", "")
        record = WhatsAppInboundMessage(
            wa_message_id=wa_message_id,
            from_phone=from_phone,
            message_type=message_type,
            processing_status=WhatsAppProcessingStatus.RECEIVED,
            raw_payload=msg,
        )

        client = self.match_client(from_phone)
        if client is None:
            record.processing_status = WhatsAppProcessingStatus.UNMATCHED
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record

        record.client_id = client.id

        if message_type in _MEDIA_TYPES:
            self._handle_media_message(record, msg, message_type, client, background_tasks)
        elif message_type == WhatsAppMessageType.TEXT:
            self._handle_text_message(record, msg, client)
        else:
            record.processing_status = WhatsAppProcessingStatus.ACKNOWLEDGED

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _handle_text_message(self, record: WhatsAppInboundMessage, msg: dict, client: Client) -> None:
        # v1: acknowledge only. A future pass could interpret text replies as
        # answers to a checklist prompt (e.g. "which document is this for?")
        # once the outbound checklist-request flow (§2e's reminder dispatch)
        # exists to prompt for that in the first place.
        self.sender.send_text(
            record.from_phone,
            "Thanks! If you're sending a document, please attach it as a photo or file.",
        )
        record.processing_status = WhatsAppProcessingStatus.ACKNOWLEDGED

    def _handle_media_message(
        self,
        record: WhatsAppInboundMessage,
        msg: dict,
        message_type: WhatsAppMessageType,
        client: Client,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        media_obj = msg.get(message_type.value, {})
        media_id = media_obj.get("id")
        if not media_id:
            record.processing_status = WhatsAppProcessingStatus.ERROR
            record.error_detail = f"no {message_type.value}.id in payload"
            return

        try:
            media_bytes, mime_type = self.sender.download_media(media_id)
        except WhatsAppNotConfiguredError as exc:
            # Expected gap until real credentials exist — log plainly, don't
            # crash the webhook (Meta expects a fast 200 regardless).
            record.processing_status = WhatsAppProcessingStatus.ERROR
            record.error_detail = str(exc)
            logger.info(f"[whatsapp] media download skipped (not configured): {exc}")
            return
        except Exception as exc:  # pragma: no cover - real Graph API failure
            record.processing_status = WhatsAppProcessingStatus.ERROR
            record.error_detail = f"media download failed: {exc}"
            logger.error(f"[whatsapp] media download failed for {media_id}: {exc}")
            return

        filename = media_obj.get("filename") or f"whatsapp-{message_type.value}-{media_id}"
        storage_key = storage_service.build_storage_key(client.id, filename)
        storage_service.upload_bytes(storage_key, media_bytes, mime_type)

        client_user = self.db.get(User, client.user_id)
        if client_user is None:
            record.processing_status = WhatsAppProcessingStatus.ERROR
            record.error_detail = f"client {client.id} has no linked user (data integrity issue)"
            return

        document_payload = DocumentCreate(
            client_id=client.id,
            category=DocumentCategory.OTHER,
            storage_key=storage_key,
            original_filename=filename,
            mime_type=mime_type,
            file_size_bytes=len(media_bytes),
        )
        # Reuses DocumentService.register_document wholesale — same RBAC,
        # checklist sync, OCR enqueue, and accountant-notification behavior
        # a browser-based client upload gets. "Acting as this client's own
        # user" is exactly what passing `client_user` as `current_user` does.
        document = DocumentService(self.db).register_document(
            client_user, document_payload, background_tasks
        )

        record.created_document_id = document.id
        record.processing_status = WhatsAppProcessingStatus.DOCUMENT_CREATED

        self.sender.send_text(
            record.from_phone,
            f"Got it — we've received \"{filename}\" and it's on its way to your accountant for review.",
        )

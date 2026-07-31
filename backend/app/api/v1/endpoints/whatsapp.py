"""
WhatsApp webhook — deliberately unauthenticated (Meta calls this directly,
there's no user token to check), but not unauthenticatable: the GET
handshake requires knowing WHATSAPP_VERIFY_TOKEN, and the POST endpoint
verifies the `X-Hub-Signature-256` header against WHATSAPP_APP_SECRET (see
whatsapp_service.verify_signature) — strictly enforced once that secret is
set, and a loud no-op with a warning until it is (no real Meta App exists
yet to get one from — see NEXT-PROMPT.md).
"""
import logging

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.whatsapp import WhatsAppInboundMessageRead, WhatsAppWebhookProcessResult
from app.services.whatsapp_service import (
    WhatsAppService,
    WhatsAppSignatureVerificationError,
    WhatsAppWebhookVerificationError,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.get("", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """One-time handshake Meta performs when you register/change the webhook
    URL in the App Dashboard. Must echo back hub.challenge as plain text with
    a 200, or Meta refuses to save the webhook config."""
    try:
        challenge = WhatsAppService(db).verify_webhook_challenge(
            hub_mode, hub_verify_token, hub_challenge
        )
    except WhatsAppWebhookVerificationError:
        return PlainTextResponse("verification failed", status_code=403)
    return PlainTextResponse(challenge, status_code=200)


@router.post("", response_model=WhatsAppWebhookProcessResult)
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    """
    Every actual inbound message/status-callback delivery from Meta lands
    here. Always returns 200 (even on a processing error for an individual
    message) — Meta interprets non-200 as "retry," and retrying a payload
    that failed for a reason that won't change on retry (e.g. an unmatched
    phone number) just wastes webhook deliveries. Errors are recorded on the
    WhatsAppInboundMessage row instead (see whatsapp_service.py), not raised.

    Signature verification is the one exception to "always 200": a
    mis-signed request is rejected outright with 403, before any payload
    parsing or processing happens — see whatsapp_service.verify_signature.
    While WHATSAPP_APP_SECRET is unset (no real Meta App exists yet — see
    NEXT-PROMPT.md), this is a no-op that logs a warning per request rather
    than rejecting everything, matching the rest of this module's
    unconfigured-is-a-no-op pattern.
    """
    raw_body = await request.body()
    try:
        verify_signature(raw_body, x_hub_signature_256)
    except WhatsAppSignatureVerificationError:
        logger.warning("[whatsapp] rejected webhook POST: signature verification failed")
        return PlainTextResponse("signature verification failed", status_code=403)

    payload = await request.json()
    try:
        processed = WhatsAppService(db).process_webhook_payload(payload)
    except Exception:
        # Still return 200 — see docstring. Log loudly since this means a
        # bug in our own parsing, not an expected per-message failure.
        logger.exception("[whatsapp] unhandled error processing webhook payload")
        return WhatsAppWebhookProcessResult(processed=[])
    return WhatsAppWebhookProcessResult(
        processed=[WhatsAppInboundMessageRead.model_validate(m) for m in processed]
    )

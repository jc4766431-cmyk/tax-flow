"""
Schemas for the WhatsApp module. Note the webhook body itself (Meta's Cloud
API "entry -> changes -> value -> messages[]" shape) is intentionally typed
as a plain `dict` at the endpoint layer, not parsed into a strict Pydantic
model — Meta's webhook payloads carry several optional/variant shapes
(status callbacks, different message types) and being lenient at the
boundary, then defensively reading only the fields we need in
`whatsapp_service.py`, is safer than a strict schema that 422s on a shape we
haven't seen yet. `WhatsAppInboundMessageRead` below is what we expose back
out of *our own* API (e.g. for a future admin "message log" view), not what
we accept from Meta.
"""
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.whatsapp import WhatsAppMessageType, WhatsAppProcessingStatus


class WhatsAppInboundMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wa_message_id: str
    from_phone: str
    message_type: WhatsAppMessageType
    processing_status: WhatsAppProcessingStatus
    client_id: uuid.UUID | None
    created_document_id: uuid.UUID | None
    error_detail: str | None


class WhatsAppWebhookProcessResult(BaseModel):
    """Returned to Meta's webhook caller — Meta doesn't parse this, but it's
    useful for `verify_webhook_flow.py`-style manual verification."""

    processed: list[WhatsAppInboundMessageRead]

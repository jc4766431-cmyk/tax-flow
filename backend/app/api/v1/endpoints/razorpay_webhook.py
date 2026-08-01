"""
Inbound Razorpay webhook — the other half of the payment flow started by
BillingService.create_subscription/upgrade_subscription and
InvoiceService.create_payment_order. See app/services/razorpay_service.py
for signature verification and app/services/billing_service.py /
app/services/invoice_service.py for what happens once a payment is
confirmed.

Public, unauthenticated (no user session — Razorpay is calling this, not a
logged-in browser), same as app/api/v1/endpoints/whatsapp.py's inbound
webhook. Trust comes entirely from the signature check, which must run
against the exact raw request body, not a re-serialized dict.
"""
import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.billing_service import SubscriptionService
from app.services.invoice_service import InvoiceService
from app.services.razorpay_service import RazorpayWebhookVerificationError, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/razorpay", tags=["webhooks"])


@router.post("")
async def receive_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
):
    raw_body = await request.body()

    try:
        verify_webhook_signature(raw_body, x_razorpay_signature)
    except RazorpayWebhookVerificationError as exc:
        logger.warning(f"[razorpay_webhook] rejected: {exc}")
        # Deliberately vague response body — don't tell a would-be attacker
        # *why* verification failed (same reasoning as whatsapp.py's webhook
        # rejecting on bad signatures without detail).
        return {"status": "rejected"}

    payload = await request.json()
    event = payload.get("event", "")

    # Razorpay's payload shape nests the actual entity under
    # payload.payment.entity (for payment.* events) or payload.order.entity
    # (for order.paid) — order_id is present on the payment entity either
    # way, which is the id BillingService/InvoiceService stored when they
    # created the order, so that's what this looks up against.
    if event in ("payment.captured", "order.paid"):
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not order_id or not payment_id:
            logger.warning(f"[razorpay_webhook] {event} payload missing order_id/payment_id")
            return {"status": "ignored", "reason": "missing order_id or payment_id"}

        subscription = SubscriptionService(db).mark_active_from_webhook(order_id, payment_id)
        if subscription is not None:
            logger.info(f"[razorpay_webhook] subscription {subscription.id} activated via {event}")
            return {"status": "ok", "matched": "subscription"}

        invoice = InvoiceService(db).mark_paid_from_webhook(order_id, payment_id)
        if invoice is not None:
            logger.info(f"[razorpay_webhook] invoice {invoice.id} marked paid via {event}")
            return {"status": "ok", "matched": "invoice"}

        logger.warning(f"[razorpay_webhook] {event} for order {order_id} matched no subscription or invoice")
        return {"status": "ignored", "reason": "no matching subscription or invoice"}

    # Every other event type (refund.*, payment.failed, etc.) is
    # acknowledged but not acted on yet — deliberately narrow scope for
    # this pass. Still return 200 so Razorpay doesn't retry indefinitely.
    return {"status": "ignored", "reason": f"unhandled event type: {event}"}

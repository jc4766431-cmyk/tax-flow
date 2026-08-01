"""
Razorpay integration: creating Orders (the unit of payment Razorpay's
Checkout works against) and verifying webhook signatures. Used by both
billing_service.py (the firm's own TaxFlow subscription) and
invoice_service.py (the firm billing its own clients) — see each module's
docstring for why they're distinct billing concepts that both happen to
use the same gateway.

Calls Razorpay's REST API directly over `httpx` (Basic Auth with
key_id/key_secret) rather than the `razorpay` Python SDK, same reasoning as
WhatsAppBusinessAPISender/SMSSender in notification_channels.py not pulling
in a provider SDK for a small, well-documented REST surface.

Unlike the notification channel senders (email/SMS/WhatsApp), this does
NOT no-op when unconfigured. A missing notification is a minor, recoverable
gap; a payment order silently not being created (or a webhook silently not
being verified) is a correctness/security bug. `RazorpayNotConfiguredError`
is raised loudly instead, the same way
WhatsAppBusinessAPISender.download_media raises rather than fabricating
success when credentials are missing.

Amounts throughout this module are in INR rupees (matching
Plan.price_per_seat_inr / Invoice.total_amount's existing Numeric(_, 2)
columns) and are converted to paise (the smallest currency sub-unit
Razorpay's API expects) only at the API-call boundary — see `_to_paise`.
"""
import hashlib
import hmac
import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_ORDERS_URL = "https://api.razorpay.com/v1/orders"


class RazorpayNotConfiguredError(RuntimeError):
    """Raised when a Razorpay API call is attempted without
    RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET configured. Distinguished from other
    RuntimeErrors so callers can log it as an expected/known limitation
    (no real Razorpay account exists yet for this project) rather than an
    unexpected bug."""


class RazorpayWebhookVerificationError(Exception):
    """Raised when the `X-Razorpay-Signature` header on an inbound webhook
    POST doesn't match the HMAC-SHA256 of the raw body, keyed with
    RAZORPAY_WEBHOOK_SECRET."""


def _to_paise(amount_inr: float) -> int:
    """Razorpay's Orders API takes amount in the smallest currency
    sub-unit — paise for INR (100 paise = ₹1), always an integer."""
    return round(amount_inr * 100)


class RazorpayService:
    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.configured = bool(self.key_id and self.key_secret)

    def create_order(
        self, amount_inr: float, *, receipt: str | None = None, notes: dict | None = None
    ) -> dict:
        """Creates a Razorpay Order for `amount_inr` rupees and returns the
        raw Order object (id, amount, currency, status, ...) — the
        `id` is what gets stored as the pending payment reference
        (Subscription.payment_gateway_ref / Invoice.razorpay_order_id) until
        a webhook confirms payment against it.

        `receipt` is Razorpay's own optional internal-reference field (max
        40 chars, must be unique) — defaults to a fresh uuid4 if not given.
        """
        if not self.configured:
            raise RazorpayNotConfiguredError(
                "Cannot create a Razorpay order: RAZORPAY_KEY_ID / "
                "RAZORPAY_KEY_SECRET are not set. This is an expected gap "
                "until a real Razorpay account exists for this project (see "
                "HANDOFF.md) — not a bug to silently work around."
            )
        payload = {
            "amount": _to_paise(amount_inr),
            "currency": "INR",
            "receipt": (receipt or str(uuid.uuid4()))[:40],
        }
        if notes:
            payload["notes"] = notes

        resp = httpx.post(
            _ORDERS_URL,
            auth=(self.key_id, self.key_secret),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


razorpay_service = RazorpayService()


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> None:
    """Verifies Razorpay's `X-Razorpay-Signature` header against the raw
    (unparsed) request body, keyed with RAZORPAY_WEBHOOK_SECRET. Deliberately
    takes raw bytes rather than a re-serialized dict, same reasoning as
    whatsapp_service.verify_signature: HMAC verification must run over the
    exact bytes Razorpay signed.

    Unlike whatsapp_service.verify_signature (which no-ops with a warning
    when its secret is unset, since a missing Meta App Secret just means
    inbound WhatsApp messages are trusted-by-default in a low-stakes way),
    a missing RAZORPAY_WEBHOOK_SECRET here raises rather than no-ops —
    an unverified payment webhook is a direct path to marking something
    paid that never was, which is a correctness/fraud risk, not a
    convenience gap.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise RazorpayWebhookVerificationError(
            "RAZORPAY_WEBHOOK_SECRET is not set — refusing to trust an "
            "unverified Razorpay webhook. Set this before exposing the "
            "webhook endpoint on a real public URL."
        )
    if not signature_header:
        raise RazorpayWebhookVerificationError("missing X-Razorpay-Signature header")

    expected_digest = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    # Constant-time comparison — a naive `==` here would reintroduce a timing
    # side-channel, defeating the point of verifying the signature at all
    # (same reasoning as whatsapp_service.verify_signature).
    if not hmac.compare_digest(signature_header, expected_digest):
        raise RazorpayWebhookVerificationError("signature mismatch")

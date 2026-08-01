"""
NotificationChannelSender: one interface, one implementation per delivery
channel, so `whatsapp_service.py` (and eventually `automation.py`'s reminder
dispatch, §2e) can send a message without knowing or caring which provider is
behind it. Today there's exactly one implementation (WhatsApp); email/SMS
senders belong here too once §2e is built — don't scatter provider-specific
code into callers.

This is a minimal version of the interface built specifically for the
WhatsApp module, per NEXT-PROMPT.md's note that a full generalization belongs
with §2e's Notifications/Automation work later.
"""
import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationChannelSender(ABC):
    @abstractmethod
    def send_text(self, to: str, body: str) -> None:
        """Send a plain-text message to `to` (channel-specific address format,
        e.g. E.164 phone number for WhatsApp)."""
        raise NotImplementedError


class WhatsAppBusinessAPISender(NotificationChannelSender):
    """
    Sends/receives via Meta's WhatsApp Cloud API (the Business API, not a
    Twilio wrapper — Twilio is a plausible alternative front-end but Meta's
    Cloud API is what this implementation targets, since it's what
    `WHATSAPP_GRAPH_API_VERSION` in config.py already implies).

    No real Meta App / WhatsApp Business Account exists for this project yet
    (see HANDOFF.md/NEXT-PROMPT.md) — `WHATSAPP_ACCESS_TOKEN` and
    `WHATSAPP_PHONE_NUMBER_ID` are unset in every environment this has been
    run in so far. Until they're set:
      - `send_text` is a no-op that logs what *would* have been sent, exactly
        like `storage_service.py`'s local-dev S3 credential fallback.
      - `download_media` raises `WhatsAppNotConfiguredError` rather than
        silently returning fake bytes — a missing document is a visible,
        debuggable failure; a fabricated one is not.

    Once real credentials are set in `.env`, both methods start actually
    calling `graph.facebook.com` — no other code changes needed.
    """

    def __init__(self) -> None:
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_version = settings.WHATSAPP_GRAPH_API_VERSION
        self.configured = bool(self.access_token and self.phone_number_id)

    @property
    def _base_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    def send_text(self, to: str, body: str) -> None:
        if not self.configured:
            logger.info(f"[whatsapp:noop, not configured] would send to {to}: {body!r}")
            return
        url = f"{self._base_url}/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Best-effort: a failed outbound confirmation shouldn't crash the
            # inbound-processing pipeline that triggered it (the document is
            # already saved by the time this is called).
            logger.error(f"[whatsapp:send_text failed] to={to}: {exc}")

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """
        Two-step Graph API media fetch: (1) resolve `media_id` to a short-lived
        CDN URL + mime type, (2) fetch the actual bytes from that URL, both
        authenticated with the same access token. Returns (bytes, mime_type).
        """
        if not self.configured:
            raise WhatsAppNotConfiguredError(
                "Cannot download WhatsApp media: WHATSAPP_ACCESS_TOKEN / "
                "WHATSAPP_PHONE_NUMBER_ID are not set. This is an expected gap "
                "until real Meta WhatsApp Business API credentials exist for "
                "this project (see HANDOFF.md) — not a bug to silently work "
                "around."
            )
        headers = {"Authorization": f"Bearer {self.access_token}"}
        meta_resp = httpx.get(f"{self._base_url}/{media_id}", headers=headers, timeout=10)
        meta_resp.raise_for_status()
        media_info = meta_resp.json()

        media_resp = httpx.get(media_info["url"], headers=headers, timeout=30)
        media_resp.raise_for_status()
        return media_resp.content, media_info.get("mime_type", "application/octet-stream")


class EmailSender(NotificationChannelSender):
    """
    Resend-API-based implementation of NotificationChannelSender — the first
    piece of §2e's "generalize to email/SMS" work. Calls Resend's HTTP API
    directly over `httpx` (POST https://api.resend.com/emails, Bearer auth),
    same reasoning as WhatsAppBusinessAPISender/SMSSender not pulling in a
    provider SDK. Mirrors their configured/no-op split: with no
    RESEND_API_KEY set, `send_text` just logs what would have been sent
    instead of raising, so callers (automation.py's reminder dispatch) can
    send through this channel unconditionally in every environment.

    `to` is an email address here rather than a phone number — channel
    callers already branch on delivery channel, so this doesn't change
    the shared interface, just its meaning.
    """

    _API_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        self.api_key = settings.RESEND_API_KEY
        self.configured = bool(self.api_key)

    def send_text(self, to: str, body: str) -> None:
        if not self.configured:
            logger.info(f"[email:noop, not configured] would send to {to}: {body!r}")
            return

        payload = {
            "from": settings.EMAIL_FROM_ADDRESS,
            "to": [to],
            "subject": "TaxFlow notification",
            "text": body,
        }
        try:
            resp = httpx.post(
                self._API_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Best-effort, same reasoning as WhatsAppBusinessAPISender.send_text:
            # a failed notification shouldn't crash the flow that triggered it.
            logger.error(f"[email:send_text failed] to={to}: {exc}")


class SMSSender(NotificationChannelSender):
    """
    Twilio-based implementation of NotificationChannelSender — the second
    piece of §2e's "generalize to email/SMS" work (after EmailSender).
    Mirrors the same configured/no-op split: with no TWILIO_ACCOUNT_SID set,
    `send_text` just logs what would have been sent, so callers (automation.py's
    reminder dispatch, once built) can send through this channel
    unconditionally in every environment.

    Calls Twilio's REST API directly over `httpx` (Basic Auth with
    account SID / auth token) rather than pulling in the `twilio` SDK, same
    reasoning as WhatsAppBusinessAPISender not using a wrapper library.

    `to` is an E.164 phone number here, same format as WhatsApp's `to`.
    """

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        self.configured = bool(self.account_sid and self.auth_token and self.from_number)

    def send_text(self, to: str, body: str) -> None:
        if not self.configured:
            logger.info(f"[sms:noop, not configured] would send to {to}: {body!r}")
            return
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        try:
            resp = httpx.post(
                url,
                auth=(self.account_sid, self.auth_token),
                data={"From": self.from_number, "To": to, "Body": body},
                timeout=10,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Best-effort, same reasoning as the other two senders: a failed
            # notification shouldn't crash the flow that triggered it.
            logger.error(f"[sms:send_text failed] to={to}: {exc}")


class WhatsAppNotConfiguredError(RuntimeError):
    """Raised when a real Meta WhatsApp Business API call is attempted without
    credentials configured. Distinguished from other RuntimeErrors so callers
    (whatsapp_service.py) can log it as an expected/known limitation rather
    than an unexpected bug."""

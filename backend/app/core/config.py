"""
Centralized, environment-based configuration.

All runtime configuration is read from environment variables (see .env.example).
Never hardcode secrets here.
"""
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "TaxFlow Platform API"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # Object storage — Cloudflare R2 (S3-compatible; see storage_service.py,
    # which is written generically against the S3 API and only uses
    # operations R2 supports: put_object/get_object + presigned PUT/GET).
    # S3_ENDPOINT_URL should be https://<account-id>.r2.cloudflarestorage.com
    # S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY come from an R2 API token
    # (Cloudflare dashboard -> R2 -> Manage API Tokens), not an AWS IAM user.
    # R2 doesn't use AWS regions — "auto" is R2's own convention and is what
    # boto3 should be given here, not a real AWS region name.
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET_NAME: str = "taxflow-documents"
    S3_REGION: str = "auto"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # WhatsApp Business API (Meta Cloud API shape) — see
    # app/services/notification_channels.py and app/api/v1/endpoints/whatsapp.py.
    # No real credentials exist for this project yet (see HANDOFF.md/NEXT-PROMPT.md).
    # WHATSAPP_VERIFY_TOKEN: arbitrary string you choose, used only for Meta's
    #   webhook-verification handshake (GET /webhooks/whatsapp?hub.verify_token=...).
    # WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID: from Meta's App Dashboard,
    #   needed to (a) call the Graph API to download inbound media and (b) send
    #   outbound replies/confirmations. Until these are set, inbound webhook
    #   *shape parsing* and phone-to-client matching still work (testable with a
    #   synthetic payload), but downloading real media and sending real replies
    #   are no-ops — see WhatsAppBusinessAPISender's docstring.
    WHATSAPP_VERIFY_TOKEN: str | None = None
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_GRAPH_API_VERSION: str = "v21.0"
    # App Secret from Meta's App Dashboard, used to verify the
    # `X-Hub-Signature-256` header on every inbound POST to
    # /webhooks/whatsapp (HMAC-SHA256 of the raw request body, keyed with
    # this secret). Until this is set, the webhook falls back to trusting
    # any POST body unsigned — see whatsapp_service.verify_signature and the
    # loud request-time warning it logs while unset. Set this before the
    # endpoint is ever exposed on a real public URL.
    WHATSAPP_APP_SECRET: str | None = None

    # Email channel (§2e generalization of NotificationChannelSender) — via
    # Resend's HTTP API rather than raw SMTP (smaller diff given no SMTP
    # provider was ever actually wired up, and one less protocol/credential
    # shape to manage, per the "minimize moving pieces" decision for this
    # deployment). RESEND_API_KEY unset => EmailSender falls back to a
    # no-op logger, same pattern as WhatsAppBusinessAPISender when its
    # credentials are unset.
    RESEND_API_KEY: str | None = None
    EMAIL_FROM_ADDRESS: str = "no-reply@taxflow.app"

    # SMS channel (§2e generalization of NotificationChannelSender, second
    # piece after EmailSender). Twilio, same reasoning as WhatsApp targeting
    # Meta's Cloud API directly — no wrapper SDK. Unset TWILIO_ACCOUNT_SID =>
    # SMSSender falls back to a no-op logger, same pattern as the other two
    # channel senders.
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None

    # OCR (§2e) — "tesseract" (local, pytesseract) or "google_document_ai"
    # (not yet implemented; falls back to tesseract if selected).
    OCR_PROVIDER: str = "tesseract"
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID: str | None = None
    # Documents above this size are skipped for auto-OCR (logged, not
    # crashed) rather than run on the same small free-tier instance that
    # also serves API requests — see app/worker/tasks.py.
    OCR_MAX_FILE_SIZE_MB: int = 5
    # Explicit ceiling passed to pdf2image.convert_from_bytes — deliberately
    # lower than its default, for the same reason as the size threshold
    # above (bounded memory/CPU on a 0.1 vCPU / 512MB instance).
    OCR_RENDER_DPI: int = 150

    # Razorpay — India-first payment gateway for both the firm's own
    # TaxFlow subscription billing (app/services/billing_service.py) and
    # the firm's client invoicing (app/services/invoice_service.py). Get
    # RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET from Settings -> API Keys in the
    # Razorpay dashboard (test mode keys start with rzp_test_), and
    # RAZORPAY_WEBHOOK_SECRET from Settings -> Webhooks when you add the
    # webhook URL there (this is a value *you* set when creating the
    # webhook, not one Razorpay generates for you). Unset =>
    # razorpay_service raises a clear, visible error on any call that would
    # need it (creating a payment order is not a best-effort notification
    # like the channel senders above — a missing gateway config here should
    # be a loud failure, not a silent no-op).
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    # Sentry — error monitoring, no-op if unset (see app/main.py).
    SENTRY_DSN: str | None = None

    # Shared-secret header required on GET /internal/tasks/heartbeat (see
    # app/api/v1/endpoints/internal.py) — this endpoint runs the scheduled
    # jobs that used to be a Celery beat schedule, so it must not be
    # publicly triggerable. Generate a long random string for this in every
    # real environment; there is no safe default.
    INTERNAL_TASK_SECRET: str | None = None


settings = Settings()

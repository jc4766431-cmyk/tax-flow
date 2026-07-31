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

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # Object storage
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET_NAME: str = "taxflow-documents"
    S3_REGION: str = "us-east-1"

    # Email
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = "noreply@taxflow.example"

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

    # Email channel (§2e generalization of NotificationChannelSender).
    # SMTP_HOST unset => EmailSender falls back to a no-op logger, same
    # pattern as WhatsAppBusinessAPISender when its credentials are unset.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
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


settings = Settings()

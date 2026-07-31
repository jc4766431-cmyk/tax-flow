"""
Thin wrapper around boto3 S3 client for presigned uploads/downloads.

Client uploads never proxy file bytes through FastAPI: the API only ever
hands out short-lived presigned URLs, and the browser talks to S3 directly.

Works against real AWS S3 (leave S3_ENDPOINT_URL unset) or any S3-compatible
store (MinIO, R2, etc. — set S3_ENDPOINT_URL) since nothing else is
configured for this project yet.
"""
import uuid
from datetime import datetime

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import settings

PRESIGNED_UPLOAD_EXPIRY_SECONDS = 15 * 60
PRESIGNED_DOWNLOAD_EXPIRY_SECONDS = 5 * 60


class StorageService:
    def __init__(self) -> None:
        # boto3 needs *some* key pair to compute a SigV4 signature even when
        # nothing is actually being uploaded to real AWS (e.g. local dev with
        # no S3-compatible backend configured yet). Falling back to
        # `aws_access_key_id=None` makes boto3 fall through to its default
        # credential chain (env vars, ~/.aws/credentials, instance metadata),
        # which finds nothing in this environment and raises
        # NoCredentialsError before it ever gets to signing anything.
        # These placeholder values are NOT real credentials and produce a
        # signature that will be rejected by real S3 — they only unblock
        # local development when S3_ACCESS_KEY_ID/S3_SECRET_ACCESS_KEY are
        # unset. Once real credentials (or a local MinIO, etc.) are
        # configured in .env, those take over automatically.
        access_key = settings.S3_ACCESS_KEY_ID or "local-dev-access-key"
        secret_key = settings.S3_SECRET_ACCESS_KEY or "local-dev-secret-key"
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=settings.S3_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )
        self._bucket = settings.S3_BUCKET_NAME

    def build_storage_key(self, client_id: uuid.UUID, original_filename: str) -> str:
        """
        Namespaced, collision-proof object key: clients/<client_id>/<date>/<uuid>-<filename>.
        Never trusts the original filename alone as a key (path traversal / collisions).
        """
        today = datetime.utcnow().strftime("%Y/%m/%d")
        safe_name = original_filename.replace("/", "_").replace("\\", "_")
        return f"clients/{client_id}/{today}/{uuid.uuid4()}-{safe_name}"

    def generate_presigned_upload(self, storage_key: str, content_type: str) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self._bucket,
                "Key": storage_key,
                "ContentType": content_type,
            },
            ExpiresIn=PRESIGNED_UPLOAD_EXPIRY_SECONDS,
        )

    def upload_bytes(self, storage_key: str, data: bytes, content_type: str) -> None:
        """
        Server-side upload — bytes go straight from this process to S3, no
        presigned URL/browser involved. Added for the WhatsApp module: inbound
        media is downloaded server-side from Meta's Graph API
        (WhatsAppBusinessAPISender.download_media) and needs to land in this
        project's own storage the same way a browser upload would, without a
        browser in the loop to hand a presigned PUT URL to.
        """
        self._client.put_object(
            Bucket=self._bucket, Key=storage_key, Body=data, ContentType=content_type
        )

    def download_bytes(self, storage_key: str) -> bytes:
        """Server-side fetch of an object's raw bytes. Added for the OCR
        pipeline (§2e), which needs the file content directly rather than a
        browser-facing presigned URL."""
        obj = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return obj["Body"].read()

    def generate_presigned_download(self, storage_key: str, filename: str | None = None) -> str:
        params = {"Bucket": self._bucket, "Key": storage_key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=PRESIGNED_DOWNLOAD_EXPIRY_SECONDS,
        )


storage_service = StorageService()

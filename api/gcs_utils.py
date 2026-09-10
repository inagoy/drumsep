"""Helpers to talk to Google Cloud Storage from Cloud Run without a service
account key file.

Cloud Run only gives us "ambient" credentials (an access token, no private
key), so `blob.generate_signed_url()` cannot sign locally. We work around
this with IAM self-impersonation: the runtime service account is granted
`roles/iam.serviceAccountTokenCreator` on itself, which lets it call the
IAM `signBlob` API to sign URLs on its own behalf.

See infra/README.md for the one-time IAM setup this depends on.
"""
import datetime
import os

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

BUCKET_NAME = os.environ["BUCKET_NAME"]

_storage_client = storage.Client()
_signing_credentials = None


def _get_signing_credentials():
    """Lazily build (and cache) credentials capable of signing URLs.

    Locally (e.g. `GOOGLE_APPLICATION_CREDENTIALS` pointing at a key file)
    the default credentials already know how to sign, so impersonation is
    skipped.
    """
    global _signing_credentials
    if _signing_credentials is not None:
        return _signing_credentials

    credentials, _ = google.auth.default()
    if hasattr(credentials, "sign_bytes"):
        # Local dev with a real service-account key file.
        _signing_credentials = credentials
        return _signing_credentials

    sa_email = os.environ.get("RUNTIME_SERVICE_ACCOUNT") or getattr(
        credentials, "service_account_email", None
    )
    if not sa_email or sa_email == "default":
        raise RuntimeError(
            "Cannot determine the runtime service account email for "
            "signing. Set RUNTIME_SERVICE_ACCOUNT explicitly."
        )

    _signing_credentials = impersonated_credentials.Credentials(
        source_credentials=credentials,
        target_principal=sa_email,
        target_scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        lifetime=3600,
    )
    return _signing_credentials


def bucket():
    return _storage_client.bucket(BUCKET_NAME)


def generate_upload_url(object_name: str, content_type: str, expires_minutes: int = 15) -> str:
    """V4 signed URL the browser can PUT the raw file to directly."""
    blob = bucket().blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expires_minutes),
        method="PUT",
        content_type=content_type,
        credentials=_get_signing_credentials(),
    )


def generate_download_url(object_name: str, expires_hours: int = 24) -> str:
    """V4 signed URL valid for `expires_hours` (default 24h, per spec)."""
    blob = bucket().blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=expires_hours),
        method="GET",
        credentials=_get_signing_credentials(),
    )


def download_to_file(object_name: str, destination_path: str) -> None:
    bucket().blob(object_name).download_to_filename(destination_path)


def upload_from_file(object_name: str, source_path: str) -> None:
    bucket().blob(object_name).upload_from_filename(source_path)


def blob_exists(object_name: str) -> bool:
    return bucket().blob(object_name).exists()

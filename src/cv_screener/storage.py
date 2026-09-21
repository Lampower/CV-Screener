"""S3-compatible object storage for generated photos and PDF resumes.

Backed by pgsty/minio (a community-maintained fork of MinIO — see
docker-compose.yml for why this isn't minio/minio), but only ever talked to
through the standard S3 API via boto3, so swapping in real AWS S3 or any
other S3-compatible service later is just an endpoint/credentials change,
not a code change.

Candidate JSON profiles stay on local disk (they're the source of truth
re-read by `indexing/build_index.py` and `agent/tools.py`); only the binary
photo/PDF assets live here. `CandidateProfile.photo_path` /
`.resume_pdf_path` store the *object key* (e.g. "photos/abc123.png"), not a
URL — use `presigned_url()` when a shareable link is actually needed.
"""

from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from cv_screener.config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_SECRET_KEY

PHOTOS_PREFIX = "photos/"
RESUMES_PREFIX = "resumes/"

_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",  # MinIO ignores this but boto3 requires a value
        )
    return _client


def check_connection() -> bool:
    """Quick liveness check used by the CLI to give a friendly error if the
    `storage` docker-compose service isn't up yet."""
    try:
        get_client().list_buckets()
        return True
    except Exception:
        return False


def ensure_bucket() -> None:
    client = get_client()
    try:
        client.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=S3_BUCKET)


def photo_key(candidate_id: str) -> str:
    return f"{PHOTOS_PREFIX}{candidate_id}.png"


def resume_key(candidate_id: str) -> str:
    return f"{RESUMES_PREFIX}{candidate_id}.pdf"


def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    """Uploads `data` under `key`, creating the bucket first if needed.
    Returns `key` unchanged, for chaining."""
    ensure_bucket()
    get_client().put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)
    return key


def download_bytes(key: str) -> bytes:
    obj = get_client().get_object(Bucket=S3_BUCKET, Key=key)
    return obj["Body"].read()


def object_exists(key: str) -> bool:
    try:
        get_client().head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def delete_object(key: str) -> None:
    get_client().delete_object(Bucket=S3_BUCKET, Key=key)


def presigned_url(key: str, expires_in: int = 3600) -> str:
    return get_client().generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": key}, ExpiresIn=expires_in
    )


def object_uri(key: str) -> str:
    """Human-readable reference for logs/CLI output (not a fetchable URL)."""
    return f"s3://{S3_BUCKET}/{key}"

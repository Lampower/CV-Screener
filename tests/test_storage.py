"""Tests for storage.py — key naming/formatting are pure functions, and the
boto3 client is mocked out for the rest, so nothing here needs a live
MinIO/S3 endpoint or an API key."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cv_screener import storage


def test_photo_key_and_resume_key_use_expected_prefixes() -> None:
    assert storage.photo_key("abc123") == "photos/abc123.png"
    assert storage.resume_key("abc123") == "resumes/abc123.pdf"


def test_object_uri_formats_as_s3_uri() -> None:
    assert storage.object_uri("photos/abc123.png") == "s3://cv-screener/photos/abc123.png"


def test_check_connection_true_when_client_succeeds() -> None:
    with patch("cv_screener.storage.get_client") as mock_get_client:
        mock_get_client.return_value.list_buckets.return_value = {"Buckets": []}
        assert storage.check_connection() is True


def test_check_connection_false_when_client_raises() -> None:
    with patch("cv_screener.storage.get_client") as mock_get_client:
        mock_get_client.return_value.list_buckets.side_effect = Exception("connection refused")
        assert storage.check_connection() is False


def test_upload_bytes_ensures_bucket_and_puts_object() -> None:
    mock_client = MagicMock()
    with patch("cv_screener.storage.get_client", return_value=mock_client), \
         patch("cv_screener.storage.ensure_bucket") as mock_ensure_bucket:
        key = storage.upload_bytes("photos/x.png", b"data", "image/png")

    mock_ensure_bucket.assert_called_once()
    mock_client.put_object.assert_called_once_with(
        Bucket=storage.S3_BUCKET, Key="photos/x.png", Body=b"data", ContentType="image/png"
    )
    assert key == "photos/x.png"

"""Tests for extract/s3_client.py using moto (in-memory S3).

Verifies the S3 wrapper (implicit auth + bucket/object operations)
behaviour without touching real AWS. moto fakes the entire S3 service.
"""

import botocore
import pytest

from config import settings
from extract import s3_client


def test_bucket_exists_true(s3_bucket):
    """Bucket created in the fixture -> must be True."""
    assert s3_client.bucket_exists() is True


def test_bucket_exists_false(s3_empty):
    """Without a bucket, head_bucket fails -> must be False, not an exception."""
    assert s3_client.bucket_exists() is False


def test_upload_test_object_upload_head_delete(s3_bucket):
    """upload_test_object must upload -> head (verify) -> delete.

    Proof: after the function returns, the object no longer exists.
    """
    key = s3_client.upload_test_object()
    assert key == "raw/_test/connectivity_check.txt"

    # head_object after delete must raise ClientError (object gone)
    with pytest.raises(botocore.exceptions.ClientError):
        s3_bucket.head_object(Bucket=settings.S3_BUCKET, Key=key)


def test_upload_bytes_preserves_full_body(s3_bucket):
    """upload_bytes must store the CSV content byte-for-byte."""
    key = "raw/transactions/year=2026/month=08/day=09/transactions_x.csv"
    s3_client.upload_bytes(key, "col1,col2\n1,a\n")

    obj = s3_bucket.get_object(Bucket=settings.S3_BUCKET, Key=key)
    assert obj["Body"].read().decode("utf-8") == "col1,col2\n1,a\n"
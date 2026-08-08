"""AWS S3 client wrapper for the raw data lake (Sprint 1)."""

import boto3
from botocore.exceptions import ClientError

from config import settings

TEST_PREFIX = "raw/_test"


def get_client():
    """Return a boto3 S3 client (credentials come from the environment)."""
    return boto3.client("s3", region_name=settings.S3_REGION)


def bucket_exists(client=None) -> bool:
    """Return True if the configured bucket is reachable with current credentials."""
    client = client or get_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        return True
    except ClientError:
        return False


def upload_test_object(client=None) -> str:
    """Upload a small test object, verify it with head_object, then delete it.

    Proves the full S3 write -> read -> delete path. Returns the object key.
    """
    client = client or get_client()
    key = f"{TEST_PREFIX}/connectivity_check.txt"
    client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=b"data-platform-connectivity-ok")
    client.head_object(Bucket=settings.S3_BUCKET, Key=key)  # raises ClientError if missing
    client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
    return key

def upload_bytes(key: str, body: str, client=None) -> None:
    """Upload a UTF-8 string as an S3 object (used by the generic extractor)."""
    client = client or get_client()
    client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=body.encode("utf-8"))
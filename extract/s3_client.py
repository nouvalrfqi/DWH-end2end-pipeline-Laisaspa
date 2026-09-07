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

def clear_prefix(prefix: str, client=None) -> int:
    """Delete every object under ``prefix`` (store-based pagination + batched delete).

    Keeps the raw/<table>/ prefix a single full snapshot so COPY INTO never
    loads accumulating batches. Returns the number of objects deleted.
    """
    client = client or get_client()
    paginator = client.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
        contents = page.get("Contents", [])
        if not contents:
            continue
        keys = [{"Key": obj["Key"]} for obj in contents]
        for i in range(0, len(keys), 1000):
            batch = keys[i:i + 1000]
            response = client.delete_objects(
                Bucket=settings.S3_BUCKET,
                Delete={"Objects": batch},
            )
            deleted += len(response.get("Deleted", []))
    return deleted


def upload_bytes(key: str, body: str, client=None) -> None:
    """Upload a UTF-8 string as an S3 object (used by the generic extractor)."""
    client = client or get_client()
    client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=body.encode("utf-8"))
"""Shared fixtures for the offline test suite.

Tests must not depend on .env: S3 settings are pinned and AWS is mocked
in-memory via moto.
"""

import boto3
import pytest
from moto import mock_aws

from config import settings


@pytest.fixture
def s3_settings(monkeypatch):
    """Pin S3 bucket and region so tests are independent of .env."""
    monkeypatch.setattr(settings, "S3_BUCKET", "spa-data-platform-dev")
    monkeypatch.setattr(settings, "S3_REGION", "ap-southeast-1")


@pytest.fixture
def s3_empty(s3_settings):
    """moto active with no bucket (bucket_exists=False path)."""
    with mock_aws():
        yield boto3.client("s3", region_name=settings.S3_REGION)


@pytest.fixture
def s3_bucket(s3_empty):
    """moto active with the bucket already created (upload/head/delete paths)."""
    s3_empty.create_bucket(
        Bucket=settings.S3_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": settings.S3_REGION},
    )
    yield s3_empty
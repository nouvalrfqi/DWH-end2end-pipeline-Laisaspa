"""Fixture bersama untuk suite Sprint 4.

Fixture = "peralatan" yang dipinjam test. Di sini ada dua jenis:
  1. settings S3 yang dipatok (test tidak boleh bergantung pada .env).
  2. AWS S3 tiruan di memori via moto (tanpa jaringan/akun asli).
"""

import boto3
import pytest
from moto import mock_aws

from config import settings


@pytest.fixture
def s3_settings(monkeypatch):
    """Pin S3_BUCKET / S3_REGION ke nilai tetap supaya test mandiri dari .env."""
    monkeypatch.setattr(settings, "S3_BUCKET", "spa-data-platform-dev")
    monkeypatch.setattr(settings, "S3_REGION", "ap-southeast-1")


@pytest.fixture
def s3_empty(s3_settings):
    """Moto aktif di memori, tapi bucket BELUM dibuat (untuk test bucket_exists=False)."""
    with mock_aws():
        yield boto3.client("s3", region_name=settings.S3_REGION)


@pytest.fixture
def s3_bucket(s3_empty):
    """Moto aktif + bucket sudah dibuat (untuk test upload, head, delete)."""
    s3_empty.create_bucket(
        Bucket=settings.S3_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": settings.S3_REGION},
    )
    yield s3_empty

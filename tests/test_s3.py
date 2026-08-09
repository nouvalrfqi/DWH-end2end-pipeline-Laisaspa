"""Test untuk extract/s3_client.py menggunakan moto (S3 tiruan di memori).

Goal: membuktikan wrapper S3 kita berfungsi (auth implicit + operasi
bucket/object) tanpa menyentuh AWS asli. moto memalsukan seluruh layanan S3.
"""

import botocore
import pytest

from config import settings
from extract import s3_client


def test_bucket_exists_true(s3_bucket):
    """Bucket dibuat di fixture -> harus True."""
    assert s3_client.bucket_exists() is True


def test_bucket_exists_false(s3_empty):
    """Bucket TIDAK dibuat -> head_bucket gagal -> harus False, bukan exception."""
    assert s3_client.bucket_exists() is False


def test_upload_test_object_upload_head_delete(s3_bucket):
    """upload_test_object harus: upload -> head (verifikasi) -> delete.

    Buktinya: setelah fungsi selesai, object sudah tidak ada lagi di S3 tiruan.
    """
    key = s3_client.upload_test_object()
    assert key == "raw/_test/connectivity_check.txt"

    # head_object setelah delete harus melempar ClientError (object tidak ada)
    with pytest.raises(botocore.exceptions.ClientError):
        s3_bucket.head_object(Bucket=settings.S3_BUCKET, Key=key)


def test_upload_bytes_menulis_body_utuh(s3_bucket):
    """upload_bytes harus menyimpan isi file CSV persis seperti aslinya."""
    key = "raw/transactions/year=2026/month=08/day=09/transactions_x.csv"
    s3_client.upload_bytes(key, "col1,col2\n1,a\n")

    obj = s3_bucket.get_object(Bucket=settings.S3_BUCKET, Key=key)
    assert obj["Body"].read().decode("utf-8") == "col1,col2\n1,a\n"

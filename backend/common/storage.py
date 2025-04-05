import re
import uuid
from pathlib import PurePosixPath
from typing import IO

import boto3
from botocore.client import BaseClient
from django.conf import settings

_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\-]+")


def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    )


def upload_file(file_obj: IO[bytes], workspace_id: int, original_filename: str) -> str:
    sanitized_name = _sanitize_filename(original_filename)
    s3_key = f"workspaces/{workspace_id}/{uuid.uuid4()}/{sanitized_name}"

    client = get_s3_client()
    client.upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        s3_key,
    )
    return s3_key


def delete_file(s3_key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)


def get_presigned_url(s3_key: str) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=settings.AWS_PRESIGNED_URL_EXPIRY,
    )


def download_file_bytes(s3_key: str) -> bytes:
    client = get_s3_client()
    response = client.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
    return response["Body"].read()


def _sanitize_filename(filename: str) -> str:
    # Strip any path component (defence against path traversal),
    # drop NULs and control characters, collapse anything weird to '_'.
    base = PurePosixPath(filename.replace("\\", "/")).name
    base = base.replace("\x00", "")
    base = _UNSAFE_FILENAME_CHARS.sub("_", base).strip("._") or "file"
    return base[:200]

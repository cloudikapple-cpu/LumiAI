"""Media utilities for downloading and processing files."""

import base64
import hashlib
from pathlib import Path
from typing import Any

import httpx


async def download_file(url: str, timeout: float = 60.0) -> bytes:
    """
    Download a file from URL.

    Args:
        url: URL to download from
        timeout: Download timeout in seconds

    Returns:
        File content as bytes
    """
    client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
    finally:
        await client.aclose()


async def download_to_storage(url: str, bucket: str, key: str) -> str:
    """
    Download a file and upload to object storage.

    Args:
        url: URL to download from
        bucket: Storage bucket name
        key: Storage key

    Returns:
        URL of the uploaded file
    """
    content = await download_file(url)

    try:
        import boto3
        from app.config import settings

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.storage.storage_endpoint,
            aws_access_key_id=settings.storage.storage_access_key,
            aws_secret_access_key=settings.storage.storage_secret_key,
            region_name=settings.storage.storage_region,
        )

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
        )

        if settings.storage.storage_public_url:
            return f"{settings.storage.storage_public_url}/{bucket}/{key}"

        return f"https://{bucket}.s3.{settings.storage.storage_region}.amazonaws.com/{key}"

    except Exception:
        return url


async def prepare_media_url(file_path: str, is_telegram: bool = True) -> str:
    """
    Prepare a media URL for processing.

    Args:
        file_path: File path or URL
        is_telegram: Whether this is from Telegram

    Returns:
        Prepared URL or base64 data URI
    """
    if file_path.startswith(("http://", "https://")):
        return file_path

    if file_path.startswith("data:"):
        return file_path

    if is_telegram and not file_path.startswith("/"):
        return file_path

    file_path_path = Path(file_path)
    if file_path_path.exists():
        content = file_path_path.read_bytes()
        ext = file_path_path.suffix.lower()

        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
        }

        content_type = content_types.get(ext, "application/octet-stream")
        b64_data = base64.b64encode(content).decode("utf-8")

        return f"data:{content_type};base64,{b64_data}"

    return file_path


def get_file_hash(data: bytes) -> str:
    """Get SHA256 hash of file data."""
    return hashlib.sha256(data).hexdigest()


def get_content_type(filename: str) -> str:
    """Get content type from filename."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "webp": "image/webp",
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "pdf": "application/pdf",
        "txt": "text/plain",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "wav": "audio/wav",
    }

    return content_types.get(ext, "application/octet-stream")
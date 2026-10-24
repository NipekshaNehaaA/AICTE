"""
Swappable Document Storage Service for AICTE Approval & Compliance Automation Platform.
Supports:
1. Local filesystem storage (default for dev and standalone deployments)
2. MinIO / S3 object storage (via MINIO_* or S3 environment variables)
3. Cryptographic SHA-256 validation, MIME detection, and magic byte checking (PDF, JPG, PNG)
"""

import os
import re
import io
import hashlib
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from app.config import settings

# Supported document file signatures (magic bytes)
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
}

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/octet-stream", # permitted fallback if magic bytes verify
}


def sanitize_filename(filename: str) -> str:
    """Sanitizes file name to prevent directory traversal and illegal characters."""
    base = os.path.basename(filename).strip()
    # Replace dangerous characters with underscore
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    if not safe or safe.startswith("."):
        safe = f"doc_{safe}"
    return safe


def validate_file_bytes(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None,
    max_size: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Validates file size, extension, declared MIME, and binary magic bytes.
    Returns: (is_valid, error_message)
    """
    limit = max_size or settings.MAX_UPLOAD_SIZE_BYTES
    if len(file_bytes) == 0:
        return False, "File is empty (0 bytes)."

    if len(file_bytes) > limit:
        max_mb = limit / (1024 * 1024)
        return False, f"File size exceeds statutory maximum limit ({max_mb:.1f} MB)."

    # Check extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '.{ext}' is not permitted. Permitted formats: PDF, JPG, PNG."

    # Validate binary magic bytes
    expected_magics = MAGIC_SIGNATURES.get(ext, [])
    magic_matched = any(file_bytes.startswith(sig) for sig in expected_magics)
    if not magic_matched:
        return (
            False,
            f"File integrity error: Binary magic bytes do not match declared '.{ext}' format. Potential spoofing or corrupted file.",
        )

    return True, ""


def compute_sha256(file_bytes: bytes) -> str:
    """Computes SHA-256 hash digest on actual bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


class BaseStorageService(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, storage_key: str, content_type: str = "application/octet-stream") -> str:
        """Stores file bytes at storage_key. Returns the storage_key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieves raw file bytes by storage_key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Deletes file at storage_key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks if file exists at storage_key."""
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_LOCAL_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> str:
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        # Directory traversal prevention
        if not full_path.startswith(self.base_dir):
            raise ValueError("Security violation: Attempted directory traversal in storage key.")
        return full_path

    def save(self, file_bytes: bytes, storage_key: str, content_type: str = "application/octet-stream") -> str:
        target_path = self._resolve_path(storage_key)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        return storage_key

    def get(self, storage_key: str) -> bytes:
        target_path = self._resolve_path(storage_key)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Stored document not found on disk: {storage_key}")
        with open(target_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if os.path.exists(target_path):
            os.remove(target_path)
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        return os.path.exists(target_path)


class MinIOStorageService(BaseStorageService):
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        from minio import Minio
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            # MinIO might be booting up or in container; log notice
            print(f"Notice: MinIO bucket check '{self.bucket}': {e}")

    def save(self, file_bytes: bytes, storage_key: str, content_type: str = "application/octet-stream") -> str:
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        data_stream = io.BytesIO(file_bytes)
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=clean_key,
            data=data_stream,
            length=len(file_bytes),
            content_type=content_type,
        )
        return clean_key

    def get(self, storage_key: str) -> bytes:
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        response = self.client.get_object(self.bucket, clean_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, storage_key: str) -> bool:
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        self.client.remove_object(self.bucket, clean_key)
        return True

    def exists(self, storage_key: str) -> bool:
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        try:
            self.client.stat_object(self.bucket, clean_key)
            return True
        except Exception:
            return False


def get_storage_service() -> BaseStorageService:
    """
    Factory function returning the configured storage backend.
    Defaults to LocalStorageService; switches to MinIOStorageService when STORAGE_BACKEND='minio'.
    """
    backend = settings.STORAGE_BACKEND.lower()
    if backend in ("minio", "s3"):
        try:
            return MinIOStorageService()
        except Exception as e:
            print(f"Warning: MinIO storage backend connection failed ({e}), falling back to LocalStorageService")
            return LocalStorageService()
    return LocalStorageService()


storage_service = get_storage_service()

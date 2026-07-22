"""Photo storage abstraction (§1.1).

STORAGE_BACKEND selects the concrete class: local disk in dev, Supabase
Storage for the free-tier demo deploy (DEPLOY.md). Video/link media never
touch this at all — they're stored as a plain URL directly on the media
row, no upload involved.
"""
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class StorageError(Exception):
    pass


class StorageBackend(ABC):
    @abstractmethod
    def save(self, *, filename: str, content: bytes, content_type: str) -> str:
        """Persist `content` and return a URL clients can fetch it from."""

    @abstractmethod
    def delete(self, url: str) -> None:
        """Best-effort removal; must not raise if the object is already gone."""


class LocalStorageBackend(StorageBackend):
    """Writes under MEDIA_LOCAL_DIR; served by the /media static mount
    registered in app/main.py."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, filename: str, content: bytes, content_type: str) -> str:
        key = f"{uuid.uuid4().hex}{Path(filename).suffix}"
        (self._base_dir / key).write_bytes(content)
        return f"/media/{key}"

    def delete(self, url: str) -> None:
        key = url.rsplit("/", 1)[-1]
        (self._base_dir / key).unlink(missing_ok=True)


class SupabaseStorageBackend(StorageBackend):
    """Uploads via Supabase Storage's REST API — the storage layer for the
    free-tier demo deploy (DEPLOY.md uses Supabase, not raw S3).

    TODO(confirm): not exercised by this repo's tests — there's no live
    Supabase project to upload against here. Verify against a real project
    before relying on this for the actual demo deploy.
    """

    def __init__(self, *, project_url: str, service_key: str, bucket: str) -> None:
        self._base = project_url.rstrip("/")
        self._service_key = service_key
        self._bucket = bucket

    def save(self, *, filename: str, content: bytes, content_type: str) -> str:
        import httpx

        key = f"{uuid.uuid4().hex}{Path(filename).suffix}"
        resp = httpx.post(
            f"{self._base}/storage/v1/object/{self._bucket}/{key}",
            headers={
                "Authorization": f"Bearer {self._service_key}",
                "Content-Type": content_type,
            },
            content=content,
            timeout=30,
        )
        if resp.status_code >= 400:
            raise StorageError(f"Supabase upload failed: {resp.status_code} {resp.text}")
        return f"{self._base}/storage/v1/object/public/{self._bucket}/{key}"

    def delete(self, url: str) -> None:
        import httpx

        key = url.rsplit(f"/{self._bucket}/", 1)[-1]
        httpx.delete(
            f"{self._base}/storage/v1/object/{self._bucket}/{key}",
            headers={"Authorization": f"Bearer {self._service_key}"},
            timeout=30,
        )


@lru_cache(maxsize=1)
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend(settings.MEDIA_LOCAL_DIR)
    if settings.STORAGE_BACKEND == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise StorageError(
                "SUPABASE_URL/SUPABASE_SERVICE_KEY must be set for STORAGE_BACKEND=supabase",
            )
        return SupabaseStorageBackend(
            project_url=settings.SUPABASE_URL,
            service_key=settings.SUPABASE_SERVICE_KEY,
            bucket=settings.SUPABASE_STORAGE_BUCKET,
        )
    if settings.STORAGE_BACKEND == "s3":
        # TODO(confirm): DEPLOY.md's actual free-tier path is Supabase
        # Storage, not a standalone S3 bucket — nothing to build or test
        # against here. Implement with boto3 if a league ever needs a
        # non-Supabase S3-compatible bucket.
        raise NotImplementedError("STORAGE_BACKEND=s3 is not implemented yet")
    raise StorageError(f"unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")

from functools import lru_cache

from app.core.config import settings
from app.modules.storage.base import StorageBackend
from app.modules.storage.local import LocalStorage
from app.modules.storage.minio import MinIOStorage


@lru_cache
def get_storage() -> StorageBackend:
    if settings.storage_backend == "minio":
        return MinIOStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
    return LocalStorage(settings.upload_dir)

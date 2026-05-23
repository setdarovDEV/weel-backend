from minio import Minio
from app.config import settings

minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket_exists():
    """Ensure the MinIO bucket exists."""
    if not minio_client.bucket_exists(settings.minio_bucket):
        minio_client.make_bucket(settings.minio_bucket)


def upload_file(object_name: str, file_data: bytes, content_type: str) -> str:
    """Upload file to MinIO and return URL."""
    from io import BytesIO
    ensure_bucket_exists()
    minio_client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return f"{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


def get_presigned_url(object_name: str, expires: int = 3600) -> str:
    """Get presigned URL for object download."""
    return minio_client.presigned_get_object(settings.minio_bucket, object_name, expires=expires)


def delete_file(object_name: str):
    """Delete file from MinIO."""
    minio_client.remove_object(settings.minio_bucket, object_name)

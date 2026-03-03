import os
import uuid
from typing import Tuple

from django.conf import settings
from minio import Minio
from minio.error import S3Error


class MinioStorageError(RuntimeError):
    pass


def _get_minio_client() -> Minio:
    if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
        raise MinioStorageError('MINIO_ACCESS_KEY e MINIO_SECRET_KEY são obrigatórios para upload de imagens.')

    return Minio(
        settings.MINIO_DOMAIN,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_image_to_minio(uploaded_file, user_id: int) -> Tuple[str, str, str]:
    client = _get_minio_client()
    bucket = settings.MINIO_IMAGES_BUCKET
    _ensure_bucket(client, bucket)

    original_name = getattr(uploaded_file, 'name', 'file')
    ext = os.path.splitext(original_name)[1].lower()
    extension = ext[1:] if ext.startswith('.') else ext

    object_name = f"images/{user_id}/{uuid.uuid4().hex}{ext}"

    content_type = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
    size = getattr(uploaded_file, 'size', None)
    if size is None:
        raise MinioStorageError('Não foi possível determinar o tamanho do arquivo para upload no MinIO.')

    file_obj = getattr(uploaded_file, 'file', uploaded_file)

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=file_obj,
            length=size,
            content_type=content_type,
        )
    except S3Error as exc:
        raise MinioStorageError(f'Falha ao enviar arquivo para MinIO: {exc}') from exc

    return object_name, content_type, extension


def get_image_from_minio(object_name: str):
    client = _get_minio_client()
    bucket = settings.MINIO_IMAGES_BUCKET
    try:
        return client.get_object(bucket, object_name)
    except S3Error as exc:
        raise MinioStorageError(f'Falha ao obter arquivo do MinIO: {exc}') from exc


def delete_image_from_minio(object_name: str) -> None:
    if not object_name:
        return

    client = _get_minio_client()
    bucket = settings.MINIO_IMAGES_BUCKET

    try:
        client.remove_object(bucket, object_name)
    except S3Error:
        pass

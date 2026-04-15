import os
import uuid
import hashlib
from io import BytesIO
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

def upload_consent_document_to_minio(
    uploaded_file, 
    consent_type: str, 
    version: str, 
    language: str
) -> Tuple[str, str, str]:
    """Upload documento de consentimento (PDF, HTML, etc) para MinIO.
    
    Valida:
    - Magic bytes (conteúdo real do arquivo)
    - Tamanho máximo (50MB)
    - Tipo MIME
    
    Retorna: (object_name, content_type, content_hash)
    """
    client = _get_minio_client()
    bucket = getattr(settings, 'MINIO_DOCUMENTS_BUCKET', 'documents')
    _ensure_bucket(client, bucket)

    original_name = getattr(uploaded_file, 'name', 'file')
    ext = os.path.splitext(original_name)[1].lower()
    
    # ✓ 1. VALIDAR EXTENSÃO
    valid_extensions = {'.pdf', '.html', '.htm'}
    if ext not in valid_extensions:
        raise MinioStorageError(
            f'Tipo de arquivo não permitido. Use: {", ".join(valid_extensions)}'
        )
    
    # ✓ 2. VALIDAR TAMANHO MÁXIMO (50 MB)
    MAX_SIZE = 50 * 1024 * 1024
    size = getattr(uploaded_file, 'size', None)
    if size is None or size > MAX_SIZE:
        raise MinioStorageError(
            f'Arquivo muito grande. Tamanho: {size} bytes. Máximo: {MAX_SIZE} bytes.'
        )
    
    # ✓ 3. VALIDAR MAGIC BYTES (conteúdo real do arquivo)
    file_obj = getattr(uploaded_file, 'file', uploaded_file)
    try:
        file_obj.seek(0)
    except (AttributeError, OSError):
        raise MinioStorageError('Arquivo não é seekable. Envie um arquivo válido.')
    header = file_obj.read(128).lstrip().upper()  # Ler até 128 bytes para ignorar espaços no início
    
    detected_mime = None
    if header.startswith(b'%PDF'):
        detected_mime = 'application/pdf'
    elif header.startswith(b'<!DOCTYPE') or header.startswith(b'<HTML') or header.startswith(b'<?XML'):
        detected_mime = 'text/html'
    
    if detected_mime is None:
        raise MinioStorageError(
            'Arquivo contém conteúdo inválido. '
            'PDF deve iniciar com "%PDF", '
            'HTML deve iniciar com "<!DOCTYPE", "<html" ou "<?xml"'
        )
    
    # ✓ 4. VALIDAR CORRESPONDÊNCIA ENTRE EXTENSÃO E CONTEÚDO
    if ext == '.pdf' and detected_mime != 'application/pdf':
        raise MinioStorageError(
            f'Extensão .pdf não corresponde ao conteúdo ({detected_mime})'
        )
    elif ext in ['.html', '.htm'] and detected_mime != 'text/html':
        raise MinioStorageError(
            f'Extensão {ext} não corresponde ao conteúdo ({detected_mime})'
        )

    # Caminho semântico: documents/{consent_type}/{version}/{language}/{uuid}.{ext}
    object_name = f"documents/{consent_type}/{version}/{language}/{uuid.uuid4().hex}{ext}"

    # Determinar content-type final
    content_type = detected_mime

    # ✓ 5. LER ARQUIVO COMPLETO E CALCULAR HASH
    file_obj.seek(0)
    file_content = file_obj.read()
    content_hash = hashlib.sha256(file_content).hexdigest()
    
    # ✓ 6. ENVIAR PARA MinIO
    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(file_content),
            length=len(file_content),
            content_type=content_type,
        )
    except S3Error as exc:
        raise MinioStorageError(f'Falha ao enviar documento para MinIO: {exc}') from exc

    return object_name, content_type, content_hash


def get_consent_document_presigned_url(object_name: str, expires_in_seconds: int = 86400) -> str:
    """Gera URL presignada temporal para download direto do MinIO.
    
    Args:
        object_name: Caminho do arquivo no MinIO
        expires_in_seconds: Tempo de validade em segundos (padrão: 24 horas)
    
    Returns:
        URL presignada válida
    """
    from datetime import timedelta
    
    client = _get_minio_client()
    bucket = getattr(settings, 'MINIO_DOCUMENTS_BUCKET', 'documents')
    
    try:
        url = client.get_presigned_url(
            method='GET',
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_in_seconds)
        )
        return url
    except S3Error as exc:
        raise MinioStorageError(f'Falha ao gerar presigned URL: {exc}') from exc


def delete_consent_document_from_minio(object_name: str) -> None:
    """Remove documento de consentimento do MinIO."""
    if not object_name:
        return

    client = _get_minio_client()
    bucket = getattr(settings, 'MINIO_DOCUMENTS_BUCKET', 'documents')

    try:
        client.remove_object(bucket, object_name)
    except S3Error:
        pass
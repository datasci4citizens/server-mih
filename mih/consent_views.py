from datetime import datetime
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import ConsentDocument


class ConsentDocumentListView(APIView):
    """GET /auth/consent-documents/ — Lista todos os documentos de consentimento ativos."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lista documentos de consentimento com suas informações de versão."""
        consent_type = request.query_params.get('type')  # opcional: filtrar por tipo
        language = request.query_params.get('language', 'pt-BR')
        
        now = timezone.now()
        query = ConsentDocument.objects.filter(is_active=True, language=language, effective_date__lte=now)
        if consent_type:
            query = query.filter(consent_type=consent_type)
        
        documents = query.order_by('-effective_date').values(
            'id',
            'consent_type',
            'version',
            'language',
            'content_hash',
            'effective_date',
            'created_at',
            'requires_reconsent',
            'changelog'
        )
        
        return Response({
            'documents': list(documents),
            'total': query.count(),
        })


class ConsentDocumentPresignedUrlView(APIView):
    """GET /auth/consent-documents/presigned-url/ — Gera URL presigned para download direto do MinIO."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retorna URL presignada para download do documento sem passar pelo Django."""
        consent_type = request.query_params.get('type')  # 'tcle' ou 'privacy_policy'
        language = request.query_params.get('language', 'pt-BR')
        doc_hash = request.query_params.get('hash')
        
        if not consent_type and not doc_hash:
            return Response(
                {'detail': 'Parâmetro "type" ou "hash" obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Buscar documento por hash ou trazer o ativo mais recente
            if doc_hash:
                doc = ConsentDocument.objects.filter(content_hash=doc_hash).first()
            else:
                doc = ConsentDocument.objects.filter(
                    consent_type=consent_type,
                    language=language,
                    is_active=True,
                    effective_date__lte=timezone.now()
                ).order_by('-effective_date').first()
            
            if not doc:
                return Response(
                    {'detail': 'Documento não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Gerar presigned URL (válida por 1 hora)
            from .minio_storage import get_consent_document_presigned_url
            presigned_url = get_consent_document_presigned_url(doc.file_path, expires_in_seconds=3600)
            
            return Response({
                'presigned_url': presigned_url,
                'document_id': doc.id,
                'document_type': doc.consent_type,
                'version': doc.version,
                'language': doc.language,
                'content_type': doc.content_type,
                'expires_in_seconds': 3600,
            })
        except Exception as e:
            return Response(
                {'detail': f'Erro ao gerar presigned URL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConsentDocumentUploadView(APIView):
    """POST /admin/consent-documents/upload/ — Upload de novo documento (admin)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Upload e versioning de documento de consentimento."""
        # Validar permissão (super_user ou staff)
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permissão negada. Apenas administradores podem fazer upload.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar campos obrigatórios
        consent_type = request.data.get('consent_type')
        version = request.data.get('version')
        language = request.data.get('language', 'pt-BR')
        file_upload = request.FILES.get('file')
        effective_date = request.data.get('effective_date')
        changelog = request.data.get('changelog', '')
        
        # Converte string "true"/"false" ou boolean original
        req_rec_raw = str(request.data.get('requires_reconsent', 'false')).lower()
        requires_reconsent = req_rec_raw in ('true', '1', 't', 'y', 'yes')
        
        if not all([consent_type, version, file_upload, effective_date]):
            return Response(
                {'detail': 'consent_type, version, file, e effective_date são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar consent_type
        valid_types = [t[0] for t in ConsentDocument._meta.get_field('consent_type').choices]
        if consent_type not in valid_types:
            return Response(
                {'detail': f'Tipo inválido. Opções: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .minio_storage import upload_consent_document_to_minio
            file_path, content_type, content_hash = upload_consent_document_to_minio(
                file_upload,
                consent_type,
                version,
                language
            )
        except Exception as e:
            return Response(
                {'detail': f'Erro ao fazer upload: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            try:
                effective_date_obj = datetime.fromisoformat(effective_date)
            except (ValueError, TypeError):
                from .minio_storage import delete_consent_document_from_minio
                delete_consent_document_from_minio(file_path)
                return Response(
                    {'detail': 'Formato de effective_date inválido. Use ISO format (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Desativar versão anterior do mesmo type/language se existir
                ConsentDocument.objects.filter(
                    consent_type=consent_type,
                    language=language,
                    is_active=True
                ).update(is_active=False)
                
                doc = ConsentDocument.objects.create(
                    consent_type=consent_type,
                    version=version,
                    language=language,
                    file_path=file_path,
                    content_type=content_type,
                    file_size=file_upload.size,
                    content_hash=content_hash,
                    effective_date=effective_date_obj,
                    is_active=True,
                    changelog=changelog,
                    requires_reconsent=requires_reconsent,
                )
            
            return Response({
                'id': doc.id,
                'consent_type': doc.consent_type,
                'version': doc.version,
                'language': doc.language,
                'content_hash': doc.content_hash,
                'content_type': doc.content_type,
                'file_size': doc.file_size,
                'effective_date': doc.effective_date.isoformat(),
                'message': 'Documento enviado com sucesso',
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            from .minio_storage import delete_consent_document_from_minio
            delete_consent_document_from_minio(file_path)
            
            return Response(
                {'detail': f'Erro ao criar documento: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

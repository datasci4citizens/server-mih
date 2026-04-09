from django.db import models
from django.conf import settings
from .omop_models import Person, Provider


class Image(models.Model):
    object_name = models.CharField(max_length=512, null=True, blank=True, db_index=True)
    content_type = models.CharField(max_length=128, null=True, blank=True)
    extension = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='images')

    def __str__(self):
        if self.extension:
            return f"Image {self.id}.{self.extension}"
        return f"Image {self.id}"


class UserProfile(models.Model):
    ROLE_RESPONSIBLE = 'responsible'
    ROLE_SPECIALIST = 'specialist'
    ROLE_CHOICES = (
        (ROLE_RESPONSIBLE, 'Responsible'),
        (ROLE_SPECIALIST, 'Specialist'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, null=True, blank=True)
    is_allowed = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    state = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    neighborhood = models.CharField(max_length=128, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserProfile {self.user_id} ({self.role})"


class PatientNonClinicalInfos(models.Model):
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name='non_clinical_infos')
    name = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PatientNonClinicalInfos {self.person_id}"


class ProviderNonClinicalInfos(models.Model):
    provider = models.OneToOneField(Provider, on_delete=models.CASCADE, related_name='non_clinical_infos')
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    is_allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ProviderNonClinicalInfos {self.provider_id}"


class ConsentDocument(models.Model):
    """Versões de documentos de consentimento com integridade verificável.
    
    Arquivos são armazenados em MinIO (PDF, HTML, etc).
    Este modelo armazena metadados + hash SHA-256 do arquivo.
    """
    consent_type = models.CharField(
        max_length=32,
        choices=(
            ('tcle', 'TCLE (Termo de Consentimento Livre e Esclarecido)'),
            ('privacy_policy', 'Privacy Policy'),
        ),
        db_index=True
    )
    version = models.CharField(max_length=32, db_index=True)  # semântico: 2.1.2, 1.0.0, etc
    language = models.CharField(
        max_length=10,
        choices=(
            ('pt-BR', 'Português (Brasil)'),
            ('en', 'English'),
        ),
        default='pt-BR'
    )
    
    # Armazenamento em MinIO
    file_path = models.CharField(max_length=512)  # caminho no MinIO
    content_type = models.CharField(max_length=64)  # application/pdf, text/html, etc
    file_size = models.BigIntegerField()  # tamanho em bytes
    
    # Integridade
    content_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256
    
    # Controle de versão
    effective_date = models.DateTimeField()  # quando esta versão entra em vigor
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Metadados
    is_active = models.BooleanField(default=True)  # se está em uso
    changelog = models.TextField(blank=True, null=True)  # o que mudou em relação à versão anterior

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consent_type', 'language', '-effective_date']),
            models.Index(fields=['content_hash']),
            models.Index(fields=['is_active', 'consent_type']),
        ]
        # Permite múltiplos idiomas/versões da mesma versão semântica
        unique_together = [('consent_type', 'version', 'language')]

    def __str__(self):
        return f"{self.get_consent_type_display()} v{self.version} ({self.language})"
    
    def delete(self, *args, **kwargs):
        """Remove arquivo do MinIO ao deletar documento."""
        from .minio_storage import delete_consent_document_from_minio
        if self.file_path:
            delete_consent_document_from_minio(self.file_path)
        super().delete(*args, **kwargs)


class ConsentManager(models.Manager):
    """Custom manager for Consent model."""
    
    def get_current_state(self, user):
        """Get current consent state for all types for a user with document info (optimized single query)."""
        from django.db.models import Max
        
        # Get latest consent ID for each consent_type in a single query
        latest_ids = self.filter(user=user).values('consent_type').annotate(
            latest_id=Max('id')
        ).values_list('latest_id', flat=True)
        
        # Fetch all latest consents with their related documents
        latest_consents = list(
            self.filter(id__in=latest_ids).select_related('document')
        )
        
        # Build state dict indexed by consent_type
        consents_by_type = {c.consent_type: c for c in latest_consents}
        
        state = {}
        for consent_type, _ in (('tcle', 'TCLE (Termo de Consentimento Livre e Esclarecido)'), ('privacy_policy', 'Privacy Policy')):
            latest = consents_by_type.get(consent_type)
            if latest:
                state[consent_type] = {
                    'accepted': latest.accepted,
                    'accepted_at': latest.created_at.isoformat(),
                    'ip_address': latest.ip_address,
                    'document_version': latest.document.version if latest.document else None,
                    'document_language': latest.document.language if latest.document else None,
                    'document_hash': latest.document.content_hash if latest.document else None,
                    'effective_date': latest.document.effective_date.isoformat() if latest.document else None,
                }
            else:
                state[consent_type] = {
                    'accepted': False,
                    'accepted_at': None,
                    'ip_address': None,
                    'document_version': None,
                    'document_language': None,
                    'document_hash': None,
                    'effective_date': None,
                }
        return state


class Consent(models.Model):
    """Rastreamento de aceitações de consentimento com referência a versão específica."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(
        max_length=32,
        choices=(
            ('tcle', 'TCLE (Termo de Consentimento Livre e Esclarecido)'),
            ('privacy_policy', 'Privacy Policy'),
        )
    )
    document = models.ForeignKey(ConsentDocument, on_delete=models.PROTECT, related_name='acceptances')
    accepted = models.BooleanField(default=False)
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=512, null=True, blank=True)

    objects = ConsentManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'consent_type', '-created_at']),
            models.Index(fields=['document', 'accepted']),
            models.Index(fields=['created_at']),
        ]
        # Permite múltiplos registros mesmo tipo/user (para histórico)
        unique_together = []

    def __str__(self):
        return f"Consent {self.user_id} - {self.document} ({self.accepted})"
    
    def save(self, *args, **kwargs):
        """Garante que tipo de consentimento corresponde ao document."""
        if self.document and self.consent_type != self.document.consent_type:
            raise ValueError(
                f"Consent type '{self.consent_type}' não corresponde ao document type '{self.document.consent_type}'"
            )
        super().save(*args, **kwargs)

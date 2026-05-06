from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import Image, UserProfile, PatientNonClinicalInfos, ProviderNonClinicalInfos, ConsentDocument, Consent
from .omop_models import (
    Person,
    Provider,
    Location,
    ConditionOccurrence,
    Observation,
    Measurement,
    VisitOccurrence,
    FactRelationship,
)


# ============================================================================
# FORMULÁRIO CUSTOMIZADO PARA CONSENTDOCUMENT
# ============================================================================

class ConsentDocumentForm(forms.ModelForm):
    """Formulário customizado para upload de documentos de consentimento."""
    document_file = forms.FileField(
        required=False,
        label='Arquivo do Documento (PDF ou HTML)',
        help_text='Máximo 50MB. Formatos aceitos: PDF, HTML'
    )
    changelog = forms.CharField(
        required=True,
        widget=forms.Textarea,
        label='Changelog',
        help_text='Descrição das mudanças nesta versão'
    )

    class Meta:
        model = ConsentDocument
        fields = ('consent_type', 'version', 'language', 'effective_date', 'is_active', 'requires_reconsent', 'changelog')
        widgets = {
            'effective_date': AdminSplitDateTime(
                attrs={
                    'class': 'vDateTimeField',
                }
            ),
        }

    def clean_document_file(self):
        file = self.cleaned_data.get('document_file')
        if file:
            # Validar extensão
            valid_extensions = {'.pdf', '.html', '.htm'}
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Tipo de arquivo não permitido. Use: {", ".join(valid_extensions)}'
                )
            
            # Validar tamanho
            MAX_SIZE = 50 * 1024 * 1024
            if file.size > MAX_SIZE:
                raise ValidationError(
                    f'Arquivo muito grande. Tamanho: {file.size} bytes. Máximo: {MAX_SIZE} bytes.'
                )
        return file

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('document_file')
        consent_type = cleaned_data.get('consent_type')
        version = cleaned_data.get('version')
        language = cleaned_data.get('language')
        
        if file and consent_type and version and language:
            from .minio_storage import upload_consent_document_to_minio
            try:
                # Upload para MinIO
                file_path, content_type, content_hash = upload_consent_document_to_minio(
                    file,
                    consent_type,
                    version,
                    language
                )
                
                self._uploaded_file_data = {
                    'file_path': file_path,
                    'content_type': content_type,
                    'content_hash': content_hash,
                    'file_size': file.size
                }
            except Exception as e:
                self.add_error('document_file', f'Erro ao fazer upload do arquivo: {str(e)}')
                
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if hasattr(self, '_uploaded_file_data'):
            data = self._uploaded_file_data
            instance.file_path = data['file_path']
            instance.content_type = data['content_type']
            instance.content_hash = data['content_hash']
            instance.file_size = data['file_size']
            
            # Desativar versão anterior do mesmo tipo/language
            if instance.id:
                # Se já tiver ID, exclui a si mesmo (caso de edição, embora seja incomum mudar arquivo sem mudar versão)
                ConsentDocument.objects.filter(
                    consent_type=instance.consent_type,
                    language=instance.language,
                    is_active=True
                ).exclude(id=instance.id).update(is_active=False)
            else:
                ConsentDocument.objects.filter(
                    consent_type=instance.consent_type,
                    language=instance.language,
                    is_active=True
                ).update(is_active=False)
                
        if commit:
            instance.save()
        return instance


# ============================================================================
# REGISTROS DE ADMIN
# ============================================================================

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'extension', 'user', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'is_allowed', 'updated_at')
    list_editable = ('is_allowed',)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'person_source_value', 'year_of_birth')


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider_name', 'provider_source_value')


@admin.register(PatientNonClinicalInfos)
class PatientNonClinicalInfosAdmin(admin.ModelAdmin):
    list_display = ('person', 'name', 'user', 'created_at', 'updated_at')


@admin.register(ProviderNonClinicalInfos)
class ProviderNonClinicalInfosAdmin(admin.ModelAdmin):
    list_display = ('provider', 'email', 'phone_number', 'is_allowed', 'updated_at')
    list_editable = ('is_allowed',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'city', 'state', 'address_1')
    search_fields = ('city', 'state', 'address_1')


@admin.register(ConsentDocument)
class ConsentDocumentAdmin(admin.ModelAdmin):
    form = ConsentDocumentForm
    list_display = ('id', 'consent_type', 'version', 'language', 'is_active', 'effective_date', 'created_at')
    list_filter = ('consent_type', 'language', 'is_active', 'effective_date')
    search_fields = ('version', 'changelog', 'content_hash')
    readonly_fields = ('content_hash', 'file_path', 'content_type', 'file_size', 'created_at', 'file_info')
    
    def get_form(self, request, obj=None, **kwargs):
        """Pré-preenche effective_date com agora quando cria novo documento."""
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Novo documento
            from django.utils import timezone
            form.base_fields['effective_date'].initial = timezone.now()
        return form
    
    fieldsets = (
        ('Metadados', {
            'fields': ('consent_type', 'version', 'language', 'effective_date', 'is_active', 'requires_reconsent')
        }),
        ('Upload do Arquivo', {
            'fields': ('document_file',),
            'description': 'Faça upload de um novo arquivo (PDF ou HTML). Se deixar em branco, mantém o arquivo atual.'
        }),
        ('Documentação (OBRIGATÓRIO)', {
            'fields': ('changelog',),
        }),
        ('Informações do Arquivo (Somente Leitura)', {
            'fields': ('file_info', 'file_path', 'content_type', 'file_size', 'content_hash'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def file_info(self, obj):
        """Exibe informações do arquivo de forma legível."""
        if obj.file_path:
            filename = obj.file_path.split('/')[-1]
            size_mb = obj.file_size / (1024*1024)
            return format_html(
                '✓ Arquivo: <strong>{}</strong><br>Tamanho: <strong>{:.2f} MB</strong>',
                filename, size_mb
            )
        return "Nenhum arquivo enviado"
    file_info.short_description = "Status do Arquivo"


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'consent_type', 'document', 'accepted', 'created_at')
    list_filter = ('consent_type', 'accepted', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ConditionOccurrence)
class ConditionOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'condition_concept_id', 'condition_start_date')


@admin.register(VisitOccurrence)
class VisitOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'visit_concept_id', 'visit_start_date', 'visit_end_date')


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'observation_concept_id', 'value_as_number', 'observation_datetime')


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'measurement_concept_id', 'value_as_number', 'measurement_date')


@admin.register(FactRelationship)
class FactRelationshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'fact_id_1', 'domain_concept_id_1', 'fact_id_2', 'domain_concept_id_2')




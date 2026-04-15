from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import Image, UserProfile, PatientNonClinicalInfos, ProviderNonClinicalInfos, ConsentDocument
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


@admin.register(ConditionOccurrence)
class ConditionOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'condition_concept_id', 'condition_start_date')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'city', 'state', 'address_1')


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


class ConsentDocumentForm(forms.ModelForm):
    """Formulário customizado para upload de documentos de consentimento."""
    document_file = forms.FileField(
        required=False,
        label='Arquivo do Documento (PDF ou HTML)',
        help_text='Máximo 50MB. Formatos aceitos: PDF, HTML'
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

    def save(self, commit=True):
        instance = super().save(commit=False)
        file = self.cleaned_data.get('document_file')
        
        if file:
            # Upload para MinIO
            from .minio_storage import upload_consent_document_to_minio
            try:
                file_path, content_type, content_hash = upload_consent_document_to_minio(
                    file,
                    instance.consent_type,
                    instance.version,
                    instance.language
                )
                instance.file_path = file_path
                instance.content_type = content_type
                instance.content_hash = content_hash
                instance.file_size = file.size
                
                # Desativar versão anterior do mesmo tipo/language
                ConsentDocument.objects.filter(
                    consent_type=instance.consent_type,
                    language=instance.language,
                    is_active=True
                ).exclude(id=instance.id).update(is_active=False)
                
            except Exception as e:
                raise ValidationError(f'Erro ao fazer upload do arquivo: {str(e)}')
        
        if commit:
            instance.save()
        return instance


@admin.register(ConsentDocument)
class ConsentDocumentAdmin(admin.ModelAdmin):
    form = ConsentDocumentForm
    list_display = ('id', 'consent_type', 'version', 'language', 'is_active', 'effective_date', 'file_size')
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
        ('Informações do Arquivo (Somente Leitura)', {
            'fields': ('file_info', 'file_path', 'content_type', 'file_size', 'content_hash'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('created_at',)
        }),
        ('Documentação', {
            'fields': ('changelog',),
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



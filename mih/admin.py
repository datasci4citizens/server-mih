from django.contrib import admin
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


@admin.register(ConsentDocument)
class ConsentDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'consent_type', 'version', 'language', 'is_active', 'effective_date', 'file_size')
    list_filter = ('consent_type', 'language', 'is_active', 'effective_date')
    search_fields = ('version', 'changelog', 'content_hash')
    readonly_fields = ('content_hash', 'file_path', 'content_type', 'file_size', 'created_at')
    
    fieldsets = (
        ('Tipo e Versão', {
            'fields': ('consent_type', 'version', 'language')
        }),
        ('Arquivo', {
            'fields': ('file_path', 'content_type', 'file_size', 'content_hash')
        }),
        ('Datas', {
            'fields': ('effective_date', 'created_at')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Documentação', {
            'fields': ('changelog',),
            'classes': ('collapse',)
        }),
    )


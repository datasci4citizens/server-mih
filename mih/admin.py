from django.contrib import admin
from .models import Patient, Mih, TrackingRecord, Image
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


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')


@admin.register(Mih)
class MihAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'diagnosis', 'created_at')


@admin.register(TrackingRecord)
class TrackingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'mih', 'image_id', 'created_at')


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'extension', 'user', 'created_at')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'person_source_value', 'year_of_birth')


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider_name', 'provider_source_value')


@admin.register(ConditionOccurrence)
class ConditionOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'condition_concept_id', 'condition_start_date')


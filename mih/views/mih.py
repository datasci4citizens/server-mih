from django.db import transaction
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from ..models import PatientNonClinicalInfos
from ..omop_models import (
    ConditionOccurrence,
    Observation,
    Measurement,
)
from ..serializers import MihSerializer
from .patient import _is_allowed_specialist


logger = logging.getLogger(__name__)


# Constants (MIH observations)
OBS_MIH_USER_NOTES = 46235038       # notas do responsável
OBS_MIH_SPECIALIST_NOTES = 46235039  # observações do especialista
OBS_MIH_DIAGNOSIS_TEXT = 46235040    # diagnóstico do especialista
OBS_MIH_SENSITIVITY = 4247583
OBS_MIH_STAIN = 440758
OBS_MIH_AESTHETIC = 4090431
OBS_MIH_PHOTO_1 = 920009
OBS_MIH_PHOTO_2 = 920010
OBS_MIH_PHOTO_3 = 920011
COND_MIH_CASE = 44783854
MEAS_MIH_PAIN_LEVEL = 43055141


# Helpers
def _set_mih_observation(condition, concept_id, *, number=None, text=None, bool_value=None):
    person = condition.person
    # Delete any existing observation for this condition+concept (bare prefix or with text)
    Observation.objects.filter(
        person=person,
        observation_concept_id=concept_id,
        value_as_string__startswith=f"mih:{condition.id}",
    ).delete()

    # Don't create if there's nothing meaningful to store
    if number is None and text in (None, '') and bool_value is None:
        return

    payload = {'person': person, 'observation_concept_id': concept_id, 'value_as_string': f"mih:{condition.id}"}
    if number is not None:
        payload['value_as_number'] = float(number)
    if text not in (None, ''):
        payload['value_as_string'] = f"mih:{condition.id}|{text}"
    if bool_value is not None:
        payload['value_as_concept_id'] = 4188539 if bool_value else 4188540
    Observation.objects.create(**payload)


def _get_mih_observation(condition, concept_id):
    row = Observation.objects.filter(
        person=condition.person,
        observation_concept_id=concept_id,
        value_as_string__startswith=f"mih:{condition.id}",
    ).order_by('-id').first()
    return row


def _serialize_mih(condition):
    measurement = Measurement.objects.filter(person=condition.person, measurement_concept_id=MEAS_MIH_PAIN_LEVEL).order_by('-id').first()

    def bool_from(concept):
        row = _get_mih_observation(condition, concept)
        if not row:
            return None
        if row.value_as_concept_id is None:
            return None
        return row.value_as_concept_id == 4188539

    def text_from(concept):
        row = _get_mih_observation(condition, concept)
        if not row or not row.value_as_string:
            return None
        value = row.value_as_string
        sep = f"mih:{condition.id}|"
        if value.startswith(sep):
            return value[len(sep):]   # texto real após o separador
        if value == f"mih:{condition.id}":
            return None              # só o prefixo bare, sem texto
        return value

    def number_from_photo(concept):
        row = _get_mih_observation(condition, concept)
        return int(row.value_as_number) if row and row.value_as_number is not None else None

    return {
        'id': condition.id,
        'mih_id': condition.id,
        'patient': condition.person_id,
        'start_date': condition.condition_start_date,
        'end_date': condition.condition_end_date,
        'painLevel': int(measurement.value_as_number) if measurement and measurement.value_as_number is not None else None,
        'sensitivityField': bool_from(OBS_MIH_SENSITIVITY),
        'stain': bool_from(OBS_MIH_STAIN),
        'aestheticDiscomfort': bool_from(OBS_MIH_AESTHETIC),
        'userObservations': text_from(OBS_MIH_USER_NOTES),
        'specialistObservations': text_from(OBS_MIH_SPECIALIST_NOTES),
        'diagnosis': text_from(OBS_MIH_DIAGNOSIS_TEXT),
        'photo_id1': number_from_photo(OBS_MIH_PHOTO_1),
        'photo_id2': number_from_photo(OBS_MIH_PHOTO_2),
        'photo_id3': number_from_photo(OBS_MIH_PHOTO_3),
    }


class MihViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if request.user.is_staff or request.user.is_superuser:
            rows = [
                _serialize_mih(row)
                for row in ConditionOccurrence.objects.filter(condition_concept_id=COND_MIH_CASE).order_by('-id')
            ]
        else:
            person_ids = PatientNonClinicalInfos.objects.filter(user=request.user).values_list('person_id', flat=True)
            rows = [
                _serialize_mih(row)
                for row in ConditionOccurrence.objects.filter(condition_concept_id=COND_MIH_CASE, person_id__in=person_ids).order_by('-id')
            ]
        return Response(rows)

    def retrieve(self, request, pk=None):
        row = ConditionOccurrence.objects.filter(pk=pk, condition_concept_id=COND_MIH_CASE).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id) or _is_allowed_specialist(request.user)):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_mih(row))

    def create(self, request):
        serializer = MihSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from ..omop_models import Person
        
        person = Person.objects.filter(pk=data.get('patient')).first()
        if not person:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_400_BAD_REQUEST)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            row = ConditionOccurrence.objects.create(
                person=person,
                condition_concept_id=COND_MIH_CASE,
                condition_start_date=data.get('start_date'),
                condition_end_date=data.get('end_date'),
            )

            if data.get('painLevel') is not None:
                Measurement.objects.create(
                    person=person,
                    measurement_concept_id=MEAS_MIH_PAIN_LEVEL,
                    value_as_number=float(data.get('painLevel')),
                    measurement_date=data.get('start_date'),
                )

            _set_mih_observation(row, OBS_MIH_SENSITIVITY, bool_value=data.get('sensitivityField'))
            _set_mih_observation(row, OBS_MIH_STAIN, bool_value=data.get('stain'))
            _set_mih_observation(row, OBS_MIH_AESTHETIC, bool_value=data.get('aestheticDiscomfort'))
            _set_mih_observation(row, OBS_MIH_USER_NOTES, text=data.get('userObservations'))
            _set_mih_observation(row, OBS_MIH_SPECIALIST_NOTES, text=data.get('specialistObservations'))
            _set_mih_observation(row, OBS_MIH_DIAGNOSIS_TEXT, text=data.get('diagnosis'))
            _set_mih_observation(row, OBS_MIH_PHOTO_1, number=data.get('photo_id1'))
            _set_mih_observation(row, OBS_MIH_PHOTO_2, number=data.get('photo_id2'))
            _set_mih_observation(row, OBS_MIH_PHOTO_3, number=data.get('photo_id3'))

        return Response(_serialize_mih(row), status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    def update(self, request, pk=None):
        row = ConditionOccurrence.objects.filter(pk=pk, condition_concept_id=COND_MIH_CASE).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id) or _is_allowed_specialist(request.user)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MihSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            if 'start_date' in data:
                row.condition_start_date = data.get('start_date')
            if 'end_date' in data:
                row.condition_end_date = data.get('end_date')
            row.save()

            if 'painLevel' in data:
                Measurement.objects.filter(person=row.person, measurement_concept_id=MEAS_MIH_PAIN_LEVEL).delete()
                if data.get('painLevel') is not None:
                    Measurement.objects.create(
                        person=row.person,
                        measurement_concept_id=MEAS_MIH_PAIN_LEVEL,
                        value_as_number=float(data.get('painLevel')),
                        measurement_date=row.condition_start_date,
                    )

        mapping = {
            'sensitivityField': (OBS_MIH_SENSITIVITY, 'bool'),
            'stain': (OBS_MIH_STAIN, 'bool'),
            'aestheticDiscomfort': (OBS_MIH_AESTHETIC, 'bool'),
            'userObservations': (OBS_MIH_USER_NOTES, 'text'),
            'specialistObservations': (OBS_MIH_SPECIALIST_NOTES, 'text'),
            'diagnosis': (OBS_MIH_DIAGNOSIS_TEXT, 'text'),
            'photo_id1': (OBS_MIH_PHOTO_1, 'number'),
            'photo_id2': (OBS_MIH_PHOTO_2, 'number'),
            'photo_id3': (OBS_MIH_PHOTO_3, 'number'),
        }
        for field, (concept, kind) in mapping.items():
            if field in data:
                if kind == 'bool':
                    _set_mih_observation(row, concept, bool_value=data.get(field))
                elif kind == 'text':
                    _set_mih_observation(row, concept, text=data.get(field))
                else:
                    _set_mih_observation(row, concept, number=data.get(field))

        return Response(_serialize_mih(row))

    def destroy(self, request, pk=None):
        row = ConditionOccurrence.objects.filter(pk=pk, condition_concept_id=COND_MIH_CASE).first()
        if row:
            non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
            if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
                return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
            row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def undiagnosed(self, request):
        """Retorna os casos MIH que ainda não possuem diagnóstico do especialista."""
        # Fetch all diagnosis strings in a single query
        diagnosed_strings = set(
            Observation.objects.filter(
                observation_concept_id=OBS_MIH_DIAGNOSIS_TEXT,
            ).values_list('value_as_string', flat=True)
        )

        conditions = ConditionOccurrence.objects.filter(condition_concept_id=COND_MIH_CASE).order_by('id')

        rows = []
        for condition in conditions:
            prefix = f"mih:{condition.id}|"
            has_diagnosis = any(v.startswith(prefix) for v in diagnosed_strings)
            if not has_diagnosis:
                rows.append(_serialize_mih(condition))
        return Response(rows)

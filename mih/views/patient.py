import json
from datetime import datetime
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from ..models import PatientNonClinicalInfos
from ..omop_models import (
    Person,
    Location,
    VisitOccurrence,
    Observation,
)
from ..serializers import PatientSerializer


# Constants (Patient concepts)
PATIENT_CONCEPTS = {
    'highFever': 44810013,
    'premature': 4272248,
    'deliveryProblems': 43530950,
    'lowWeight': 4171115,
    'deliveryType': 4145318,
    'deliveryProblemsTypes': 432382,
    'consultType': 910007,
}

YES_CONCEPT_ID = 4188539
NO_CONCEPT_ID = 4188540

DELIVERY_TYPE_VALUE_MAP = {
    'cesarean': 4015701,
    'normal': 4125611,
}

CONSULT_TYPE_VALUE_MAP = {
    'public': 44804377,
    'private': 44803901,
}


# Helpers
def _to_optional_int(value):
    if value in (None, ''):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return None


def _set_observation_choice(person, concept_id, value, value_map):
    Observation.objects.filter(person=person, observation_concept_id=concept_id).delete()
    if value in (None, ''):
        return
    normalized = str(value).strip().lower()
    concept_value = value_map.get(normalized)
    if concept_value is None:
        return
    Observation.objects.create(
        person=person,
        observation_concept_id=concept_id,
        value_as_concept_id=concept_value,
    )


def _get_observation_choice(person, concept_id, value_map):
    row = Observation.objects.filter(person=person, observation_concept_id=concept_id).order_by('-id').first()
    if not row or row.value_as_concept_id is None:
        return None
    reverse = {v: k for k, v in value_map.items()}
    return reverse.get(int(row.value_as_concept_id))


def _parse_person_source_value(value):
    if not value:
        return {}
    try:
        data = json.loads(value)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {'name': value}


def _set_observation_bool(person, concept_id, enabled):
    Observation.objects.filter(person=person, observation_concept_id=concept_id).delete()
    if enabled is not None:
        Observation.objects.create(
            person=person,
            observation_concept_id=concept_id,
            value_as_concept_id=YES_CONCEPT_ID if bool(enabled) else NO_CONCEPT_ID,
        )


def _set_observation_number(person, concept_id, value):
    Observation.objects.filter(person=person, observation_concept_id=concept_id).delete()
    if value is not None:
        Observation.objects.create(
            person=person,
            observation_concept_id=concept_id,
            value_as_number=float(value),
        )


def _set_observation_text(person, concept_id, value):
    Observation.objects.filter(person=person, observation_concept_id=concept_id).delete()
    if value not in (None, ''):
        Observation.objects.create(
            person=person,
            observation_concept_id=concept_id,
            value_as_string=str(value),
        )


def _get_observation_bool(person, concept_id):
    row = Observation.objects.filter(person=person, observation_concept_id=concept_id).order_by('-id').first()
    if not row or row.value_as_concept_id is None:
        return None
    return row.value_as_concept_id == YES_CONCEPT_ID


def _get_observation_number(person, concept_id):
    row = Observation.objects.filter(person=person, observation_concept_id=concept_id).order_by('-id').first()
    if not row:
        return None
    if row.value_as_number is None:
        return None
    return int(row.value_as_number)


def _get_observation_text(person, concept_id):
    row = Observation.objects.filter(person=person, observation_concept_id=concept_id).order_by('-id').first()
    return row.value_as_string if row else None


def _serialize_patient(person):
    source = _parse_person_source_value(person.person_source_value)
    non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
    birthday = None
    if person.birth_datetime:
        birthday = person.birth_datetime.isoformat().replace('+00:00', 'Z')
    elif person.year_of_birth and person.month_of_birth and person.day_of_birth:
        try:
            birthday = datetime(person.year_of_birth, person.month_of_birth, person.day_of_birth).isoformat() + 'Z'
        except Exception:
            birthday = None

    consult_choice = _get_observation_choice(person, PATIENT_CONCEPTS['consultType'], CONSULT_TYPE_VALUE_MAP)
    consult_type = consult_choice
    if consult_type is None:
        consult_type = _get_observation_text(person, PATIENT_CONCEPTS['consultType'])
    if consult_type is None:
        consult = VisitOccurrence.objects.filter(person=person).order_by('-id').first()
        consult_type = str(consult.visit_concept_id) if consult and consult.visit_concept_id is not None else None

    return {
        'id': person.id,
        'patient_id': person.id,
        'name': (non_clinical.name if non_clinical else None) or source.get('name'),
        'birthday': birthday,
        'user_id': non_clinical.user_id if non_clinical and non_clinical.user_id else None,
        'created_at': non_clinical.created_at.isoformat().replace('+00:00', 'Z') if non_clinical and non_clinical.created_at else None,
        'updated_at': non_clinical.updated_at.isoformat().replace('+00:00', 'Z') if non_clinical and non_clinical.updated_at else None,
        'highFever': _get_observation_bool(person, PATIENT_CONCEPTS['highFever']),
        'premature': _get_observation_bool(person, PATIENT_CONCEPTS['premature']),
        'deliveryProblems': _get_observation_bool(person, PATIENT_CONCEPTS['deliveryProblems']),
        'lowWeight': _get_observation_bool(person, PATIENT_CONCEPTS['lowWeight']),
        'deliveryType': _get_observation_choice(person, PATIENT_CONCEPTS['deliveryType'], DELIVERY_TYPE_VALUE_MAP) or _get_observation_text(person, PATIENT_CONCEPTS['deliveryType']),
        'brothersNumber': _get_observation_number(person, OBS_BROTHERS_NUMBER),
        'consultType': consult_type,
        'deliveryProblemsTypes': _get_observation_text(person, PATIENT_CONCEPTS['deliveryProblemsTypes']),
    }


OBS_BROTHERS_NUMBER = 4072485


class PatientViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if request.user.is_staff or request.user.is_superuser:
            persons = Person.objects.all().order_by('id')
            rows = [_serialize_patient(person) for person in persons]
        else:
            non_clinicals = PatientNonClinicalInfos.objects.filter(user=request.user).select_related('person')
            rows = [_serialize_patient(nc.person) for nc in non_clinicals]
        return Response(rows)

    def retrieve(self, request, pk=None):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_patient(person))

    def create(self, request):
        serializer = PatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            birthday = data.get('birthday')
            location = None
            meta = {'name': data.get('name')}
            person = Person.objects.create(
                person_source_value=json.dumps(meta),
                birth_datetime=birthday,
                year_of_birth=birthday.year if birthday else None,
                month_of_birth=birthday.month if birthday else None,
                day_of_birth=birthday.day if birthday else None,
                gender_concept_id=0,
                location=location,
            )

            # Always associate created patient with the authenticated user
            PatientNonClinicalInfos.objects.create(
                person=person,
                name=data.get('name'),
                user=request.user,
            )

            _set_observation_bool(person, PATIENT_CONCEPTS['highFever'], data.get('highFever'))
            _set_observation_bool(person, PATIENT_CONCEPTS['premature'], data.get('premature'))
            _set_observation_bool(person, PATIENT_CONCEPTS['deliveryProblems'], data.get('deliveryProblems'))
            _set_observation_bool(person, PATIENT_CONCEPTS['lowWeight'], data.get('lowWeight'))
            _set_observation_choice(person, PATIENT_CONCEPTS['deliveryType'], data.get('deliveryType'), DELIVERY_TYPE_VALUE_MAP)
            _set_observation_number(person, OBS_BROTHERS_NUMBER, data.get('brothersNumber'))
            _set_observation_text(person, PATIENT_CONCEPTS['deliveryProblemsTypes'], data.get('deliveryProblemsTypes'))
            consult_type = data.get('consultType')
            _set_observation_choice(person, PATIENT_CONCEPTS['consultType'], consult_type, CONSULT_TYPE_VALUE_MAP)
            if consult_type not in (None, ''):
                concept = _to_optional_int(consult_type)
                VisitOccurrence.objects.create(person=person, visit_concept_id=concept)

        return Response(_serialize_patient(person), status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PatientSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            source = _parse_person_source_value(person.person_source_value)
            if 'name' in data:
                source['name'] = data.get('name')
                person.person_source_value = json.dumps(source)

            if 'birthday' in data:
                birthday = data.get('birthday')
                if birthday is None:
                    person.birth_datetime = None
                    person.year_of_birth = None
                    person.month_of_birth = None
                    person.day_of_birth = None
                else:
                    person.birth_datetime = birthday
                    person.year_of_birth = birthday.year
                    person.month_of_birth = birthday.month
                    person.day_of_birth = birthday.day

            person.save()

            non_clinical, _ = PatientNonClinicalInfos.objects.get_or_create(person=person)
            if 'name' in data:
                non_clinical.name = data.get('name')
            # Only staff may change patient ownership
            if 'user_id' in data and request.user.is_staff:
                non_clinical.user_id = data.get('user_id')
            non_clinical.save()

            for field, concept in PATIENT_CONCEPTS.items():
                if field in ('deliveryProblemsTypes',):
                    if field in data:
                        _set_observation_text(person, concept, data.get(field))
                else:
                    if field in data:
                        _set_observation_bool(person, concept, data.get(field))

            if 'deliveryType' in data:
                _set_observation_choice(person, PATIENT_CONCEPTS['deliveryType'], data.get('deliveryType'), DELIVERY_TYPE_VALUE_MAP)

            if 'consultType' in data:
                _set_observation_choice(person, PATIENT_CONCEPTS['consultType'], data.get('consultType'), CONSULT_TYPE_VALUE_MAP)

            if 'brothersNumber' in data:
                _set_observation_number(person, OBS_BROTHERS_NUMBER, data.get('brothersNumber'))

            if 'consultType' in data:
                VisitOccurrence.objects.filter(person=person).delete()
                consult_type = data.get('consultType')
                if consult_type not in (None, ''):
                    concept = _to_optional_int(consult_type)
                    VisitOccurrence.objects.create(person=person, visit_concept_id=concept)

        return Response(_serialize_patient(person))

    def destroy(self, request, pk=None):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return Response(status=status.HTTP_204_NO_CONTENT)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        person.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def my_patients(self, request):
        """Retorna os pacientes vinculados ao responsável autenticado."""
        non_clinicals = PatientNonClinicalInfos.objects.filter(user=request.user).select_related('person')
        rows = [_serialize_patient(nc.person) for nc in non_clinicals]
        return Response(rows)

    def patient_mih(self, request, pk=None):
        """Retorna todos os registros MIH de um paciente específico."""
        from .mih import _serialize_mih
        from ..omop_models import ConditionOccurrence
        
        COND_MIH_CASE = 44783854
        
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        rows = [
            _serialize_mih(row)
            for row in ConditionOccurrence.objects.filter(person=person, condition_concept_id=COND_MIH_CASE).order_by('-id')
        ]
        return Response(rows)

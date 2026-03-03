import json
from datetime import datetime
from django.http import Http404, StreamingHttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from .models import Image, PatientNonClinicalInfos
from .minio_storage import get_image_from_minio, delete_image_from_minio, MinioStorageError
from .omop_models import (
    Person,
    Location,
    ConditionOccurrence,
    Observation,
    Measurement,
    VisitOccurrence,
    FactRelationship,
)
from .serializers import PatientSerializer, MihSerializer, TrackingRecordSerializer, ImageSerializer


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    pass


PATIENT_CONCEPTS = {
    'highFever': 44810013,
    'premature': 4272248,
    'deliveryProblems': 43530950,
    'lowWeight': 4171115,
    'deliveryType': 4145318,
    'deliveryProblemsTypes': 910006,
    'consultType': 910007,
}

OBS_BROTHERS_NUMBER = 4072485
OBS_TRACKING_TEXT = 920002
OBS_MIH_USER_NOTES = 920003
OBS_MIH_SPECIALIST_NOTES = 920004
OBS_MIH_DIAGNOSIS_TEXT = 920005
OBS_MIH_SENSITIVITY = 4247583
OBS_MIH_STAIN = 440758
OBS_MIH_AESTHETIC = 920008
OBS_MIH_PHOTO_1 = 920009
OBS_MIH_PHOTO_2 = 920010
OBS_MIH_PHOTO_3 = 920011
COND_MIH_CASE = 44783854
MEAS_MIH_PAIN_LEVEL = 43055141

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


class PatientViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        rows = [_serialize_patient(person) for person in Person.objects.all().order_by('id')]
        return Response(rows)

    def retrieve(self, request, pk=None):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_patient(person))

    def create(self, request):
        serializer = PatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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

        PatientNonClinicalInfos.objects.create(
            person=person,
            name=data.get('name'),
            user_id=data.get('user_id'),
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

        serializer = PatientSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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
        if 'user_id' in data:
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
        person.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _set_mih_observation(condition, concept_id, *, number=None, text=None, bool_value=None):
    person = condition.person
    Observation.objects.filter(
        person=person,
        observation_concept_id=concept_id,
    ).filter(value_as_string=f"mih:{condition.id}").delete()

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
        return value.replace(sep, '', 1) if value.startswith(sep) else value

    def number_from_photo(concept):
        row = _get_mih_observation(condition, concept)
        return int(row.value_as_number) if row and row.value_as_number is not None else None

    return {
        'id': condition.id,
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        rows = [
            _serialize_mih(row)
            for row in ConditionOccurrence.objects.filter(condition_concept_id=COND_MIH_CASE).order_by('id')
        ]
        return Response(rows)

    def retrieve(self, request, pk=None):
        row = ConditionOccurrence.objects.filter(pk=pk, condition_concept_id=COND_MIH_CASE).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_mih(row))

    def create(self, request):
        serializer = MihSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        person = Person.objects.filter(pk=data.get('patient')).first()
        if not person:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_400_BAD_REQUEST)

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

    def update(self, request, pk=None):
        row = ConditionOccurrence.objects.filter(pk=pk, condition_concept_id=COND_MIH_CASE).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MihSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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
            row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrackingRecordViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        rows = Observation.objects.filter(observation_concept_id=OBS_TRACKING_TEXT).order_by('id')
        payload = []
        for row in rows:
            image_ref = FactRelationship.objects.filter(fact_id_1=row.id).order_by('-id').first()
            payload.append({
                'id': row.id,
                'mih': image_ref.fact_id_2 if image_ref else None,
                'image_id': int(row.value_as_number) if row.value_as_number is not None else None,
                'observations': row.value_as_string,
            })
        return Response(payload)

    def retrieve(self, request, pk=None):
        row = Observation.objects.filter(pk=pk, observation_concept_id=OBS_TRACKING_TEXT).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        image_ref = FactRelationship.objects.filter(fact_id_1=row.id).order_by('-id').first()
        return Response({
            'id': row.id,
            'mih': image_ref.fact_id_2 if image_ref else None,
            'image_id': int(row.value_as_number) if row.value_as_number is not None else None,
            'observations': row.value_as_string,
        })

    def create(self, request):
        serializer = TrackingRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        person_id = data.get('mih')
        condition = ConditionOccurrence.objects.filter(pk=person_id, condition_concept_id=COND_MIH_CASE).first() if person_id else None
        person = condition.person if condition else Person.objects.order_by('id').first()
        if not person:
            return Response({'detail': 'Person not found.'}, status=status.HTTP_400_BAD_REQUEST)

        row = Observation.objects.create(
            person=person,
            observation_concept_id=OBS_TRACKING_TEXT,
            value_as_string=data.get('observations'),
            value_as_number=float(data.get('image_id')) if data.get('image_id') is not None else None,
        )

        if condition:
            FactRelationship.objects.create(fact_id_1=row.id, fact_id_2=condition.id)

        return Response({
            'id': row.id,
            'mih': condition.id if condition else None,
            'image_id': int(row.value_as_number) if row.value_as_number is not None else None,
            'observations': row.value_as_string,
        }, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        row = Observation.objects.filter(pk=pk, observation_concept_id=OBS_TRACKING_TEXT).first()
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TrackingRecordSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'observations' in data:
            row.value_as_string = data.get('observations')
        if 'image_id' in data:
            row.value_as_number = float(data.get('image_id')) if data.get('image_id') is not None else None
        row.save()

        if 'mih' in data:
            FactRelationship.objects.filter(fact_id_1=row.id).delete()
            mih_id = data.get('mih')
            if mih_id is not None:
                FactRelationship.objects.create(fact_id_1=row.id, fact_id_2=mih_id)

        image_ref = FactRelationship.objects.filter(fact_id_1=row.id).order_by('-id').first()
        return Response({
            'id': row.id,
            'mih': image_ref.fact_id_2 if image_ref else None,
            'image_id': int(row.value_as_number) if row.value_as_number is not None else None,
            'observations': row.value_as_string,
        })

    def destroy(self, request, pk=None):
        row = Observation.objects.filter(pk=pk, observation_concept_id=OBS_TRACKING_TEXT).first()
        if row:
            FactRelationship.objects.filter(fact_id_1=row.id).delete()
            row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

    @action(detail=True, methods=['get'], url_path='content')
    def content(self, request, pk=None):
        image = self.get_object()
        if not image.object_name:
            raise Http404('Image object not found')

        try:
            minio_obj = get_image_from_minio(image.object_name)
        except MinioStorageError:
            raise Http404('Image file not found in object storage')

        def stream_minio_object(obj, chunk_size=8192):
            try:
                while True:
                    chunk = obj.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                obj.close()
                obj.release_conn()

        response = StreamingHttpResponse(
            streaming_content=stream_minio_object(minio_obj),
            content_type=image.content_type or 'application/octet-stream',
        )
        return response

    def perform_destroy(self, instance):
        delete_image_from_minio(instance.object_name)
        super().perform_destroy(instance)

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from ..models import PatientNonClinicalInfos
from ..omop_models import (
    Person,
    Observation,
    FactRelationship,
)
from ..serializers import TrackingRecordSerializer


OBS_TRACKING_TEXT = 46235038


class TrackingRecordViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if request.user.is_staff or request.user.is_superuser:
            rows = Observation.objects.filter(observation_concept_id=OBS_TRACKING_TEXT).order_by('id')
        else:
            person_ids = PatientNonClinicalInfos.objects.filter(user=request.user).values_list('person_id', flat=True)
            rows = Observation.objects.filter(observation_concept_id=OBS_TRACKING_TEXT, person_id__in=person_ids).order_by('id')
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
        non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
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

        from ..omop_models import ConditionOccurrence
        
        COND_MIH_CASE = 44783854
        
        person_id = data.get('mih')
        condition = ConditionOccurrence.objects.filter(pk=person_id, condition_concept_id=COND_MIH_CASE).first() if person_id else None
        person = condition.person if condition else Person.objects.order_by('id').first()
        if not person:
            return Response({'detail': 'Person not found.'}, status=status.HTTP_400_BAD_REQUEST)
        non_clinical = PatientNonClinicalInfos.objects.filter(person=person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

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

        non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
        if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

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
            non_clinical = PatientNonClinicalInfos.objects.filter(person=row.person).first()
            if not (request.user.is_staff or (non_clinical and non_clinical.user_id == request.user.id)):
                return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
            FactRelationship.objects.filter(fact_id_1=row.id).delete()
            row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

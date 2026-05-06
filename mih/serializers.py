from rest_framework import serializers
import logging
from .models import Image
from .minio_storage import upload_image_to_minio, MinioStorageError


logger = logging.getLogger(__name__)


class PatientSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    birthday = serializers.DateTimeField(required=False, allow_null=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    highFever = serializers.BooleanField(required=False, allow_null=True)
    premature = serializers.BooleanField(required=False, allow_null=True)
    deliveryProblems = serializers.BooleanField(required=False, allow_null=True)
    lowWeight = serializers.BooleanField(required=False, allow_null=True)
    deliveryType = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    brothersNumber = serializers.IntegerField(required=False, allow_null=True)
    consultType = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    deliveryProblemsTypes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tale_document_id = serializers.IntegerField(required=False, allow_null=True)
    tale_accepted = serializers.BooleanField(required=False, allow_null=True)


class MihSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    patient = serializers.IntegerField(required=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    painLevel = serializers.IntegerField(required=False, allow_null=True)
    sensitivityField = serializers.BooleanField(required=False, allow_null=True)
    stain = serializers.BooleanField(required=False, allow_null=True)
    aestheticDiscomfort = serializers.BooleanField(required=False, allow_null=True)
    userObservations = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    specialistObservations = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    diagnosis = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    photo_id1 = serializers.IntegerField(required=False, allow_null=True)
    photo_id2 = serializers.IntegerField(required=False, allow_null=True)
    photo_id3 = serializers.IntegerField(required=False, allow_null=True)


class TrackingRecordSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    mih = serializers.IntegerField(required=False, allow_null=True)
    image_id = serializers.IntegerField(required=False, allow_null=True)
    observations = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ImageSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = Image
        fields = ('id', 'file')
        read_only_fields = ('id',)

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({'detail': 'Usuário autenticado é obrigatório para upload de imagem.'})

        uploaded_file = validated_data.get('file')
        try:
            object_name, content_type, extension = upload_image_to_minio(uploaded_file, user.id)
        except MinioStorageError as exc:
            logger.exception("Error uploading image to MinIO from serializer")
            raise serializers.ValidationError({'detail': str(exc)})

        img = Image.objects.create(
            user=user,
            object_name=object_name,
            content_type=content_type,
            extension=extension or None,
        )
        return img

    def to_representation(self, instance):
        return {'id': instance.id}

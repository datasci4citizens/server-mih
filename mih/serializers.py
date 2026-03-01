from rest_framework import serializers
from .models import Image


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
        img = Image.objects.create(
            user=user if user and user.is_authenticated else None,
            file=validated_data.get('file')
        )
        return img

    def to_representation(self, instance):
        return {'id': instance.id}

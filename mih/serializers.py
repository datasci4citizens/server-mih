from rest_framework import serializers
from .models import Patient, Mih, TrackingRecord, Image


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'


class MihSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mih
        fields = '__all__'


class TrackingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingRecord
        fields = '__all__'


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

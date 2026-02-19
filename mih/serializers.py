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
    class Meta:
        model = Image
        fields = '__all__'

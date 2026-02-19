from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Patient, Mih, TrackingRecord, Image
from .serializers import PatientSerializer, MihSerializer, TrackingRecordSerializer, ImageSerializer


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    pass


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class MihViewSet(viewsets.ModelViewSet):
    queryset = Mih.objects.all()
    serializer_class = MihSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TrackingRecordViewSet(viewsets.ModelViewSet):
    queryset = TrackingRecord.objects.all()
    serializer_class = TrackingRecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

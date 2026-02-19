from django.db import models
from django.conf import settings


class Patient(models.Model):
    name = models.CharField(max_length=255)
    birthday = models.DateTimeField(null=True, blank=True)
    highFever = models.BooleanField(null=True)
    premature = models.BooleanField(null=True)
    deliveryProblems = models.BooleanField(null=True)
    lowWeight = models.BooleanField(null=True)
    deliveryType = models.CharField(max_length=255, null=True, blank=True)
    brothersNumber = models.IntegerField(null=True, blank=True)
    consultType = models.CharField(max_length=255, null=True, blank=True)
    deliveryProblemsTypes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patients', null=True, blank=True)

    def __str__(self):
        return f"Patient {self.id} - {self.name}"


class Mih(models.Model):
    start_date = models.DateTimeField(null=True)
    photo_id1 = models.IntegerField(null=True, blank=True)
    photo_id2 = models.IntegerField(null=True, blank=True)
    photo_id3 = models.IntegerField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    painLevel = models.IntegerField(null=True, blank=True)
    sensitivityField = models.BooleanField(null=True)
    stain = models.BooleanField(null=True)
    aestheticDiscomfort = models.BooleanField(null=True)
    userObservations = models.TextField(null=True, blank=True)
    specialistObservations = models.TextField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='mih')

    def __str__(self):
        return f"MIH {self.id} for patient {self.patient_id}"


class TrackingRecord(models.Model):
    image_id = models.IntegerField()
    observations = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mih = models.ForeignKey(Mih, on_delete=models.CASCADE, related_name='tracking_records', null=True, blank=True)

    def __str__(self):
        return f"TrackingRecord {self.id}"


class Image(models.Model):
    extension = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='images')

    def __str__(self):
        return f"Image {self.id}.{self.extension}"

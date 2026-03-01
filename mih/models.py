from django.db import models
from django.conf import settings
from .omop_models import Person, Provider


class Image(models.Model):
    file = models.FileField(upload_to='images/%Y/%m/%d')
    extension = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='images')

    def save(self, *args, **kwargs):
        if self.file and (not self.extension):
            name = getattr(self.file, 'name', '')
            if '.' in name:
                self.extension = name.rsplit('.', 1)[-1].lower()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.extension:
            return f"Image {self.id}.{self.extension}"
        return f"Image {self.id}"


class UserProfile(models.Model):
    ROLE_RESPONSIBLE = 'responsible'
    ROLE_SPECIALIST = 'specialist'
    ROLE_CHOICES = (
        (ROLE_RESPONSIBLE, 'Responsible'),
        (ROLE_SPECIALIST, 'Specialist'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, null=True, blank=True)
    is_allowed = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    state = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    neighborhood = models.CharField(max_length=128, null=True, blank=True)
    accept_tcle = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserProfile {self.user_id} ({self.role})"


class PatientNonClinicalInfos(models.Model):
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name='non_clinical_infos')
    name = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PatientNonClinicalInfos {self.person_id}"


class ProviderNonClinicalInfos(models.Model):
    provider = models.OneToOneField(Provider, on_delete=models.CASCADE, related_name='non_clinical_infos')
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    is_allowed = models.BooleanField(default=True)
    accept_tcle = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ProviderNonClinicalInfos {self.provider_id}"

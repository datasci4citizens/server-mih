from django.test import TestCase

from ..models import Patient, Mih
from ..omop_models import Person, Location


class PatientModelTest(TestCase):
    def test_create_patient_and_mih(self):
        p = Patient.objects.create(name="João", highFever=True)
        self.assertEqual(Patient.objects.count(), 1)
        m = Mih.objects.create(patient=p)
        self.assertEqual(Mih.objects.count(), 1)
        self.assertEqual(m.patient.id, p.id)


class OmopModelsTest(TestCase):
    def test_person_and_location(self):
        loc = Location.objects.create(city="São Paulo", state="SP", address_1="Rua A")
        person = Person.objects.create(person_source_value="ext-123", year_of_birth=1990, location=loc)
        self.assertEqual(Person.objects.count(), 1)
        self.assertEqual(person.location.id, loc.id)
        self.assertEqual(person.person_source_value, "ext-123")

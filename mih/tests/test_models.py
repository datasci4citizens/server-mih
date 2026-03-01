from django.test import TestCase

from ..omop_models import Person, Location, ConditionOccurrence, Observation


class OmopModelsTest(TestCase):
    def test_person_and_location(self):
        loc = Location.objects.create(city="São Paulo", state="SP", address_1="Rua A")
        person = Person.objects.create(person_source_value="ext-123", year_of_birth=1990, location=loc)
        self.assertEqual(Person.objects.count(), 1)
        self.assertEqual(person.location.id, loc.id)
        self.assertEqual(person.person_source_value, "ext-123")

    def test_condition_and_observation(self):
        person = Person.objects.create(person_source_value="p-1")
        cond = ConditionOccurrence.objects.create(person=person, condition_concept_id=44783854)
        obs = Observation.objects.create(person=person, observation_concept_id=920002, value_as_string="ok")
        self.assertEqual(cond.person_id, person.id)
        self.assertEqual(obs.person_id, person.id)

from django.db import models
from django.conf import settings


class Location(models.Model):
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    address_1 = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Location {self.id} - {self.city} / {self.state}"


class Provider(models.Model):
    provider_name = models.CharField(max_length=255, null=True, blank=True)
    provider_source_value = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Provider {self.id} - {self.provider_name}"


class Person(models.Model):
    person_source_value = models.CharField(max_length=512, null=True, blank=True)
    year_of_birth = models.IntegerField(null=True, blank=True)
    month_of_birth = models.IntegerField(null=True, blank=True)
    day_of_birth = models.IntegerField(null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Person {self.id} - {self.person_source_value}"


class VisitOccurrence(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    visit_concept_id = models.IntegerField(null=True, blank=True)
    visit_start_date = models.DateTimeField(null=True, blank=True)
    visit_end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Visit {self.id} for person {self.person_id}"


class ConditionOccurrence(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    condition_concept_id = models.IntegerField(null=True, blank=True)
    condition_start_date = models.DateTimeField(null=True, blank=True)
    condition_end_date = models.DateTimeField(null=True, blank=True)
    provider = models.ForeignKey(Provider, null=True, blank=True, on_delete=models.SET_NULL)
    condition_type_concept_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Condition {self.id} (person {self.person_id})"


class Observation(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    observation_concept_id = models.IntegerField(null=True, blank=True)
    value_as_number = models.FloatField(null=True, blank=True)
    value_as_concept_id = models.IntegerField(null=True, blank=True)
    value_as_string = models.TextField(null=True, blank=True)
    observation_datetime = models.DateTimeField(null=True, blank=True)
    provider = models.ForeignKey(Provider, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Observation {self.id} (person {self.person_id})"


class Measurement(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    measurement_concept_id = models.IntegerField(null=True, blank=True)
    value_as_number = models.FloatField(null=True, blank=True)
    measurement_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Measurement {self.id} (person {self.person_id})"


class FactRelationship(models.Model):
    domain_concept_id_1 = models.IntegerField(null=True, blank=True)
    domain_concept_id_2 = models.IntegerField(null=True, blank=True)
    fact_id_1 = models.IntegerField(null=True, blank=True)
    fact_id_2 = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"FactRel {self.id}: {self.fact_id_1} <-> {self.fact_id_2}"

from django.db import models

# Create your models here.

from django_dataclass_field.fields import DataClassField
from dataclasses import dataclass


@dataclass
class Car:
    brand: str
    model: str
    year: int
    color: str


class CarModel(models.Model):
    car_data = DataClassField(Car)

from django.contrib import admin

from car_app.models import CarModel

admin.site.site_header = "Car Project Admin"

admin.site.register(CarModel)

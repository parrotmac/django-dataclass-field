# django-dataclass-field

A simple and efficient way to have a typed Django JSON field using Dataclasses. Under the hood, it leverages the power of `dacite` to bring the magic of dataclasses to your Django models.

## Features

- Use Python's built-in dataclasses as a field type in Django models.
- Automatic serialization and deserialization using `dacite`.
- Strongly typed structure for your JSON fields simplifies working with JSON data in Django.

## Installation

### 1. Install the Package

Install the `django-dataclass-field` package via pip:

```
pip install django-dataclass-field
```

### 2. Update Django Settings

#### Update `INSTALLED_APPS`

Add `'django_dataclass_field'` to the `INSTALLED_APPS` list in your Django project's settings:

```python
INSTALLED_APPS = [
    ...
    'django_dataclass_field',
    ...
]
```

#### Update `TEMPLATES` Setting

Ensure that the `APP_DIRS` setting within the `TEMPLATES` configuration is set to `True`. This setting tells Django to look for templates in each app's `templates` directory:

```python
TEMPLATES = [
    {
        ...
        'APP_DIRS': True,
        ...
    },
]
```

### 3. Usage

With the package installed and settings updated, you can now proceed to use `DataClassField` in your Django models. Refer to the "Usage" section of this README for detailed examples and guidance.

## Quick Start

Let's consider a car-themed example. Assume you have a dataclass `Car`:

```python
from dataclasses import dataclass

@dataclass
class Car:
    brand: str
    model: str
    year: int
    color: str
```

Now, if you want to store this data structure in a Django model, you can simply use `DataClassField`:

```python
from django.db import models
from django_dataclass_field.fields import DataClassField

class CarModel(models.Model):
    car_data = DataClassField(Car)
```

With the above, the `car_data` field will automatically serialize instances of the `Car` dataclass into JSON when saving to the database, and will deserialize the JSON back into an instance of `Car` when reading from the database.

That's it! You're ready to bring strongly typed JSON fields into your Django projects. Happy coding! 🚗💨

## Usage

### Basic Usage

Following the earlier example, you can easily create new instances of `CarModel`:

```python
new_car = CarModel(car_data=Car(brand="Toyota", model="Prius", year=2022, color="red"))
new_car.save()
```

Retrieving the instance will give you access to the `Car` dataclass:

```python
retrieved_car = CarModel.objects.get(id=new_car.id)
print(retrieved_car.car_data.brand)  # Outputs: Toyota
```

### Querying

You can query the fields as you would with any other Django JSON field. For instance, to find all red Toyotas:

```python
red_Toyotas = CarModel.objects.filter(car_data__brand="Toyota", car_data__color="red")
```

## Dependencies

- Django
- dacite

## License

Licensed under either of

 * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
 * MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

## Contribution

We welcome contributions! Please open an issue or submit a pull request if you have any improvements or features to add.

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any
additional terms or conditions.

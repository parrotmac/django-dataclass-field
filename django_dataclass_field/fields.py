import dataclasses
import json
from enum import Enum
from typing import Any, Dict, Optional, Type

from dacite import Config, MissingValueError, from_dict
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import JSONField, Model
from django.forms.fields import InvalidJSONInput, JSONString
from django.forms.widgets import Widget


class JSONWidget(Widget):
    template_name = "admin/jsonwidget.html"
    is_hidden = False

    def __init__(self, attrs=None):
        default_attrs = {"cols": "40", "rows": "20"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class DataClassFormField(forms.JSONField):
    default_error_messages = {
        "invalid": "Enter valid JSON representation of the Dataclass."
    }
    widget = JSONWidget

    def __init__(self, encoder=None, decoder=None, **kwargs):
        self.encoder = encoder
        self.decoder = decoder
        schema = kwargs.pop("schema", None)
        self.widget = JSONWidget(attrs={"schema": json.dumps(schema)})
        super().__init__(**kwargs)

    def to_python(self, value):
        if self.disabled:
            return value
        if value in self.empty_values:
            return None
        elif isinstance(value, (list, dict, int, float, JSONString)):
            return value
        try:
            converted = json.loads(value, cls=self.decoder)
        except json.JSONDecodeError:
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )
        if isinstance(converted, str):
            return JSONString(converted)
        else:
            return converted

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        if data is None:
            return None
        try:
            return json.loads(data, cls=self.decoder)
        except json.JSONDecodeError:
            return InvalidJSONInput(data)

    def prepare_value(self, value):
        if dataclasses.is_dataclass(value):
            value = dataclasses.asdict(value)
        if isinstance(value, InvalidJSONInput):
            return value
        return json.dumps(value, ensure_ascii=False, cls=self.encoder)

    def has_changed(self, initial, data):
        if super().has_changed(initial, data):
            return True
        # For purposes of seeing whether something has changed, True isn't the
        # same as 1 and the order of keys doesn't matter.
        return json.dumps(initial, sort_keys=True, cls=self.encoder) != json.dumps(
            self.to_python(data), sort_keys=True, cls=self.encoder
        )


class DataClassField(JSONField):
    description = "Map Python Dataclasses to model fields."

    def formfield(self, **kwargs):
        try:
            kwargs["schema"] = generate_schema(self.data_class)
        except Exception:
            kwargs["schema"] = {}
        return super().formfield(
            **{
                "form_class": DataClassFormField,
                **kwargs,
            }
        )

    def value_to_string(self, obj: Any) -> Any:
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def __init__(self, data_class, *args, **kwargs):
        self.data_class = data_class
        super().__init__(*args, **kwargs)

    @property
    def non_db_attrs(self):
        return super().non_db_attrs + (
            "data_class",
        )  # type: ignore

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["data_class"] = self.data_class
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        from_db = super().from_db_value(value, expression, connection)
        if from_db is None:
            return from_db
        return from_dict(
            data_class=self.data_class, data=from_db, config=Config(cast=[Enum, Dict])
        )

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, self.data_class):
            return value
        if isinstance(value, str):
            obj = json.loads(value)
        else:
            obj = value
        try:
            return from_dict(data_class=self.data_class, data=obj)
        except ValidationError:
            raise ValidationError(
                message=f"Value must be of type {self.data_class.__name__}",
                code="invalid",
                params={"value": value},
            )
        except MissingValueError:
            raise ValidationError(
                message=f"Value must be of type {self.data_class.__name__}",
                code="invalid",
                params={"value": value},
            )

    def validate(self, value: Any, _: Optional[Model]) -> None:
        if value is None:
            return
        if isinstance(value, self.data_class):
            return
        raise ValidationError(
            message=f"Value must be of type {self.data_class.__name__}",
            code="invalid",
            params={"value": value},
        )

    def get_prep_value(self, value):
        """
        Called when saving to the database. Convert the value to a string.

        Since we are subclassing JSONField, our logic should focus on creating
        a JSON-serializable object from the dataclass, then passing it to the
        parent class to be serialized to a string.

        Args:
            value: The dataclass instance to be serialized.

        Returns: A value ready to be inserted into the database.
        """
        if value is None:
            return value
        if not isinstance(value, self.data_class):
            # validate that this is valid data for the dataclass
            self.to_python(value)
            return super().get_prep_value(value)
        # convert Python objects back to query values
        return super().get_prep_value(dataclasses.asdict(value))


def _lookup_scalar(type_hint: str) -> str:
    if type_hint == "str":
        return "string"
    elif type_hint == "int" or type_hint == "float":
        return "number"
    elif type_hint == "dict":
        return "object"
    elif type_hint == "list":
        return "array"
    elif type_hint == "bool":
        return "boolean"
    elif type_hint == "None":
        return "null"
    else:
        raise ValueError("Unhandled type: %s" % type_hint)


def parse_type(type_hint: str) -> Dict[str, Any]:
    try:
        if "|" in type_hint:
            types = [_lookup_scalar(t.strip()) for t in type_hint.split("|")]
            return {"anyOf": [{"type": t} for t in types]}

        if type_hint.startswith("Optional["):
            return {"type": _lookup_scalar(type_hint[9:-1])}

        if type_hint.startswith("List["):
            return {"type": "array", "items": {"type": _lookup_scalar(type_hint[5:-1])}}

        return {"type": _lookup_scalar(type_hint)}
    except ValueError:
        return {}

def generate_schema(dc: Type[dataclasses.dataclass]):  # type: ignore
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    for dc_key, dc_field in dc.__dataclass_fields__.items():  # type: ignore
        has_default_defined = type(dc_field.default) == dataclasses._MISSING_TYPE  # type: ignore

        if not has_default_defined:
            schema["properties"][dc_key] = parse_type(str(dc_field.type))  # type: ignore
            schema["properties"][dc_key]["default"] = dc_field.default  # type: ignore
        else:
            schema["properties"][dc_key] = parse_type(str(dc_field.type))  # type: ignore

        if dc_field.init:
            schema["required"].append(dc_key)  # type: ignore

    return schema

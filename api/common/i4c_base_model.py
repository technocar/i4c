from typing import Any
from pydantic import BaseModel, schema
from datetime import datetime
import pytz
from pydantic.fields import ModelField


class I4cBaseModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: v.astimezone(pytz.utc).replace(tzinfo=None).isoformat(timespec='milliseconds')+'Z'
        }


def field_schema(field: ModelField, **kwargs: Any) -> Any:
    if field.field_info.extra.get("hidden_from_schema", False):
        raise schema.SkipField(f"{field.name} field is being hidden")
    else:
        return original_field_schema(field, **kwargs)


original_field_schema = schema.field_schema
schema.field_schema = field_schema

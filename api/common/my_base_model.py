from pydantic import BaseModel
from datetime import datetime
import pytz


class MyBaseModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: v.astimezone(pytz.utc).replace(tzinfo=None).isoformat(timespec='milliseconds')+'Z'
        }

from pydantic import BaseModel


class PatchResponse(BaseModel):
    changed: bool

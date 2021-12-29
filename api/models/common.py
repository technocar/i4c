from pydantic import Field
from common import I4cBaseModel


class PatchResponse(I4cBaseModel):
    """Response from patch endpoints."""
    changed: bool = Field(..., title="Indicates if the conditions were met, thus the change was carried out.")

from typing import Optional, List
from pydantic import BaseModel


class SnapshotBase(BaseModel):
    pass


class Axis(BaseModel):
    pass


class MazakSnapshot(SnapshotBase):
    # todo 1: basic fields
    field1: Optional[str] = None

    #axes: List[Axis] = []

from enum import Enum


class MetaCategory(str, Enum):
    event = "EVENT"
    condition = "CONDITION"
    sample = "SAMPLE"

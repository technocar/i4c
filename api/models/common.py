from pydantic import Field
from common import I4cBaseModel


class PatchResponse(I4cBaseModel):
    """Response from patch endpoints."""
    changed: bool = Field(..., title="Indicates if the conditions were met, thus the change was carried out.")


def prev_iterator(iterable, *, include_first=True):
    prev = None
    include_next = include_first
    for current in iterable:
        if include_next:
            yield prev, current
        include_next = True
        prev = current


series_check_load_sql = open("models/series_check_load.sql").read()
series_check_load_extra_sql = open("models/series_check_load_extra.sql").read()


def check_rel(rel, left, right):
    if left is None:
        return False
    if right is None:
        return False
    if rel in ("=", "eq"):
        return left == right
    if rel in ("!=", "neq"):
        return left != right
    if rel in ("*", "in"):
        return left in right
    if rel in ("!*", "nin"):
        return left not in right
    if rel in ("<", "lt"):
        return left < right
    if rel in ("<=", "lte"):
        return left <= right
    if rel in (">", "gt"):
        return left > right
    if rel in (">=", "gte"):
        return left >= right
    return False

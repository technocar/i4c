import datetime
from enum import Enum


def deepdict(o, json_compat=False, hide_bytes=False):
    """
    Creates a dict of a variety of sources.
    As a general rule, if something has fields, it will be converted to dict, if something is enumerable, it will be
    converted to list. Enums are converted to their values.
    """
    if hide_bytes and isinstance(o, bytes):
        return "<bytes>"
    if isinstance(o, Enum):
        res = o.value
    elif isinstance(o, dict) or hasattr(o, "__dict__"):
        res = {k:deepdict(v, json_compat, hide_bytes) for (k,v) in dict(o).items()}
    elif isinstance(o, str):
        res = o
    elif hasattr(o, "__getitem__"):
        res = [deepdict(i, json_compat, hide_bytes) for i in o]
    else:
        if json_compat:
            if isinstance(o, datetime.date) or isinstance(o, datetime.time) or isinstance(o, datetime.datetime):
                res = o.isoformat()
            else: # TODO handle non-json types
                res = o
        else:
            res = o
    return res

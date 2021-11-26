import datetime
import math
from enum import Enum
from fractions import Fraction
from typing import List


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


def frac_index(list, index):
    i = math.floor(index)
    x = Fraction(index - i).limit_denominator()
    if x == 0:
        return list[i]
    return float(list[i]*(1-x) + list[i+1]*x)


def optimize_timestamp_label(l: List[datetime.datetime]) -> List[str]:
    """ It keeps at least the to most significant, non-equal part, but ensures to be unique """
    if len(l) <= 1:
        return [str(i) for i in l]
    ld = [(f"{dt.year}. ",
           f"{dt.month}. ",
           f"{dt.day} ",
           f"{dt.hour}:",
           f"{dt.minute}:",
           f"{dt.second}.",
           f"{dt.microsecond}*") for dt in l]

    def is_first_same():
        return len(set(d[0] for d in ld)) == 1

    def truncate_first(ld):
        return [d[1:] for d in ld]

    def is_unique(keep_cols:int):
        return len(set(d[:keep_cols+1] for d in ld)) == len(set(ld))

    while is_first_same():
        ld = truncate_first(ld)
    keep_cols = 2
    while not is_unique(keep_cols):
        keep_cols += 1
    return ["".join(i[:keep_cols+1])[:-1] for i in ld]


def test_optimize_timestamp_label():
    return [datetime.datetime(year=2021, month=11, day=25, hour=12, minute=34, second=11),
            datetime.datetime(year=2021, month=11, day=25, hour=12, minute=36, second=13),
            datetime.datetime(year=2021, month=11, day=25, hour=12, minute=36, second=13),
            datetime.datetime(year=2021, month=11, day=25, hour=12, minute=40, second=12),
            datetime.datetime(year=2021, month=11, day=26, hour=13, minute=34, second=11),
            ]

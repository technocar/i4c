import re
from functools import reduce
from typing import List, Optional, Any


def filter2regex(filters:List[str]) -> Optional[List[str]]:

    def get_regex(filter):
        if filter.startswith("|"):
            pre, filter = ".*?\\m", filter[1:]
        else:
            pre, filter = ".*?", filter

        if filter.endswith("|"):
            filter, post = filter[:-1], "\\M.*"
        else:
            filter, post = filter, ".*"

        filter = re.escape(filter)

        return f"{pre}{filter}{post}"

    if not filters:
        return None

    return [get_regex(w) for w in filters]


def filter2sql(filters:List[str], compaire_expr: str, params: List[Any], *, case_sensitive=False) -> str:
    fr = filter2regex(filters)
    if not fr:
        return ""

    def r(a,b):
        return f"{a} \nand {b}"

    rel = "~" if case_sensitive else "~*"
    startindex = len(params) + 1
    params.extend(fr)
    return reduce(r, [f"(({compaire_expr}) {rel} ${i})" for i, _ in enumerate(fr, start=startindex)])

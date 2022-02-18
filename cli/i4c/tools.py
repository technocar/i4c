import sys
import datetime
import json
import functools


class I4CException(Exception):
    message: str

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


@functools.wraps(json.dumps)
def jsonify(*pars, **kwpars):
    old_default = kwpars.get("default", None)

    def new_default(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat(timespec='milliseconds')
        if old_default is not None:
            return old_default(o)
        raise TypeError(f"Type {type(o)} not serializable")

    kwpars["default"] = new_default

    return json.dumps(*pars, **kwpars)


def resolve_file(fn):
    """
    Resolves filename parameter. @<file> will be read from file, - will read from stdin, otherwise the
    parameter itself is returned.
    """
    if fn == "@-":
        return sys.stdin.read()
    if fn is not None and fn.startswith("@"):
        with open(fn[1:], "r") as f:
            return f.read()
    return fn


def jsonbrief(o, inner=False):
    "Short string representation of a dict for logging purposes"
    if type(o) == dict:
        res = ", ".join([f"{k}:{jsonbrief(v, inner=True)}" for (k,v) in o.items()])
        if inner: res = f"{{{res}}}"
        return res
    elif type(o) == list:
        res = ",".join(jsonbrief(v, inner) for v in o)
        res = f"[{res}]"
        return res
    else:
        return f"{o}"



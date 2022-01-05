import sys
import datetime
import json
import functools


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
    if fn == "-":
        return sys.stdin.read()
    if fn is not None and fn.startswith("@"):
        with open(fn[1:], "r") as f:
            return f.read()
    return fn

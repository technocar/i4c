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

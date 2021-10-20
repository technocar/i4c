import re
from datetime import datetime

debug_mode = False


def set_debug_mode(value=True):
    global debug_mode
    debug_mode = value


def write_debug_sql(file_name, sql, params):
    def p(match):
        idx = int(match.group("num")) - 1
        p = params[idx]
        if isinstance(p, str):
            return "'" + p.replace("'","''") + "'" + match.group("rem")
        if isinstance(p, datetime):
            return "'" + str(p) + "'" + match.group("rem")
        return str(p) + match.group("rem")

    if not debug_mode:
        return

    regex = r"([$](?P<num>\d+))(?P<rem>\D|$)"
    r = re.sub(regex, p, sql, 0, re.MULTILINE)

    with open(file_name, "w") as f:
        f.write(r)
        print(f'File written to: {file_name}')

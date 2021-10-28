import os
import re
from datetime import datetime
from textwrap import dedent

debug_mode = False

debug_dir = 'debug'


def set_debug_mode(value=True):
    if value:
        if not os.path.isdir(debug_dir):
            return
    global debug_mode
    debug_mode = value


def param2sql_str(p):
    if isinstance(p, str):
        return "'" + p.replace("'", "''") + "'"
    if isinstance(p, datetime):
        return "'" + str(p) + "'"
    return str(p)


def param2sql_type(p):
    if isinstance(p, str):
        return f"character varying({len(p)})"
    if isinstance(p, datetime):
        return "timestamp"
    if isinstance(p, int):
        return "integer"
    if isinstance(p, float):
        return "double precision"
    return type(p).__name__


def debug_sql_replace(sql, *params):
    def p(match):
        idx = int(match.group("num")) - 1
        p = params[idx]
        return param2sql_str(p) + match.group("rem")

    if not debug_mode:
        return

    regex = r"([$](?P<num>\d+))(?P<rem>\D|$)"
    return re.sub(regex, p, sql, 0, re.MULTILINE)


def debug_sql_prepared(sql, *params):
    return dedent(
        f'-- DEALLOCATE plan;\n'
        f'PREPARE plan ({", ".join(param2sql_type(p) for p in params)}) AS\n'
        f'    {sql};\n\n'
        f'EXECUTE plan ({", ".join(param2sql_str(p) for p in params)});')


def write_debug_sql(file_name, sql, *params):
    file_name = debug_dir + '\\' + file_name
    with open(file_name, "w") as f:
        f.write(
            f'-- replaced\n'
            f'{debug_sql_replace(sql, *params)}\n\n'
            f'-- prepared\n'
            f'{debug_sql_prepared(sql, *params)}\n\n'
            f'-- orig\n'
            f'{sql}')
        print(f'File written to: {file_name}')

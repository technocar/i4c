import sys
import os
import io
import json
from copy import deepcopy
import jsonpath_ng.ext
import functools
import datetime
import logging
from .tools import I4CException
from click import ClickException

log = logging.getLogger("i4c")


class InputFormat:
    fmt = "tabular"
    tabular_type = "sep"
    encoding = "utf-8"
    sep = "tab"
    row_sep = "auto"
    col_names = []
    col_widths = []
    col_types = []
    header = False
    table_fmt = "table"


def load_table(f, fmt):
    """
    Load tabular text file as defined in the fmt parameter.
    :param f: an file-like object that is iterable and yields lines
    :param fmt: InputFormat configured to tabular
    :return: json-compatible array or dict
    """

    def split_line_fix(ln):
        return [ln[f:t] for (f,t) in col_slices]

    def split_line_sep_spaces(ln):
        return list(filter(None, ln.split(" ")))

    def split_line_sep_char(ln):
        return ln.split(split_char)

    f.reconfigure(newline={"cr": "\n", "lf": "\r", "crlf": "\n\r", "auto": None}[fmt.row_sep], encoding=fmt.encoding)

    if fmt.tabular_type == "sep":
        if fmt.sep == "spaces":
            split_line = split_line_sep_spaces
        else:
            if fmt.sep == "none":
                split_line = (lambda ln: [ln])
            else:
                split_char = {"tab":"\t", "space":" ", "comma": ",", "semicolon": ";"}[fmt.sep]
                split_line = split_line_sep_char
    else:
        if None in fmt.col_widths:
            none_pos = fmt.col_widths.index(None)
            col_bounds = \
                [sum(fmt.col_widths[:n]) for n in range(0, none_pos+1)] + \
                [-sum(fmt.col_widths[n:]) for n in range(none_pos+1, len(fmt.col_widths))] + \
                [None]
        else:
            col_bounds = [sum(fmt.col_widths[:n]) for n in range(len(fmt.col_widths)+1)]
        col_slices = list(zip(col_bounds[:-1], col_bounds[1:]))
        split_line = split_line_fix

    if fmt.header:
        line = next(f, None)
        if line is None: raise Exception("Expected header not found")
        if line.endswith("\n"): line = line[:-1]
        if line.endswith("\r"): line = line[:-1]
        header = split_line(line)
        col_names = [None] * max(len(header), len(fmt.col_names))
        for i, n in enumerate(header):
            col_names[i] = n
        for i, n in enumerate(fmt.col_names):
            if n:
                col_names[i] = n
    else:
        col_names = list(fmt.col_names)

    for (i, n) in enumerate(col_names):
        if n is None:
            col_names[i] = f"c{i+1}"

    def add_line_rows(row, data):
        cols = col_names or (f"c{n+1}" for n in range(len(row)))
        data.append({n: v for (n, v) in zip(cols, row)})

    def add_line_row1(row, data):
        if len(data) == 0:
            data.extend(row)

    def add_line_columns(row, data):
        for i, c in enumerate(col_names):
            data[c].append(row[i])

    def add_line_column1(row, data):
        data.append(row[0])

    def add_line_table(row, data):
        data.append(row)

    if fmt.table_fmt == "rows":
        data = []
        add_line = add_line_rows
    elif fmt.table_fmt == "row1":
        data = []
        add_line = add_line_row1
    elif fmt.table_fmt == "columns":
        data = {c:[] for c in col_names}
        add_line = add_line_columns
    elif fmt.table_fmt == "column1":
        data = []
        add_line = add_line_column1
    else:
        data = []
        add_line = add_line_table

    for ln in f:
        if ln.endswith("\n"): ln = ln[:-1]
        if ln.endswith("\r"): ln = ln[:-1]
        row = split_line(ln)
        for i, t in enumerate(fmt.col_types):
            if t == "i": row[i] = int(row[i])
            elif t == "f": row[i] = float(row[i])
            elif t == "isodt": row[i] = datetime.datetime.fromisoformat(row[i])
            # TODO we need to support datetimes better
        add_line(row, data)

    return data


def format_attrs(s, default: InputFormat = None):
    """
    Takes a format definition string or enumerable of strings, and returns format object.

    :param s: String or string list, with dot-separated format descriptors
    :param default: a prototype object which will be overwritten and returned.
    :return: an InputFormat object with all the fields filled in
    """
    f = default or InputFormat()
    if isinstance(s, str):
        s = (s,)
    for i in s:
        for e in i.split("."):
            if e == "csv":
                f.fmt = "tabular"
                f.tabular_type = "sep"
                f.sep = "comma"
            elif e == "str":
                f.fmt = "str"
            elif e == "lines":
                f.fmt = "tabular"
                f.tabular_type = "sep"
                f.sep = "none"
                f.table_fmt = "column1"
            elif e == "sep" or e == "fix":
                f.fmt = "tabular"
                f.tabular_type = e
            elif e == "json" or e == "xml":
                f.fmt = e
            elif e in ("comma", "tab", "semicolon", "space", "spaces", "none"):
                f.sep = e
            elif "=" in e:
                (n, _, w) = e.partition("=")
                if n == "": n = None
                if w == "": w = None
                f.col_names.append(n)
                first_alpha = w and next((i[0] for i in enumerate(w) if not i[1].isnumeric()), None)
                if first_alpha is None:
                    t = None
                else:
                    t = w[first_alpha:]
                    w = w[:first_alpha]
                w = w and int(w)
                f.col_widths.append(w)
                f.col_types.append(t)
            elif e == "header":
                f.header = True
            elif e == "noheader":
                f.header = False
            elif e in ("cr", "lf", "crlf", "auto"):
                f.row_sep = e
            elif e.startswith("enc"):
                f.encoding = e[3:]
            elif e in ("rows", "columns", "table", "row1", "column1"):
                f.table_fmt = e
            elif e == "trimcells":
                f.trim_cells = True
            elif e == "notrimcells":
                f.trim_cells = False

    if f.fmt == "tabular" and f.tabular_type == "fix":
        if len(f.col_names) == 0:
            raise ClickException("No columns specified for fixed text format.")
        if len([_ for w in f.col_widths if w is None]) > 1:
            raise ClickException("Only one column can have flexible width for fixed text format.")
    return f


def parse_assignment(expr):
    escape = False
    eq_sign = None
    in_str = False
    in_dstr = False
    depth = 0
    for (i, c) in enumerate(expr):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if not in_str and c == "\"":
            in_dstr = not in_dstr
            continue
        if not in_dstr and c == "'":
            in_str = not in_str
            continue
        if in_str or in_dstr:
            continue
        if c == "[":
            depth = depth + 1
            continue
        if c == "]":
            depth = depth - 1
            continue
        if c == "=" and depth == 0:
            eq_sign = i
            break
    if eq_sign is not None:
        if expr[eq_sign-1] == "*":
            return expr[:eq_sign-1], "*=", expr[eq_sign+1:]
        else:
            return expr[:eq_sign], "=", expr[eq_sign+1:]
    else:
        return expr, "=", None


def process_input(args, body, input_data, input_format, input_foreach, input_placement):
    """
    Processes input parameters, and creates an array of arguments/bodies from the
    provided templates. Even if input_foreach is omitted, the function returns an
    array, with a single element.

    :param args: a list of arguments.
    :param body: body template.
    :param input_data: input data.
    :param input_format: format string.
    :param input_foreach: split jsonpath.
    :param input_placement: assignments.
    :return: a list of bodies.
    """

    if body is None:
        if input_data is not None:
            body = {}
    elif isinstance(body, str):
        body = json.loads(body)
    else:
        body = dict(body)

    d = InputFormat()
    if input_data:
        if not input_data.startswith("@"):
            d.fmt = "str"
        else:
            _, ext = os.path.splitext(input_data[1:])
            if ext == ".csv":
                d.separator = "comma"
            elif ext.lower() in (".json", ".xml"):
                d.fmt = ext.lower()
    attr = format_attrs(input_format, default=d)

    if input_data == "@-":
        if attr.fmt == "xml":
            raise Exception("Not implemented") # TODO we need to pick a module. etree is kinda shit
        elif attr.fmt == "json":
            ext = json.load(sys.stdin)
        elif attr.fmt == "tabular":
            ext = load_table(sys.stdin, attr)
        elif attr.fmt == "str":
            ext = sys.stdin.read()
            if ext.endswith("\n"):
                ext = ext[:-1]
    elif input_data is not None and input_data.startswith("@"):
        input_data = input_data[1:]
        if attr.fmt == "xml":
            raise Exception("Not implemented") # TODO we need to pick a module. etree is kinda shit
        elif attr.fmt == "json":
            with open(input_data, "r") as f:
                ext = json.load(f)
        elif attr.fmt == "tabular":
            with open(input_data, "r") as f:
                ext = load_table(f, attr)
        elif attr.fmt == "str":
            with open(input_data, "r") as f:
                ext = f.read()
            if ext.endswith("\n"):
                ext = ext[:-1]
    elif input_data is not None:
        if attr.fmt == "xml":
            raise Exception("Not implemented") # TODO we need to pick a module. etree is kinda shit
        elif attr.fmt == "json":
            ext = json.loads(input_data)
        elif attr.fmt == "tabular":
            with io.TextIOWrapper(io.BytesIO(input_data.encode())) as f:
                ext = load_table(f, attr)
        elif attr.fmt == "str":
            ext = input_data
    else:
        ext = None
        
    if not input_placement and input_data:
        input_placement = ["$"]

    input_placement = input_placement or []

    input_foreach = input_foreach or "$"
    foreach = jsonpath_ng.ext.parse(input_foreach)
    items = [i.value for i in foreach.find(ext)]

    bodies = []
    argses = []
    for item in items:
        body_copy = deepcopy(body)

        def arg_ref(par, val):
            if not par.startswith("__"):
                return par, val
            val = jsonpath_ng.ext.parse(val).find(item)
            if len(val) != 1:
                raise I4CException("Parameter path must return a (singular) value.")
            return par[2:], val[0].value

        args_copy = dict(arg_ref(k, v) for (k, v) in args.items())
        argses.append(args_copy)

        for p in input_placement:
            placement, op, expr = parse_assignment(p)

            if not placement or placement == "$":
                placement = None
            else:
                placement = jsonpath_ng.ext.parse(placement)

            if attr.fmt == "xml":
                raise Exception("not impl") #TODO
            else:
                expr = expr or "$"
                expr = jsonpath_ng.ext.parse(expr)
                matches = expr.find(item)
                if matches:
                    if op == "*=" or len(matches) > 1:
                        piece = [m.value for m in matches]
                    else:
                        piece = matches[0].value
                else:
                    piece = None

                if placement is None:
                    body_copy = piece
                elif isinstance(piece, list):
                    placements = placement.find(body_copy)
                    if len(placements) == len(piece):
                        for tgt, src in zip(placements, piece):
                            tgt.full_path.update_or_create(body_copy, src)
                    elif len(placements) <= 1:
                        placement.update_or_create(body_copy, piece)
                    else:
                        raise I4CException(f"There are {len(piece)} inputs and {len(placements)} placements.")
                else:
                    placement.update_or_create(body_copy, piece)
        bodies.append(body_copy)

    return argses, bodies

import sys
import jinja2
import json
import jsonpath_ng.ext
import isodate
import logging
import click
import click.formatting
from .tools import jsonify, resolve_file

log = logging.getLogger("i4c")


def localize_time(time):
    if time is None:
        return None

    if isinstance(time, str):
        try:
            time = isodate.parse_datetime(time)
        except Exception as e:
            log.debug(f"can't parse time: {time}")
            return "???"

    newtime = time.astimezone()
    return newtime


def format_time(time, format_str=None):
    if time is None:
        return None

    if isinstance(time, str):
        try:
            time = isodate.parse_datetime(time)
        except Exception as e:
            log.debug(f"can't parse time: {time}")
            return "???"

    try:
        format_str = format_str or "%c"
        s = time.strftime(format_str)
    except Exception as e:
        log.debug(f"time format string bad: {format_str}")
        return "???"

    return s


def make_jinja_env():
    env = jinja2.Environment(block_start_string="{-", block_end_string="-}")
    env.filters["json_dumps"] = json.dumps
    env.filters["jd"] = json.dumps
    env.filters["format_time"] = format_time
    env.filters["ft"] = format_time
    env.filters["tzloc"] = localize_time
    return env


ctrlchars = ["nul", "soh", "stx", "etx", "eot", "enq", "ack", "bel",
             "bs", "tab", "lf", "vt", "ff", "cr", "so", "si",
             "dle", "dc1", "dc2", "dc3", "dc4", "nak", "syn", "etb",
             "can", "em", "sub", "esc", "fs", "gs", "rs", "us"]


def process_json(response, outexpr, outfile, template):
    log.debug(f"process_json")
    if outexpr:
        log.debug(f"search jsonpath")
        outexpr = jsonpath_ng.ext.parse(outexpr)
        items = [match.value for match in outexpr.find(response)]
        log.debug(f"found {len(items)} items")
    else:
        items = [response]

    if outfile == "-":
        outfile = None

    if outfile or template:
        env = make_jinja_env()
        if outfile:
            outfile = env.from_string(outfile)
        if template:
            template = resolve_file(template)
            template = env.from_string(template)

    for item in items:
        if not isinstance(item, dict):
            itemdict = {"value": item}
        else:
            def sanitize(s):
                s = s.replace("-", "_")
                return s
            itemdict = {sanitize(k): v for (k,v) in item.items()}

        if template:
            for (code, name) in enumerate(ctrlchars):
                itemdict[name] = chr(code)
            itemdict["nl"] = "\n"
            item_str = template.render(itemdict)
        else:
            if isinstance(item, dict):
                item_str = jsonify(item, indent=2)
            else:
                item_str = str(item)
            item_str = item_str + "\n"

        if not outfile:
            sys.stdout.write(item_str)
        else:
            fn = outfile.render(itemdict)
            log.debug(f"writing item to {fn}")
            with open(fn, "w") as f:
                f.write(item_str)


def print_table(table):
    if len(table) == 0:
        return

    cols = max(len(r) for r in table)

    if cols == 0:
        return

    colw = [max(len(r[c]) for r in table) for c in range(cols)]

    # for now, we make two space gaps, and the last column will autosize and wrap
    # but for safety, we set a minimum of 10 character width for the last column
    lastcol = sum(colw[:-1]) + 2*cols - 2
    lastcolw = 78 - lastcol
    if lastcolw < 10: lastcolw = 10

    for row in table:
        lastcell = row[-1].strip()
        lastcell = click.formatting.wrap_text(lastcell, width=lastcolw, preserve_paragraphs=True)
        lastcellrows = lastcell.split("\n")
        line = "  ".join(cell.ljust(w) for (cell, w) in zip(row[:-1], colw))
        click.echo(line + "  " + lastcellrows[0])
        for lastcellrow in lastcellrows[1:]:
            line = " "*lastcol + lastcellrow
            click.echo(line)
        if len(lastcellrows) > 1:
            click.echo()

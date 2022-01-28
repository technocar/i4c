import os.path
import re
import sys
import datetime
from functools import wraps
import json
import yaml
import logging.config
import click.globals
from .apidef import I4CDef
from .conn import I4CConnection, HTTPError
from .outputproc import print_table, process_json, make_jinja_env
from .inputproc import assemble_body
from .tools import resolve_file
from difflib import SequenceMatcher

log = None # will be set from main


def stream_copy(src, dst):
    "This will pump data from a stream to another, used to download from http to file/stdout."
    buf = src.read(0x10000)
    while buf:
        dst.write(buf)
        buf = src.read(0x10000)


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


@click.group()
def top_grp():
    pass


def json_options(f):
    # TODO this is now DRY but not super-DRY. dynamic command creation uses its own version
    "This macro adds json output processing Click options"
    @click.option("--output-expr", help="Jsonpath expression to apply to the response. "
                                        "The returned items will be separately processed by "
                                        "--output-file and --output-template. If omitted, the entire result will be one item.")
    @click.option("--output-file", help="Output file name or jinja template. "
                                        "If a template is given, it will be evaluated "
                                        "against each data item (see --output-expr). If omitted or -, stdout is used.")
    @click.option("--output-template", help="Jinja template to process data items "
                                            "before printed or written to a file. If omitted, raw json will be written.")
    @wraps(f)
    def newf(*a, **kw):
        return f(*a, **kw)

    return newf


def callback(ctx, **args):
    # This is the main Click callback that performs the API call
    log.debug(f"callback {args}")

    ep = args.pop("_ep")
    path = ep["path"]
    method = ep["method"]
    action = ep["action"]

    # process body
    if "body" in args:
        body = args.pop("body")
        body = resolve_file(body)

        input_data = args.get("input_data", None)
        input_format = args.get("input_format", None)
        input_placement = args.get("input_placement", None)
        body = assemble_body(body, input_data, input_format, input_placement)
        if isinstance(body, str):
            body = body.encode("utf-8")
    else:
        body = None

    if args.get("print_curl", False):
        raise Exception("Not implemented") # TODO

    response = action.invoke(**args, body=body)

    output_file = args.get("output_file", None)
    output_expr = args.get("output_expr", None)
    output_template = args.get("output_template", None)

    if action.response and action.response.content_type == "application/json":
        process_json(response, output_expr, output_file, output_template)
    else:
        origin_file_name = response.headers.get_filename()
        if output_expr or output_template:
            click.ClickException("Can't apply expression or template to non-json responses")
        if not output_file:
            log.debug(f"streaming to stdout")
            stream_copy(response, sys.stdout.buffer)
        else:
            env = make_jinja_env()
            output_file = env.from_string(output_file)
            output_file = output_file.render({"origin": origin_file_name})
            log.debug(f"writing to file {output_file}")
            with open(output_file, "wb") as f:
                stream_copy(response, f)


def make_callback(**outer_args):
    """
    Create a closure that takes a Click context, outer_args and any number of actual arguments defined in OpenAPI doc,
    and calls `callback`. The closure also handles exceptions.
    """
    def f(**args):
        try:
            res = callback(click.globals.get_current_context(), _ep=outer_args, **args)
        except click.ClickException as e:
            raise
        except HTTPError as e:
            body = e.read()
            if e.headers["Content-Type"] == "application/json":
                body = json.loads(body)
                if "detail" in body:
                    body = body["detail"]
            if body:
                if isinstance(body, bytes):
                    body = body.decode()
                if isinstance(body, list):
                    body = ", " + "\n".join(jsonbrief(row) for row in body)
                else:
                    body = ", " + jsonbrief(body)
            raise click.ClickException(f"Server reported {e.code} {e.msg}{body}")
        except Exception as e:
            error_type = None if type(e) == Exception else type(e).__name__
            msg = getattr(e, "message", None)
            msg = msg or ", ".join((str(i) for i in getattr(e, "args", None)))
            msg = msg or getattr(e, "__str__", None)
            msg = msg or ""
            raise click.ClickException(" ".join(filter(None, (error_type, msg))))
        return res
    return f


class TZDateTime(click.ParamType):
    name = "iso timestamp"

    def convert(self, value, param, ctx):
        if isinstance(value, str):
            try:
                m = re.fullmatch(r"(\d\d\d\d)-(\d\d)-(\d\d)(T(\d\d)(:(\d\d)(:(\d\d)(\.(\d{1,6}))?)?)?(Z|([+-])(\d\d)(:(\d\d))?)?)?", value)
                if m is None:
                    self.fail(f"Not recognized date format: {value}.", param=param, ctx=ctx)
                y, m, d, _, h, _, n, _, s, _, us, zz, zsgn, zh, _, zm = m.groups()
                y, m, d, h, n, s, zh, zm = (int(i) if i is not None else 0 for i in (y, m, d, h, n, s, zh, zm))
                if us is not None:
                    us = int(us.ljust(6, "0"))
                else:
                    us = 0
                if zz == "Z" or zz == "z":
                    tz = datetime.timezone.utc
                elif zsgn is not None:
                    if zm is None: zm = 0
                    zsgn = -1 if zsgn == "-" else 1
                    zh = zsgn * zh
                    zm = zsgn * zm
                    tz = datetime.timezone(datetime.timedelta(hours=zh, minutes=zm))
                else:
                    tz = None
                value = datetime.datetime(y, m, d, h, n, s, microsecond=us, tzinfo=tz)
            except Exception as e:
                self.fail(f"{e}", param=param, ctx=ctx)

        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            value = value.astimezone()

        return value


def make_commands(conn: I4CConnection):
    """
    Make click Groups and Commands based on command_mapping, which is derived from openapi.json
    """
    log.debug(f"make_commands, get api")

    api_def = conn.api_def()

    for (obj_name, obj) in api_def.objects.items():
        log.debug(f"make_commands, processing obj {obj_name}")
        if len(obj.actions) == 1:
            grp = top_grp
        else:
            # TODO could figure out some way to explain an object
            help = ", ".join(obj.actions)
            grp = click.Group(obj_name, help=help)
            top_grp.add_command(grp)

        for (action_name, action) in obj.actions.items():
            log.debug(f"make_commands, processing action {action_name}")
            params = []
            for param_name, param in action.params.items():
                param_decl = "--" + param_name.replace("_", "-")
                attrs = {}
                attrs["multiple"] = param.is_array
                attrs["required"] = param.required
                if param.type == "integer":
                    attrs["type"] = click.INT
                elif param.type == "number":
                    attrs["type"] = click.FLOAT
                elif param.type == "boolean":
                    attrs["type"] = click.BOOL
                elif param.type == "string" and param.type_fmt == "date-time":
                    attrs["type"] = TZDateTime()
                elif param.type_enum:
                    attrs["type"] = click.Choice(param.type_enum)

                paramhelp = param.description or param.title
                paramhelp = paramhelp or (param_name.replace("_", " ").capitalize() + "." +
                                (" Multiple values allowed." if param.is_array else ""))
                attrs["help"] = paramhelp

                params.append(click.Option((param_decl,), **attrs))

            if action.body:
                attrs = {}
                attrs["required"] = action.body.required

                helpstr = ""
                if action.body.sch_obj:
                    helpstr = f"Use the `doc {action.body.sch_obj}` command to get the definition. "
                helpstr = helpstr + "Use @filename to read from a file, or @- to read from stdin."
                attrs["help"] = helpstr

                params.append(click.Option(("--body",), **attrs))

                params.append(click.Option(("--input-data",),
                    help="The data which will be processed and inserted to the body according to the other "
                         "--input-* options. Use @filename to read from a file, or @- to read from stdin."))

                params.append(click.Option(("--input-placement",), multiple=True,
                    help="Specifies where the input should be placed into the body, and optionally what part of the "
                         "input. If only a <jsonpath> is given, the input will be written at that location. If "
                         "<jsonpath1>=<jsonpath2> is used, the second expression will be extracted from the input, and "
                         "placed where indicated by the first expression. The target must exist. E.g.:\xa0$.name=$[0][1]."))

                params.append(click.Option(("--input-format",), multiple=True,
                    help="Specifies a format attribute. If omitted, the format will be derived from the file extension. "
                         "Attributes are separated by `.`, or you can specify multiple options, which will be combined. "
                         "For a detailed explanation on data input and transformations, see the transform command."))

            if action.authentication == "basic":
                params.append(click.Option(("--profile",), help="The name of the saved profile to use"))
                params.append(click.Option(("--auth-user",), help="User name for authentication"))
                params.append(click.Option(("--auth-pwd",), help="Password for basic authentication"))
                params.append(click.Option(("--auth-key",), help="Private key for signed timestamp authentication"))

            # params.append(click.Option(("--print-curl",), is_flag=True,
            #    help="Instead of executing, print a CURL command line. Please note that sensitive information will be "
            #        "included in the result. Also note that signature based authentication expires in 60 seconds."))

            if action.response:
                if action.response.content_type == "application/json":
                    params.append(click.Option(("--output-expr",),
                        help="Jsonpath expression to apply to the response. The returned items will be separately processed by " \
                             "--output-file and --output-template. If omitted, the entire result will be one item."))
                    params.append(click.Option(("--output-file",),
                        help="Output file name or jinja template. If a template is given, it will be evaluated " \
                             "against each data item (see --output-expr). If omitted or -, stdout is used. " \
                             "If the response contains file name, it can be referred to as {{origin}}"))
                    params.append(click.Option(("--output-template",),
                        help="Jinja template to process data items before printed or written to a file. If omitted, raw " \
                              "json will be written."))
                else:
                    params.append(click.Option(("--output-file",),
                        help="Output file name. If omitted or -, stdout is used."))

            callback = make_callback(path=action.path, method=action.method, action=conn[obj_name][action_name])
            cmd_name = action_name if len(obj.actions) > 1 else obj_name
            cmd = click.Command(cmd_name, callback=callback, params=params, help=action.help(), short_help=action.short_help())
            grp.add_command(cmd)


@top_grp.group("profile", help="Manage saved profiles")
def profile():
    pass


@profile.command("get", help="Gets all fields of a profile, or the default one if no name is given. "
    "Sensitive fields are redacted.")
@click.option("--name", help="The profile name to read")
@json_options
@click.pass_context
def profile_get(ctx, name, output_expr, output_file, output_template):
    log.debug(f"profile_get")
    conn = ctx.obj["connection"]
    profiles = conn.profiles()
    if name:
        profile = next((profile for profile in profiles if profile["profile"] == name), None)
        if profile is None:
            raise click.ClickException("Profile does not exist")
    else:
        profile = next((profile for profile in profiles if profile["default"]), None)
        if profile is None:
            raise click.ClickException("No default profile set up")

    process_json(profile, output_expr, output_file, output_template)


@profile.command("new-key", help="Creates a new key pair for the profile, and displays the public key")
@click.option("--name", help="The profile name to modify. Must exist.")
@click.option("--override", is_flag=True, help="If the profile has a key already, replace it. The old key is deleted.")
@click.pass_context
def profile_new_key(ctx, name, override):
    log.debug(f"profile_new_key")
    conn = ctx.obj["connection"]
    pubkey = conn.profile_new_key(name, override)
    click.echo(pubkey)


@profile.command("save", help="Creates or modifies a profile")
@click.option("--name", help="Name of the profile. Can not be 'default'. If omitted, the default profile will be modified.")
@click.option("--base-url", help="Base url.")
@click.option("--api-def-file", help="Name of openapi definition file. If not set, will be downloaded from the server.")
@click.option("--del-api-def-file", is_flag=True, help="If provided, the openapi-def setting will be removed from the profile.")
@click.option("--user", help="The value of the user-name used for authentication. If omitted, the profile name will be used.")
@click.option("--password", help="The value of the password for authentication or . to prompt.")
@click.option("--del-password", is_flag=True, help="If provided, the password will be removed from the profile.")
@click.option("--del-private-key", is_flag=True, help="If provided, the private key will be removed from the profile.")
@click.option("--clear-extra", is_flag=True, help="If provided, all extra information will be removed.")
@click.option("--extra", multiple=True, help="Add/merge extra information. Extra information has name=value format, and"
                                             "it is stored with the profile, but otherwise not used. If value is"
                                             "omitted, the information is deleted. Multiple instances allowed.")
@click.option("--override", is_flag=True, help="If the profile exists, it will be modified.")
@click.option("--make-default", is_flag=True, help="Make the profile default")
@click.pass_context
def profile_save(ctx, name, base_url, api_def_file, del_api_def_file, user, password, del_password, del_private_key,
                 clear_extra, extra, override, make_default):
    log.debug(f"profile_save")
    conn = ctx.obj["connection"]
    if password == ".":
        password = click.termui.prompt("Password", hide_input=True, confirmation_prompt=True)
    try:
        if extra is not None:
            extra = dict((lambda x: (x[0], x[2] or None))(i.partition("=")) for i in extra)

        conn.write_profile(name=name, base_url=base_url, api_def_file=api_def_file, del_api_def_file=del_api_def_file,
                           user=user, password=password, del_password=del_password, del_private_key=del_private_key,
                           clear_extra=clear_extra, extra=extra,
                           override=override, make_default=make_default)
    except Exception as e:
        raise click.ClickException(f"{e}")


@profile.command("list", help="Gives back all existing profiles. Sensitive fields will be redacted.")
@click.option("--user-name", help="Filter by user name.")
@click.option("--has-password", is_flag=True, help="Only password authenticated.")
@click.option("--has-key", is_flag=True, help="Only public key authenticated.")
@click.option("--base-url", help="Base URL contains substring.")
@json_options
@click.pass_context
def profile_list(ctx, user_name, has_password, has_key, base_url, output_expr, output_file, output_template):
    log.debug(f"profile_list")
    conn = ctx.obj["connection"]
    data = conn.profiles()
    if user_name:
        data = [i for i in data if i["user"] == user_name]
    if has_password:
        data = [i for i in data if i["password"]]
    if has_key:
        data = [i for i in data if i["public-key"]]
    if base_url:
        data = [i for i in data if base_url in i.get("base-url", "")]
    process_json(data, output_expr, output_file, output_template)


@profile.command("delete", help="Permanently deletes the profile. Irreversible!")
@click.option("--name", help="The profile name to delete.")
@click.pass_context
def profile_delete(ctx, name):
    log.debug(f"profile_delete")
    if name == "default":
        raise click.ClickException("'default' is not valid profile name.")
    conn = ctx.obj["connection"]
    if not conn.delete_profile(name):
        raise click.ClickException("Profile does not exist")


@top_grp.command("doc")
@click.argument("schema", required=False)
@click.option("--raw", is_flag=True, default=False)
@json_options
@click.pass_context
def doc(ctx, schema, raw, output_expr, output_file, output_template):
    """
    Output OpenAPI definition. If schema is specified, only that schema is displayed. The names of
    the schemas are used in parameters, especially --body parameters, which almost always take a schema.

    If no output-expr and output-template is specified, a human readable formatting is provided.
    If you want the raw format, use --raw or specify output-expr as $.
    """

    log.debug(f"doc")
    conn = ctx.obj["connection"]

    if output_expr or output_template or raw:
        if schema:
            obj = conn.api_def().content["components"]["schemas"].get(schema, None)
            if obj is None:
                raise click.ClickException("Schema does not exist.")
        else:
            obj = conn.api_def().content

        if not output_expr and not output_template:
            output_expr = "$"

        process_json(obj, output_expr, output_file, output_template)
        return

    if schema:
        sch = conn.api_def().schema.get(schema, None)
        if sch is None:
            click.echo("No such schema exists.")
            similars = [f"  {k}" for k in conn.api_def().schema.keys() if SequenceMatcher(None, k, schema).ratio() > 0.6]
            partials = [f"  {k}" for k in conn.api_def().schema.keys() if schema in k]
            candidates = similars + partials
            if candidates:
                click.echo("Closest candidates are:")
                click.echo("\n".join(candidates))
            return
        click.echo(schema)
        click.echo()
        desc = sch.describe()
        if sch.type == "object":
            desc = desc + " Mandatory fields marked with\xa0*."
        desc = click.formatting.wrap_text(desc, preserve_paragraphs=True)
        click.echo(desc)
        click.echo()
        if sch.type == "object":
            # there is no way to preserve the order, because fastAPI already messes it up. sorting alphabetically.
            table = [[("*" if v.required else "") + k, v.type_desc(), v.describe(brief=True)]
                     for (k, v) in sorted(sch.properties.items(), key=lambda p: p[0])]
            click.echo("Fields:")
            print_table(table)
        elif sch.type_enum is not None:
            desc = f"It is a {sch.type} with possible values:"
            desc = click.formatting.wrap_text(desc, preserve_paragraphs=True)
            click.echo(desc)
            for op in sch.type_enum:
                click.echo(f"  {op}")
        else:
            click.echo(f"It is of type {sch.type}")
    else:
        click.echo("Commands and paths:")
        paths = [[obj_name, act_name if len(obj.actions) > 1 else "", f"{act.method.upper()} {act.path}"]
                 for (obj_name, obj) in conn.api_def().objects.items()
                 for (act_name, act) in obj.actions.items()]
        print_table(paths)
        click.echo()
        click.echo("Schemas:")
        schemas = ", ".join(conn.api_def().schema.keys())
        schemas = click.formatting.wrap_text(schemas, preserve_paragraphs=True)
        click.echo(schemas)

@top_grp.command("transform")
@click.option("--body")
@click.option("--input-data", help="The data which will be processed according to the other "
    "--input-* options. Use @filename to read from a file, or @- to read from stdin.")
@click.option("--input-format", multiple=True, help=
    "Specifies a format attribute. If omitted, the format will be derived from the file extension. "
    "Attributes are separated by `.`, or you can specify multiple options, which will be combined.")
@click.option("--input-placement", multiple=True, help=
    "Specifies where the input should be placed into the body, and optionally what part of the "
    "input. If only a <jsonpath> is given, the input will be written at that location. If "
    "<jsonpath1>=<jsonpath2> is used, the second expression will be extracted from the input, and "
    "placed where indicated by the first expression. The target must exist. E.g.:\xa0$.name=$[0][1].")
@json_options
def transform(body, input_data, input_format, input_placement, output_expr, output_file, output_template):
    """
    Short circuited data input-output command. Data will be read and processed the same way as for all commands with a
    --body option. Then the assembled data package will be formatted for output like a json response. This can be used
    to test input transformations, or to pre-process real data into files or piping. The command is executed locally,
    no data is transmitted to the API.

    The input formatting works as follows. The base or skeleton of the resulting data structure is given in --body.
    The format is json. Raw value can be given in-place, a file can be referred as @filename, or stdin can be used
    by specifying a single `-` character.

    The input file can be json, xml or a tabular text file that is processed into a json object according to the
    --input-format attributes. If --input-format is not given, the following defaults will be used based on the
    extension (see the description of formatting options below):

    \b
    csv -> sep.comma.noheaeder.table
    txt -> sep.tab.noheader.table
    json -> json
    xml -> xml

    The attributes can be written in any order, and can be dot-separated or given in separate options. If multiple
    options are given, they will be combined. The attributes are as follows.

    File type attributes:

    \b
    sep -> separated tabular text file
    csv -> shorthand for sep.comma
    txt -> shorthand for sep.tab
    fix -> fixed width tabular text file
    json -> json
    xml -> xml
    str -> a single string value

    For separated files, the following attributes can be used:

    \b
    tab -> tab delimited
    comma -> comma delimited
    semicolon -> semicolon delimited
    space -> space delimited, every space is a delimiter
    spaces -> space delimited, consecutive spaces are considered as one

    For fixed width data, the column widths are defined with:

    # TODO

    For tabular data, the following attributes can be used:

    \b
    cr|lf|crlf|auto -> Specifies the row separator.
    [no]header -> The first row contains or does not contain a header.
    [no]trimcells -> Weather to strip each data cell from leading/trailing whitespace.
    enc<codepage> -> Code page. E.g. enccp1252 or encansi. Default is utf8.
    rows -> The file is processed into an array of rows, rows are json objects.
    row1 -> The first row will be returned as an array of values. The rest is ignored.
    columns -> The file is processed into a json in which all columns are arrays.
    column1 -> The first column of each row is collected to an array. The rest of the row is ignored.
    table -> The file is processed into an array of arrays t[row][column].

    If omitted, attributes have defaults. If the input is a file or stdin, the default is:

    sep.tab.auto.noheader.notrimcells.table

    If the input is direct, the default is `str`.

    Once the data is loaded processed, elements of it can be inserted into the body skeleton. The insertion is done
    with the --input-place option. Multiple options can be specified, each will be executed in order. The format of
    the option is:

    \b
    --input-placement "<place>=<path>"
    --input-placement "<place>"

    The <place> is a jsonpath that points to a location in the skeleton. The skeleton root can be simply referred to
    as "$". If the jsonpath refers to multiple locations (i.e. contains *), all of them will be targets.

    The <path> is a jsonpath or xpath, depending on the input type. Xml inputs only accept xpath, the other types only
    accept jsonpath. Jsonpath can be omitted, in which case $ will be used.

    Example 1

    \b
    echo {"a":{"b":10}} | cli transform --body {\\"x\\":null}
      --input-format json --input-file - --input-placement $.x=$.a

    {"x":{"b":10}}

    Example 2

    \b
    file.txt:
    color,weight,price
    red,100,10
    blue,100,10
    green,200,20

    cli transform --input-file file.txt --input-format csv.header.rows

    \b
    [{"color":"red", "weight":"100", "price":"10"},
     {"color":"blue", "weight":"100", "price":"10"},
     {"color":"green", "weight":"200", "price":"20"}]

    # TODO consider: if we use wildcard on both sides, what happens

    # TODO data type conversions
    """

    log.debug(f"transform")
    try:
        body = resolve_file(body)
        data = assemble_body(body, input_data, input_format, input_placement)
    except Exception as e:
        raise click.ClickException(f"{e}")
    process_json(data, output_expr, output_file, output_template)


def read_log_cfg():
    if os.path.isfile("logconfig.yaml"):
        with open("logconfig.yaml") as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            logging.config.dictConfig(cfg)

try:
    read_log_cfg()
    log = logging.getLogger("i4c")
    # yeah, this is ugly. we do a sneak peek for --profile
    # because we need it to get the api def
    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    log.debug(f"using profile {profile}")
    connection = I4CConnection(profile=profile)
    make_commands(connection)
    top_grp(obj={"connection": connection}, prog_name="i4c")
except click.ClickException as e:
    click.echo(e.message)

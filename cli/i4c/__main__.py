import sys
from functools import wraps
import click.globals
from .apidef import I4CDef
from .conn import I4CConnection
from .outputproc import print_table, process_json
from .inputproc import assemble_body


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

    path = args["path"]
    method = args["method"]
    ep = args["ep"]

    additional_headers = {}
    sec = ep.get("security", None)
    if sec:
        profile = args.get("profile", None)
        for seci in sec:
            sch = next(k for k in seci.keys())
            sch = api_def["components"]["securitySchemes"][sch]
            if sch["type"] == "http" and sch["scheme"] == "basic":
                auth_user = args["auth_user"]
                auth_pwd = args["auth_pwd"]
                auth_key = args["auth_key"]
                if not auth_user or (not auth_pwd and not auth_key):
                    (profile, p_user, p_pwd, p_key) = read_profile(profile, "~", "username", "password", "private-key")
                    auth_user = auth_user or p_user or profile
                    auth_pwd = auth_pwd or p_pwd
                    auth_key = auth_key or p_key
                if auth_key:
                    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    signature = sign(auth_key, timestamp)
                    token = f"{auth_user}:{timestamp}{signature}"
                    token = token.encode()
                    token = base64.b64encode(token).decode()
                    additional_headers["Authorization"] = f"Basic {token}"
                elif auth_pwd:
                    token = f"{auth_user}:{auth_pwd}"
                    token = token.encode()
                    token = base64.b64encode(token).decode()
                    additional_headers["Authorization"] = f"Basic {token}"
            # TODO handle other methods, not needed for this project

    # assemble url
    url = base_url + path

    for p in ep.get("parameters", []):
        if p["in"] == "path":
            pn = p["name"]
            if pn not in args:
                raise Exception(f"Missing argument: {pn}")
            value = args[pn]
            value = urllib.parse.quote(value)
            url = url.replace("{" + pn + "}", value)

    queries = []
    for p in ep.get("parameters", []):
        if p["in"] == "query":
            pn = p["name"]
            val = args.get(pn, None)
            if val:
                if not isinstance(val, list) and not isinstance(val, tuple):
                    val = [val]
                for i in val:
                    i = urllib.parse.quote(i)
                    queries.append(pn + "=" + i)
    if queries:
        url = url + "?" + "&".join(queries)

    # process body
    body = args.get("body", None)
    body = resolve_file(body)
    if isinstance(body, dict):
        body = jsonify(body).encode("utf-8")
    if isinstance(body, str):
        body = body.encode("utf-8")

    # do the call
    method = method.upper()

    if args.get("print_curl", False):
        raise Exception("Not implemented") # TODO

    log.debug(f"calling {method} {url}")
    if body: log.debug(f"body {jsonbrief(body)}")
    req = urllib.request.Request(url, data=body, method=method, headers=additional_headers)
    conn = urllib.request.urlopen(req)
    # TODO handle errors?
    content_type = conn.headers.get_content_type()
    origin_file_name = conn.headers.get_filename()
    if content_type == "application/json":
        log.debug(f"parsing json response")
        response = json.load(conn)
        if origin_file_name:
            response["origin"] = origin_file_name
    else:
        log.debug(f"{content_type} response")
        response = conn

    output_expr = args.get("output_expr", None)
    output_file = args.get("output_file", None)
    output_template = args.get("output_template", None)

    if isinstance(response, dict):
        process_json(response, output_expr, output_file, output_template)
    else:
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
    and calls `do`. The closure also handles exceptions.
    """
    def f(**args):
        try:
            res = do(click.globals.get_current_context(), **outer_args, **args)
        except click.ClickException as e:
            raise
        except urllib.error.HTTPError as e:
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


def make_commands(api_def: I4CDef):
    """
    Make click Groups and Commands based on command_mapping, which is derived from openapi.json
    """

    for (obj_name, obj) in api_def.objects.items():
        if len(obj.actions) == 1:
            grp = top_grp
        else:
            help = f"Command group for managing {obj} data."
            grp = click.Group(obj_name, help=help)
            top_grp.add_command(grp)

        for (action_name, action) in obj.actions.items():
            params = []
            for param_name, param in action.params.items():
                param_decl = "--" + param_name.replace("_", "-")
                attrs = {}
                attrs["multiple"] = param.is_array
                attrs["required"] = param.required
                #TODO use data type

                paramhelp = param.description or param.title
                paramhelp = paramhelp or (param_name.replace("_", " ").capitalize() + "." +
                                (" Multiple values allowed." if param.is_array else ""))
                attrs["help"] = paramhelp

                params.append(click.Option((param_decl,), **attrs))

            if action.body:
                param_decl = "--body"
                attrs = {}
                attrs["required"] = action.body.required

                helpstr = ""
                if action.body.sch_obj:
                    helpstr = f"Use the `doc {action.body.sch_obj}` command to get the definition. "
                helpstr = helpstr + "Use - to read from stdin, or @filename to read from file."
                attrs["help"] = helpstr

                params.append(click.Option((param_decl,), **attrs))

                params.append(click.Option(("--input-file",),
                    help="Points to a file which will be processed and inserted to the body according to the other "
                        "--input-* options. Use - to read from stdin."))

                params.append(click.Option(("--input-format",), multiple=True,
                    help="Specifies a format attribute. If omitted, the format will be derived from the file extension. "
                        "Attributes are separated by `.`, or you can specify multiple options, which will be combined. "
                        "For a detailed explanation on data input and transformations, see the transform command."))

            if action.authentication == "basic":
                params.append(click.Option(("--profile",), help="The name of the saved profile to use"))
                params.append(click.Option(("--auth-user",), help="User name for authentication"))
                params.append(click.Option(("--auth-pwd",), help="Password for basic authentication"))
                params.append(click.Option(("--auth-key",), help="Private key for signed timestamp authentication"))

            params.append(click.Option(("--print-curl",), is_flag=True,
                help="Instead of executing, print a CURL command line. Please note that sensitive information will be "
                    "included in the result. Also note that signature based authentication expires in 60 seconds."))

            if action.response_type == "application/json":
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

            callback = make_callback(path=action.path, method=action.method, action=action)
            cmd_name = action_name if len(obj.actions) > 1 else obj_name
            cmd = click.Command(cmd_name, callback=callback, params=params, help=action.help())
            grp.add_command(cmd)


def redact_profile(prof):
    "Remove sensitive information from profile before printing/exporting"
    prof = prof.copy()
    if "password" in prof:
        prof["password"] = True
    if "private-key" in prof:
        pri = prof.pop("private-key")
        prof["public-key"] = conn.public_key(pri)
    return prof


@top_grp.group("profile", help="Manage saved profiles")
def profile():
    pass


@profile.command("get", help="Gets all fields of a profile, or the default one if no name is given. "
    "Sensitive fields are redacted.")
@click.option("--name", help="The profile name to read")
@json_options
def profile_get(name, output_expr, output_file, output_template):
    data = load_profile() or {}
    default = data.get("default", None)

    if not name:
        name = default
        if not name:
            raise click.ClickException("No default profile set up")

    sect = data.get(name, None)
    if sect is None:
        raise click.ClickException("Profile does not exist")
    sect = {"name": name, **sect, "is-default": name == default}
    sect = {"profile": redact_profile(sect)}
    process_json(sect, output_expr, output_file, output_template)


@profile.command("new-key", help="Creates a new key pair for the profile, and displays the public key")
@click.option("--name", help="The profile name to modify. Must exist.")
@click.option("--override", is_flag=True, help="If the profile has a key already, replace it. The old key is deleted.")
@click.pass_context
def profile_new_key(ctx, name, override):
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
@click.option("--override", is_flag=True, help="If the profile exists, it will be modified.")
@click.option("--make-default", is_flag=True, help="Make the profile default")
@click.pass_context
def profile_save(ctx, name, base_url, api_def_file, del_api_def_file, user, password, del_password, del_private_key, override, make_default):
    conn = ctx.obj["connection"]
    if password == ".":
        password = click.termui.prompt("Password", hide_input=True, confirmation_prompt=True)
    try:
        conn.write_profile(name, base_url, api_def_file, del_api_def_file, user, password, del_password, del_private_key, override, make_default)
    except Exception as e:
        raise click.ClickException(e.message)


@profile.command("list", help="Gives back all existing profiles. Sensitive fields will be redacted.")
# TODO do we want any filters?
@json_options
@click.pass_context
def profile_list(ctx, output_expr, output_file, output_template):
    conn = ctx.obj["connection"]
    data = conn.profiles()
    process_json(data, output_expr, output_file, output_template)


@profile.command("delete", help="Permanently deletes the profile. Irreversible!")
@click.option("--name", help="The profile name to delete.")
@click.pass_context
def profile_delete(ctx, name):
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

    conn = ctx.obj["connection"]

    if output_expr or output_template or raw:
        if schema:
            obj = conn.api_def().content["components"]["schemas"][schema]
        else:
            obj = conn.api_def().content

        if not output_expr and not output_template:
            output_expr = "$"

        process_json(obj, output_expr, output_file, output_template)
        return

    if schema:
        sch = conn.api_def().schema[schema]
        click.echo(schema)
        click.echo()
        desc = click.formatting.wrap_text(sch.description, preserve_paragraphs=True)
        click.echo(desc)
        click.echo()
        if sch.data_type == "object":
            # there is no way to preserve the order, because fastAPI already messes it up. sorting alphabetically.
            table = [[k, v.data_type, v.description] for (k, v) in sorted(sch.properties.items(), key=lambda p: p[0])]
            click.echo("Fields:")
            print_table(table)
        elif sch.type_enum is not None:
            desc = f"It is a {sch.data_type} with possible values:"
            desc = click.formatting.wrap_text(desc, preserve_paragraphs=True)
            click.echo(desc)
            for op in sch.type_enum:
                click.echo(f"  {op}")
        else:
            click.echo(f"It is of type {sch.data_type}")
    else:
        click.echo("Commands and paths:")
        paths = [[obj_name, act_name if len(obj.actions) > 1 else "", f"{act.method.upper()} {act.path}"]
                 for (obj_name, obj) in conn.api_def().objects.items()
                 for (act_name, act) in obj.actions.items()]
        print_table(paths)
        click.echo()
        click.echo("Schemas:")
        schemas = ", ".join(conn.api_def.schema.keys())
        schemas = click.formatting.wrap_text(schemas, preserve_paragraphs=True)
        click.echo(schemas)


@top_grp.command("transform")
@click.option("--body")
@click.option("--input-file")
@click.option("--input-format", multiple=True, help="")
@click.option("--input-placement", multiple=True, help="")
@json_options
def transform(body, input_file, input_format, input_placement, output_expr, output_file, output_template):
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

    csv -> sep.comma.noheaeder.table
    txt -> sep.tab.noheader.table
    json -> json
    xml -> xml

    The attributes can be written in any order, and can be dot-separated or given in separate options. If multiple
    options are given, they will be combined. The attributes are:

    File type attributes:

    sep -> separated tabular text file
    csv -> shorthand for sep.comma
    txt -> shorthand for sep.tab
    fix -> fixed width tabular text file
    json -> canonical json file
    xml -> xml file

    For separated files, the following attributes can be used:

    tab -> tab delimited
    comma -> comma delimited
    semicolon -> semicolon delimited
    space -> space delimited, every space is a delimiter
    spaces -> space delimited, consecutive spaces are considered as one

    For fixed width files, the column widths are defined with:

    # TODO

    For tabular files, the following attributes can be used:

    cr|lf|crlf|auto -> specifies the row separator
    [no]header -> the first row contains or does not contain a header
    [no]trimcells -> weather to strip each data cell from leading/trailing whitespace
    rows -> the file is processed into an array of rows, rows are json objects.
    columns -> the file is processed into a json in which all columns are arrays.
    table -> the file is processed into an array of arrays t[row, column].

    If omitted, attributes have defaults, which are:

    sep.tab.auto.noheader.notrimcells.table

    Once the data is loaded processed, elements of it can be inserted into the body skeleton. The insertion is done
    with the --input-place option. Multiple options can be specified, each will be executed in order. The format of
    the option is:

    --input-placement "<place>=<path>"
    --input-placement "<place>"

    The <place> is a jsonpath that points to a location in the skeleton. The skeleton root can be simply referred to
    as "$". If the jsonpath refers to multiple locations (i.e. contains *), all of them will be targets.

    The <path> is a jsonpath or xpath, depending on the input type. Xml inputs only accept xpath, the other types only
    accept jsonpath. Jsonpath can be omitted, in which case $ will be used.

    Example 1

    echo {"a":{"b":10}} | cli transform --body {"x":null}
      --input-format json --input-file - --input-place "$.x=$.a"

    {"x":{"b":10}}

    Example 2

    file.txt:
    color,weight,price
    red,100,10
    blue,100,10
    green,200,20

    cli transform --input-file file.txt --input-format csv.header.rows

    [{"color":"red", "weight":"100", "price":"10"},
     {"color":"blue", "weight":"100", "price":"10"},
     {"color":"green", "weight":"200", "price":"20"}]

    # TODO consider: if we use wildcard on both sides, what happens

    # TODO data type conversions
    """

    data = assemble_body(body, input_file, input_format, input_placement)
    process_json(data, output_expr, output_file, output_template)


def read_log_cfg():
    # TODO
    pass


try:
    read_log_cfg()
    connection = I4CConnection()
    make_commands(connection.api_def())
    top_grp(obj={"connection": connection}, prog_name="i4c")
except click.ClickException as e:
    click.echo(e.message)

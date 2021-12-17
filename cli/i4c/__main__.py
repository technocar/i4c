import sys
from functools import wraps
import click.globals
from .apidef import I4CDef
from .conn import I4CConnection
from outputproc import print_table, process_json
from inputproc import assemble_body


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
            # TODO get description for the object
            # openapi/rest does not have a concept of objects, thus we need some custom data
            help = f"Command group for managing {obj} data."
            grp = click.Group(obj_name, help=help)
            top_grp.add_command(grp)
            
        for (action_name, action) in obj.actions.items():
            # , (path, method, info)

            params = []
            for param in info.get("parameters", []):
                param_decl = "--" + param["name"].replace("_", "-")
                attrs = {}

                type_info = get_data_type(api_def, param)

                if type_info["is_array"]:
                    attrs["multiple"] = True

                attrs["required"] = type_info["required"]

                #TODO use data type

                paramhelp = param.get("description", None)
                paramhelp = paramhelp or type_info["title"]
                paramhelp = paramhelp or (param["name"].replace("_", " ").capitalize() + "." +
                                (" Multiple values allowed." if attrs.get("multiple", False) else ""))
                attrs["help"] = paramhelp

                params.append(click.Option((param_decl,), **attrs))

            body = info.get("requestBody", None)
            if body:
                param_decl = "--body"
                attrs = {}
                attrs["required"] = body.get("required", True)

                schema = dig(body, ["content", "application/json", "schema"])
                if schema:
                    if "$ref" in schema:
                        _, _, cls = schema["$ref"].rpartition("/")
                    else:
                        cls = act.capitalize() + obj.capitalize() + "Body" # TODO doc command does not understand this
                helpstr = ""
                if cls:
                    helpstr = f"Schema: {cls}. Use the `doc {cls}` command to get the definition. "
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
                # TODO append body assembly params

            sec = info.get("security", None) or def_sec
            if sec:
                params.append(click.Option(("--profile",), help="The name of the saved profile to use"))
                for seci in sec:
                    sch = next(k for k in seci.keys())
                    sch = api_def["components"]["securitySchemes"][sch]
                    if sch["type"] == "http" and sch["scheme"] == "basic":
                        params.append(click.Option(("--auth-user",), help="User name for authentication"))
                        params.append(click.Option(("--auth-pwd",), help="Password for basic authentication"))
                        params.append(click.Option(("--auth-key",), help="Private key for signed timestamp authentication"))

            params.append(click.Option(("--print-curl",), is_flag=True,
                help="Instead of executing, print a CURL command line. Please note that sensitive information will be "
                    "included in the result. Also note that signature based authentication expires in 60 seconds."))

            if 1==1: # TODO only add output parameters if the response is json
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
            if 1==2: # TODO if the response is other than json, add output-file, and no templating
                params.append(click.Option(("--output-file",),
                    help="Output file name. If omitted or -, stdout is used."))

            callback = make_do(path=path, method=method, ep=info)
            cmd_name = action_name if len(actions) > 1 else obj_name
            cmd = click.Command(cmd_name, callback=callback, params=params, help=help)
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
def profile_new_key(*, name, override):
    def chg(data):
        prof = name or data.get("default", None)
        if not prof:
            raise click.ClickException("Specify profile or set up a default")
        if prof not in data:
            raise click.ClickException("Profile does not exist")

        if not override and "private-key" in data[prof]:
            raise click.ClickException("The profile already has a key")

        pri, pub = keypair_create()
        data[prof]["private-key"] = pri
        return pub

    pubkey = apply_profile_change(chg)
    click.echo(pubkey)


@profile.command("put", help="Creates or modifies a profile")
@click.option("--name", required=True, help="Name of the profile. Can not be 'default'.")
@click.option("--user-name", help="The value of the user-name used for authentication. If omitted, the profile name will be used.")
@click.option("--password", help="The value of the password for authentication or . to prompt.")
@click.option("--custom", multiple=True, help="Custom information that will be stored in the profile. The format "
    "is name=value. The name will be prefixed with x- if it is not already.")
@click.option("--override", is_flag=True, help="If the profile exists, it will be modified.")
@click.option("--make-default", is_flag=True, help="Make the profile default")
def profile_put(name, user_name, password, custom, override, make_default):
    def chg(data):
        data = data or {}
        sect = data.get(name, None)
        if sect is not None and not override:
            raise click.ClickException("The profile already exists")
        if sect is None:
            sect = {}
            data[name] = sect
        if user_name: sect["username"] = user_name
        if password: sect["password"] = password
        for cust in custom:
            (fld, value) = cust.split("=", 1)
            if not fld.startswith("x-"):
                fld = "x-" + fld
            sect[fld] = value
        if make_default: data["default"] = name

    if password == ".":
        password = click.termui.prompt("Password", hide_input=True, confirmation_prompt=True)
    apply_profile_change(chg)


@profile.command("list", help="Gives back all existing profiles. Sensitive fields will be redacted.")
# TODO do we want any filters?
@json_options
def profile_list(output_expr, output_file, output_template):
    data = load_profile(require_exist=False) or {}
    default = data.get("default", None)
    data = [{"profile": k, **redact_profile(v), "is-default": (k == default)} for (k,v) in data.items() if k != "default"]
    data = {"profiles": data}
    process_json(data, output_expr, output_file, output_template)


@profile.command("delete", help="Permanently deletes the profile. Irreversible!")
@click.option("--name", help="The profile name to delete.")
def profile_delete(name):
    def chg(data):
        if name in data:
            data.pop(name)
        else:
            raise click.ClickException("Profile does not exist")
    apply_profile_change(chg)


@top_grp.command("doc")
@click.argument("schema", required=False)
@click.option("--raw", is_flag=True, default=False)
@json_options
def doc(schema, raw, output_expr, output_file, output_template):
    """
    Output OpenAPI definition. If schema is specified, only that schema is displayed. The names of
    the schemas are used in parameters, especially --body parameters, which almost always take a schema.

    If no output-expr and outout-template is specified, a human readable formatting is provided.
    If you want the raw format, use --raw.
    """

    if raw and not output_expr and not output_template:
        output_expr = "$"

    if schema:
        obj = api_def["components"]["schemas"][schema]
    else:
        obj = api_def

    if output_expr or output_template:
        process_json(obj, output_expr, output_file, output_template)
        return

    if schema:
        click.echo(schema)
        click.echo()
        desc = obj.get("description", None)
        if desc:
            desc = click.formatting.wrap_text(desc, preserve_paragraphs=True)
            click.echo(desc)
            click.echo()
        sch_type = obj.get("type")
        if sch_type == "object":
            props = obj["properties"]
            req = obj.get("required", [])

            def prop_row(name, info):
                if 'allOf' in info:
                    info = info["allOf"]
                    info = info[0]  # TODO how to handle multi-item allOf?

                if "$ref" in info:
                    t = info["$ref"]
                    pre, _, t = t.rpartition("/")
                else:
                    if "type" in info:
                        t = info["type"]
                    elif "anyOf" in info:

                        def typeof(n):
                            t = n.get("type", None)
                            if not t: return None
                            if t == "array":
                                t = dig(n, ("items", "type")) or ""
                                t = f"{t}[]"
                            return t

                        t = "|".join(filter(None, (typeof(i) for i in info["anyOf"])))
                        if len(t) > 25: t = t[:22] + "..."
                    else:
                        t = "?"
                    is_array = (t == "array")
                    if is_array:
                        t = info["items"]
                        if "type" in t:
                            t = t["type"]
                        elif "$ref" in t:
                            t = t["$ref"]
                            pre, _, t = t.rpartition("/")
                    if is_array:
                        t = f"{t}[]"
                desc = info.get("title", "")
                if desc and not desc.endswith("."): desc = desc + "."

                attribs = []
                if name in req: attribs.append("required")
                if info.get("nullable", False): attribs.append("nullable")
                if attribs:
                    attribs = ", ".join(attribs)
                    attribs = attribs.capitalize() + "."
                    desc = " ".join(filter(None, (desc, attribs)))
                return [name, t, desc]

            # there is no need to preserve the order, because fastAPI already messes it up. sorting alphabetically.
            table = [prop_row(k, v) for (k, v) in sorted(props.items(), key=lambda p: p[0])]
            click.echo("Fields:")
            print_table(table)
        else:
            if "enum" in obj:
                desc = f"It is a {sch_type} with possible values:"
                desc = click.formatting.wrap_text(desc, preserve_paragraphs=True)
                click.echo(desc)
                for op in obj["enum"]:
                    click.echo(f"  {op}")
            else:
                click.echo(f"It is of type {sch_type}")
    else:
        click.echo("Commands and paths:")
        paths = [[obj, act if len(actions) > 1 else "", f"{method.upper()} {path}"]
                 for (obj, actions) in command_mapping.items()
                 for (act, (path, method, info)) in actions.items()]
        print_table(paths)
        click.echo()
        click.echo("Schemas:")
        schemas = ", ".join(api_def["components"]["schemas"].keys())
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


try:
    read_log_cfg()
    connection = I4CConnection()
    make_commands(connection.api_def())
    top_grp(obj={}, prog_name="i4c")
except click.ClickException as e:
    click.echo(e.message)

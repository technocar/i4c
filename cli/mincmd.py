# coding=utf-8
import functools
import os
import re
import sys
import base64
import datetime
import logging
import logging.config
from copy import deepcopy
import urllib.parse
import urllib.request
import urllib.error
import json
import yaml
import jsonpath_ng.ext
import click.globals
import jinja2
import hashlib
import nacl.encoding
import nacl.signing
from functools import wraps

log_file = None
log_cfg = None
log_level = None
log = None


def read_log_cfg():
    global log_cfg, log_file, log_level, log

    log_file = os.environ.get("mincmd-logfile", None)
    log_cfg = os.environ.get("mincmd-logcfg", None)
    log_level = os.environ.get("mincmd-loglevel", None)
    if log_cfg:
        with open(log_cfg) as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            logging.config.dictConfig(cfg)
    elif log_file or log_level:
        pars = {}
        if log_level:
            levels = {"CRITICAL": 50, "ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10}
            log_level = log_level.upper()
            if log_level not in levels:
                raise click.ClickException("log level must be " + "|".join(levels))
            pars["level"] = levels[log_level]
        if log_file:
            pars["filename"] = log_file
        logging.basicConfig(**pars)
    log = logging.getLogger("mincmd")


profile_file = os.environ.get("mincmd-profile", None)
if not profile_file:
    profile_file = os.path.expanduser("~") + "/.mincmd/profiles"

base_url = None
api_def_file = None
api_def_url = None


def read_api_cfg():
    global base_url, api_def_file, api_def_url

    # reading base URL
    base_url = os.environ.get('mincmd-base-url', None)
    if not base_url:
        raise click.ClickException("Base URL is missing from the environment. Set mincmd-base-url")

    # reading api def
    api_def_file = os.environ.get('mincmd-api-def-file', None)
    api_def_url = os.environ.get('mincmd-api-def-url', None)

    if not (api_def_file or api_def_url) and base_url:
        api_def_url = f"{base_url}/openapi.json"


command_mapping = {}
api_def = {}


def read_definition_file(fn):
    log.debug(f"reading openapi spec file {fn}")
    try:
        with open(api_def_file, "r") as f:
            content = json.load(f)
    except OSError as e:
        raise click.ClickException(f"OpenAPI definition file is inaccessible: {e.strerror} ({e.errno})")
    return content


def read_definition_url(url):
    log.debug(f"downloading openapi spec {api_def_url}")
    try:
        with urllib.request.urlopen(api_def_url) as u:
            content = json.load(u)
    except urllib.error.URLError as e:
        raise click.ClickException(f"Unable to download API definition: {e.reason}")
    return content


def load_definition():
    global api_def
    global command_mapping

    if api_def_file:
        api_def = read_definition_file(api_def_file)
    elif api_def_url:
        api_def = read_definition_url(api_def_url)

    for (path, methods) in api_def["paths"].items():
        for (method, info) in methods.items():
            action = info.get("x-mincl-action", None) or info.get("x-action", None) or method
            obj = info.get("x-mincl-object", None) or info.get("x-object", None) or \
                path[1:].replace("/", "_").replace("{", "by").replace("}", "")
            command_mapping.setdefault(obj, {})[action] = (path, method, info)
    # TODO allow overwrite mapping from config file


@click.group()
def top_grp():
    pass


def load_profile(require_exist=True):
    if not os.path.isfile(profile_file):
        if require_exist:
            raise click.ClickException("Unable to read profile information")
        else:
            return None
    # on linux, check file attrs
    if os.name == "posix":
        mode = os.stat(profile_file).st_mode
        if mode & 0o177 != 0:
            raise click.ClickException("Profile refused because of improper access rights")

    with open(profile_file, "r") as f:
        data = yaml.safe_load(f)

    return data


def read_profile(profile, *keys):
    data = load_profile()
    profile = profile or data.get("default", None)

    if not profile:
        raise click.ClickException("Authentication is incomplete, and no profile is given")

    sect = data.get(profile, None)
    if not sect:
        raise click.ClickException("The specified profile does not exist")

    res = (profile if key == "~" else sect.get(key, None)
        for key in keys)

    return res


def apply_profile_change(chg):
    """
    Opens the profile file, loads its content, and passes it to the function given in chg. If the function changes
    the content, it will be saved into the file as new content. One folder level will be created, and the file will be
    created if don't exist. On posix systems, mode will be appropriately set.

    :param chg: a function that takes a single parameter: the profile data as dict
    :return: returns the new data
    """
    data = load_profile(require_exist=False)
    data = data or {}
    newdata = deepcopy(data)
    result = chg(newdata)
    if data != newdata:
        folder = os.path.dirname(profile_file)
        if not os.path.isdir(folder):
            os.mkdir(folder, 0o700)
        with open(profile_file, "w") as f:
            yaml.dump(newdata, f)
        os.chmod(profile_file, 0o600)
    return result


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


def format_time(time, format_str):
    if time is None:
        return None

    if isinstance(time, str):
        try:
            time = datetime.datetime.fromisoformat(time) # TODO not stable
        except Exception as e:
            log.debug(f"can't parse time: {time}")
            return "???"

    try:
        s = time.strftime(format_str)
    except Exception as e:
        log.debug(f"time format string bad: {format_str}")
        return "???"

    return s


def make_jinja_env():
    env = jinja2.Environment()
    env.filters["json_dumps"] = json.dumps
    env.filters["jd"] = json.dumps
    env.filters["format_time"] = format_time
    env.filters["ft"] = format_time
    # TODO moar filters?
    return env


ctrlchars = ["nul", "soh", "stx", "etx", "eot", "enq", "ack", "bel",
             "bs", "tab", "lf", "vt", "ff", "cr", "so", "si",
             "dle", "dc1", "dc2", "dc3", "dc4", "nak", "syn", "etb",
             "can", "em", "sub", "esc", "fs", "gs", "rs", "us"]


def process_json(response, outexpr, outfile, template):
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
            itemdict = item

        if template:
            for (code, name) in enumerate(ctrlchars):
                itemdict[name] = chr(code)
            itemdict["nl"] = "\n"
            item_str = template.render(itemdict)
        else:
            if isinstance(item, dict):
                item_str = json.dumps(item, indent=2)
            else:
                item_str = str(item)

        if not outfile:
            sys.stdout.write(item_str)  # TODO determine if we need click.echo() instead
        else:
            fn = outfile.render(itemdict)
            log.debug(f"writing item to {fn}")
            with open(fn, "w") as f:
                f.write(item_str)


def public_key(private_key):
    if isinstance(private_key, str):
        private_key = nacl.signing.SigningKey(private_key, encoder=nacl.encoding.Base64Encoder)
    elif not isinstance(private_key, nacl.signing.SigningKey):
        private_key = nacl.signing.SigningKey(private_key)
    pub = private_key.verify_key
    pub = pub.encode(encoder=nacl.encoding.Base64Encoder).decode()
    return pub


def keypair_create():
    pri = nacl.signing.SigningKey.generate()
    pub = public_key(pri)
    pri = pri.encode(encoder=nacl.encoding.Base64Encoder).decode()
    return pri, pub


def sign(private_key, data):
    """
    Signs `data` with `private_key`, and returns the signature.

    :param private_key: the private key, can be bytes, base64 encoded str or SigningKey
    :param data: the data to sign, str or bytes
    :return: base64 encoded signature
    """
    if isinstance(private_key, str):
        private_key = nacl.signing.SigningKey(private_key, encoder=nacl.encoding.Base64Encoder)
    elif not isinstance(private_key, nacl.signing.SigningKey):
        private_key = nacl.signing.SigningKey(private_key)
    if isinstance(data, str):
        data = data.encode()
    signature = private_key.sign(data) # sign return a weirdo bytes derived class that combines message and signature
    signature = signature.signature # we only need the signature
    signature = base64.b64encode(signature).decode()
    return signature


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


def do(ctx, **args):
    "This is the main Click callback that performs the API call"
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
        body = json.dumps(body).encode("utf-8")
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


def make_do(**outer_args):
    """
    Create a closure that takes a Click context, outer_args and any number of actual arguments defined in OpenAPI doc,
    and calls `do`. The closure also handles exceptions.
    """
    def call_do(**args):
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
    return call_do


def follow_ref(apidef, ref):
    path_items = ref.split("/")
    if path_items[0] == "#":
        sch = apidef
        for path_item in path_items[1:]:
            sch = sch[path_item]
        return sch
    else:
        return None


def get_data_type(apidef, param, *, all_fields=True):
    """
    Take an openapi def and a parameter definition, and extracts data type information. Returns a dict with the
    extracted information.

    :param apidef: openapi dict
    :param param: parameter, body property, schema, or object reference
    :param all_fields: fill in all the fields, even if not found in the definition
    :return: a dict with the following members: required, title, default, is_array, data_type, value_list
    """

    if all_fields:
        res = dict(required=False, title=None, default=None, is_array=False, data_type=None, value_list=None)
    else:
        res = {}

    if "allOf" in param:
        for i in param["allOf"]:
            temp = get_data_type(apidef, i, all_fields=False)
            res.update(temp)

    if "$ref" in param:
        ref = param["$ref"]
        sch = follow_ref(apidef, ref)
        if sch:
            temp = get_data_type(apidef, sch, all_fields=False)
            res.update(temp)
        else:
            log.warning("param $ref to external doc, not following")
            # TODO we need fallback

    if "schema" in param:
        temp = get_data_type(apidef, param["schema"], all_fields=False)
        res.update(temp)

    if "type" in param:
        param_type = param["type"]

        if param_type == "array":
            res["is_array"] = True
            if "items" in param:
                temp = get_data_type(apidef, param["items"], all_fields=False)
                res.update(temp)
        else:
            res["data_type"] = param_type

        if "enum" in param:
            res["value_list"] = param["enum"]

    if "description" in param:
        res["description"] = param["description"]
    if "title" in param:
        res["title"] = param["title"]
    if "default" in param:
        res["default"] = param["default"]
    if "required" in param:
        res["required"] = param["required"]

    return res


def dig(d, path):
    enum = (i for i in path)
    while d is not None:
        fld = next(enum, None)
        if fld is None:
            return d
        d = d.get(fld, None)
    return None


def make_commands():
    """
    Make click Groups and Commands based on command_mapping, which is derived from openapi.json
    """
    def_sec = api_def.get("security", None)

    for (obj, actions) in command_mapping.items():
        if len(actions) == 1:
            grp = top_grp
        else:
            # TODO get description for the object
            # openapi/rest does not have a concept of objects, thus we need some custom data
            help = f"Command group for managing {obj} objects."
            grp = click.Group(obj, help=help)
            top_grp.add_command(grp)
        for (act, (path, method, info)) in actions.items():
            title = info.get("title", None)

            desc = info.get("description", None)
            resp = dig(info, ["responses", "200", "content", "application/json", "schema"])
            if resp:
                if "$ref" in resp:
                    _, _, cls = resp["$ref"].rpartition("/")
                else:
                    cls = act.capitalize() + obj.capitalize() + "Response" # TODO doc command does not understand this
                desc = f"{desc} Returns a {cls} object. Use the `doc {cls}` command to get details."

            help = "\n\n".join(filter(None, [title, desc, f"Calls {method.upper()} {path}"]))

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
            cmd_name = act if len(actions) > 1 else obj
            cmd = click.Command(cmd_name, callback=callback, params=params, help=help)
            grp.add_command(cmd)


def redact_profile(prof):
    "Remove sensitive information from profile before printing/exporting"
    prof = prof.copy()
    if "password" in prof:
        prof["password"] = True
    if "private-key" in prof:
        pri = prof.pop("private-key")
        prof["public-key"] = public_key(pri)
    return prof


@top_grp.group("profile", help="Manage saved profiles")
def profile():
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
                    info = info[0] # TODO how to handle multi-item allOf?
                    
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
        paths = [[obj, act if len(actions) > 1 else "", f"{method.upper()} {path}" ]
            for (obj, actions) in command_mapping.items()
            for (act, (path, method, info)) in actions.items()]
        print_table(paths)
        click.echo()
        click.echo("Schemas:")
        schemas = ", ".join(api_def["components"]["schemas"].keys())
        schemas = click.formatting.wrap_text(schemas, preserve_paragraphs=True)
        click.echo(schemas)


class InputFormat:
    fmt = "tabular"
    tabular_type = "sep"
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

    # TODO row_sep is now ignored, we use file enum

    def split_line_fix(ln):
        return [ln[f:t] for (f,t) in col_slices]

    def split_line_sep_spaces(ln):
        return list(filter(None, ln.split(" ")))

    def split_line_sep_char(ln):
        return ln.split(split_char)

    if fmt.tabular_type == "sep":
        if fmt.sep == "spaces":
            split_line = split_line_sep_spaces
        else:
            split_char = {"tab":"\t", "space":" ", "comma": ",", "semicolon": ";"}[fmt.sep]
            split_line = split_line_sep_char
    else:
        col_bounds = functools.reduce(lambda a, x: a + [a[-1] + x], fmt.col_widths, [0])
        col_slices = list(zip(col_bounds[:-1], col_bounds[1:]))
        split_line = split_line_fix

    if fmt.header:
        line = next(f, None)
        if line is None: raise Exception("Expected header not found")
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
        data.append({n: v for (n, v) in zip(col_names, row)})

    def add_line_columns(row, data):
        for i, c in enumerate(col_names):
            data[c].append(row[i])

    def add_line_table(row, data):
        data.append(row)

    if fmt.table_fmt == "rows":
        data = []
        add_line = add_line_rows
    elif fmt.table_fmt == "columns":
        data = {c:[] for c in col_names}
        add_line = add_line_columns
    else:
        data = []
        add_line = add_line_table

    for ln in f:
        if ln.endswith("\n"): ln = ln[:-len("\n")]   # TODO if we ever implement row_sep, this needs to be removed
        row = split_line(ln)
        for i, t in enumerate(fmt.col_types):
            if t == "i": row[i] = int(row[i])
            elif t == "f": row[i] = float(row[i])
            elif t == "isodt": row[i] = datetime.datetime.fromisoformat(row[i])
        add_line(row, data)

    return data


def format_attrs(s):
    """
    Takes a format definition string or list of strings, and returns format object.

    :param s: String or string list, with dot-separated format descriptors
    :return: an InputFormat object with all the fields filled in
    """
    f = InputFormat()
    if isinstance(s, str):
        s = [s]
    for i in s:
        for e in i.split("."):
            if e == "csv":
                f.fmt = "tabular"
                f.tabular_type = "sep"
                f.sep = "comma"
            elif e == "sep" or e == "fix":
                f.fmt = "tabular"
                f.tabular_type = e
            elif e == "json" or e == "xml":
                f.fmt = e
            elif e in ("comma", "tab", "semicolon", "space", "spaces"):
                f.sep = e
            elif "=" in e:
                (n, _, w) = e.partition("=")
                if n == "": n = None
                if w == "": w = None
                f.col_names.append(n)
                first_alpha = next((i[0] for i in enumerate(w) if not i[1].isnumeric()), None)
                if first_alpha is None:
                    t = None
                else:
                    t = w[first_alpha:]
                    w = w[:first_alpha]
                f.col_widths.append(w)
                f.col_types.append(t)
            elif e == "header":
                f.header = True
            elif e == "noheader":
                f.header = False
            elif e in ("cr", "lf", "crlf", "auto"):
                f.row_sep = e
            elif e in ("rows", "columns", "table"):
                f.table_fmt = e
            elif e == "trimcells":
                f.trim_cells = True
            elif e == "notrimcells":
                f.trim_cells = False
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


def assemble_body(body, input_file, input_format, input_placement):
    if body is None:
        body = {}
    elif isinstance(body, str):
        body = json.loads(body)
    else:
        body = dict(body)

    attr = format_attrs(input_format)

    if input_file == "-":
        if attr.fmt == "xml":
            raise Exception("Not implemented") # TODO we need to pick a module. etree is kinda shit
        elif attr.fmt == "json":
            ext = json.load(sys.stdin)
        elif attr.fmt == "tabular":
            ext = load_table(sys.stdin, attr)
    elif input_file is not None:
        if attr.fmt == "xml":
            raise Exception("Not implemented") # TODO we need to pick a module. etree is kinda shit
        elif attr.fmt == "json":
            with open(input_file, "r") as f:
                ext = json.load(f)
        elif attr.fmt == "tabular":
            with open(input_file, "r") as f:
                ext = load_table(f, attr)

    if not input_placement and input_file:
        input_placement = ["$"]

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
            matches = expr.find(ext)
            if matches:
                if op == "*=" or len(matches) > 1:
                    piece = [m.value for m in matches]
                else:
                    piece = matches[0].value
            else:
                piece = None

            if placement is not None:
                placement.update(body, piece)
            else:
                body = piece

    return body


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


if __name__ == '__main__':
    try:
        read_log_cfg()
        read_api_cfg()
        load_definition()
        make_commands()
        prog_name = os.environ.get("mincmd-program-name", "CLI")
        top_grp(obj={}, prog_name=prog_name)
    except click.ClickException as e:
        click.echo(e.message)

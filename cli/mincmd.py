# coding=utf-8

import os
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
import click.globals

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



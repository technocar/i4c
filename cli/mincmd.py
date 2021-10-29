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




def make_commands(api_def):
    """
    Make click Groups and Commands based on command_mapping, which is derived from openapi.json
    """

    for (obj, actions) in api_def.command_mapping.items():
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







import os
import json
import datetime
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Dict, Any
from .tools import jsonify


class Param:
    title: str
    description: str
    location: str # path | query
    is_array: bool
    required: bool
    type: str
    type_fmt: Any
    sch_obj: str

    def __repr__(self):
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items())
        flds = ", ".join(flds)
        return f"Param({flds})"


class Action:
    title: str
    description: str
    authentication: str  # noauth, basic, unknown
    response_type: str
    response_class: str
    params: Dict[str, Param]
    body_required: bool
    body_content_type: str
    body_class: str
    path: str
    method: str
    raw: dict

    def __repr__(self):
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items() if f != "raw")
        flds = ", ".join(flds)
        return f"Action({flds})"

    def help():
        s = []
        if title:
            s.append(title)
        if description:
            s.append(description)
        if not s:
            return nice_name()
        s.append(f"Calls {method} {path}.")
        return s.join("\n")


class Obj:
    actions: Dict[str, Action]


class Schema:
    pass # TODO


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

"""
ACTION PROPERTIES:

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
"""


def _proc_auth(a):
    """
    'a' is the required OpenAPI 'Security Scheme Object' items.
    Return the classification for the entire requirement.
    """
    # this is rudimentary. optimally we could support other auth schemes,
    # but we only use this one, so whatever
    if not a:
        return "noauth"
    if len(a) == 1 and a[0] == {"type": "http", "scheme": "basic"}:
        return "basic"
    else:
        return "unknown"


def _proc_sch(sch): # TODO try remove self
    if sch is None:
        return None, False, "unknown", None, None, None

    title = sch.get("title", None)
    datatype = sch.get("type", "unknown")
    isarray = datatype == "array"
    if isarray:
        typeroot = sch.get("items", {})
        datatype = typeroot.get("type", "unknown")
    else:
        typeroot = sch
    typename = typeroot.get("$ref", None)
    typefmt = typeroot.get("format", None)
    typeenum = typeroot.get("enum", None)

    return title, isarray, datatype, typefmt, typeenum, typename


def preproc_def(apidef):
    # TODO bring singular allOf to parent level

    def descend(level):
        if "$ref" in level:
            refd = level["$ref"]
            if refd.startswith("#/components/schemas/"):
                refd = refd[21:]
            refd = apidef["components"]["schemas"][refd]
            for (k, v) in refd.items():
                if k not in level:
                    level[k] = v
        for (k, v) in level.items():
            if isinstance(v, dict):
                descend(v)

    descend(apidef)


class I4CDef:
    content = None
    objects: Dict[str, Obj] = {}
    schema: Dict[str, Schema] = {}

    def __init__(self, *, base_url=None, def_file=None):
        if def_file:
            def_file = os.path.expanduser(def_file)
            with open(def_file, "r") as f:
                self.content = json.load(f)
        elif base_url:
            url = base_url
            if not url.endswith("/"):
                url = url + "/"
            url = url + "openapi.json"
            with urllib.request.urlopen(url) as u:
                self.content = json.load(u)
        else:
            raise Exception("Either base url or definition file required.")

        preproc_def(self.content)

        # TODO collect schema objects

        for (path, methods) in self.content["paths"].items():
            for (method, info) in methods.items():
                obj_name, _, action_name = info["operationId"].partition("_")
                action_name = action_name.replace("_", "-")

                if obj_name in self.objects:
                    obj = self.objects[obj_name]
                else:
                    obj = Obj()
                    obj.actions = {}
                    self.objects[obj_name] = obj

                action = Action()

                action.path = path
                action.method = method
                action.raw = info

                action.summary = info.get("summary", None)
                action.description = info.get("description", None)

                sec = info.get("security", [])
                sec = [[self.content["components"]["securitySchemes"][k] for k in s.keys()] for s in sec]
                sec = [_proc_auth(a) for a in sec]
                if "noauth" in sec:
                    action.security = 'noauth'
                elif "basic" in sec:
                    action.security = 'basic'
                else:
                    action.security = 'unknown'

                action.params = {}
                for p in info.get("parameters", []):
                    par = Param()
                    par.location = p["in"]
                    par.description = p.get("description", None)
                    par.required = p.get("required", False)
                    sch = p.get("schema", None)
                    if sch:
                        (par.title, par.is_array, par.type, par.type_fmt, par.type_enum, par.sch_obj) = _proc_sch(sch)
                    else:
                        par.title = None
                        par.is_array = False
                        par.type = "unknown"
                        par.type_fmt = None
                        par.type_enum = None
                        par.sch_obj = None
                    action.params[p["name"]] = par
                    # TODO fix bug: datapoint.list reports no type for parameter device

                body = info.get("requestBody", None)
                if body is not None:
                    action.body_required = body.get("required", False)
                    ct = body.get("content", {})
                    ct, sch = next(iter(ct.items()), (None, None))
                    sch = sch.get("schema", None)
                    action.body_content_type = ct
                    (action.body_title, action.body_is_array, action.body_type, action.body_type_fmt, action.body_type_enum, action.body_sch_obj) = _proc_sch(sch)
                else:
                    action.body_required = False
                    action.body_content_type = None
                    action.body_title = None
                    action.body_is_array = False
                    action.body_type = 'unknown'
                    action.body_type_fmt = None
                    action.body_type_enum = None
                    action.body_sch_obj = None

                # TODO fill in response

                obj.actions[action_name] = action

    def assemble_url(self, obj, action=None, **params):
        obj = self.objects[obj]

        if action is None and len(obj) == 1:
            action = list(obj.values())[0]
        else:
            action = obj.actions[action]

        method = action.method.upper()
        url = action.path

        for pn, p in action.params.items():
            if p.location == "path":
                if pn not in params:
                    raise Exception(f"Missing argument: {pn}")
                value = params[pn]
                if not isinstance(value, str) and not isinstance(value, bytes):
                    value = str(value)
                value = urllib.parse.quote(value)
                url = url.replace("{" + pn + "}", value)

        queries = []
        for pn, p in action.params.items():
            if p.location == "query":
                val = params.get(pn, None)
                if val:
                    if not isinstance(val, list) and not isinstance(val, tuple):
                        val = [val]
                    for i in val:
                        if isinstance(i, datetime.datetime):
                            i = i.isoformat()
                        elif not isinstance(i, str) and not isinstance(i, bytes):

                            # TODO there should be a whole lot more conversions
                            # datetime
                            # period
                            i = str(i)
                        i = urllib.parse.quote(i)
                        queries.append(pn + "=" + i)
        if queries:
            url = url + "?" + "&".join(queries)

        return method, url

    def prepare_body(self, obj, action, body):
        obj = self.objects[obj]

        if action is None and len(obj) == 1:
            action = list(obj.values())[0]
        else:
            action = obj.actions[action]

        content_type = action.body_content_type

        if content_type == "application/json":
            if any(isinstance(body, t) for t in (dict, list, str, int, float, bool)):
                body = jsonify(body).encode()
        elif content_type == "application/octet-stream":
            if any(isinstance(body, t) for t in (dict, list, int, float, bool)):
                body = jsonify(body).encode()
            elif isinstance(body, str):
                body = body.encode()
        elif content_type == "text/plain":
            if isinstance(body, str):
                body = body.encode()

        return body, content_type

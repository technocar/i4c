import os
import json
import datetime
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Dict, Any
from .tools import jsonify


class Schema:
    title: str
    description: str
    is_array: bool
    required: bool
    type: str
    type_fmt: str
    type_enum: List[str]
    sch_obj: str

    def __repr__(self):
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items())
        flds = ", ".join(flds)
        return f"{self.__class__.__name__}({flds})"


class Body(Schema):
    content_type: str


class Param(Schema):
    location: str # path | query


def nice_name(s):
    return " ".join(word.capitalize() for word in s.split("_"))


class Action:
    title: str
    description: str
    authentication: str  # noauth, basic, unknown
    response_type: str
    response_class: str
    params: Dict[str, Param]
    body: Body
    path: str
    method: str
    raw: dict

    def __repr__(self):
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items() if f != "raw")
        flds = ", ".join(flds)
        return f"Action({flds})"

    def help(self):
        s = []
        if self.summary:
            s.append(self.summary)
            s.append("")
        if self.description:
            s.append(self.description)
        if not s:
            return nice_name(self.raw["operationId"])
        s.append(f"Calls {self.method.upper()} {self.path}")
        return "\n".join(s)


class Obj:
    actions: Dict[str, Action]

    def __repr__(self):
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items())
        flds = ", ".join(flds)
        return f"Obj({flds})"


class Schema:
    pass # TODO


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


def _proc_sch(sch, target):
    if sch is None:
        target.title = None
        target.is_array = False
        target.type = "unknown"
        target.type_fmt = None
        target.type_enum = None
        target.sch_obj = None

    target.title = sch.get("title", None)
    target.type = sch.get("type", "unknown")
    target.is_array = target.type == "array"
    if target.is_array:
        typeroot = sch.get("items", {})
        target.type = typeroot.get("type", "unknown")
    else:
        typeroot = sch
    target.sch_obj = typeroot.get("$ref", None)
    target.type_fmt = typeroot.get("format", None)
    target.type_enum = typeroot.get("enum", None)


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
                    _proc_sch(sch, par)
                    action.params[p["name"]] = par

                body = info.get("requestBody", None)
                if body is not None:
                    ct = body.get("content", {})
                    ct, sch = next(iter(ct.items()), (None, None))
                    sch = sch.get("schema", None)
                    action.body = Body()
                    action.body.required = body.get("required", False)
                    action.body.content_type = ct
                    _proc_sch(sch, action.body)
                else:
                    action.body = None

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

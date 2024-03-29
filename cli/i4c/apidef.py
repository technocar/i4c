from __future__ import annotations
import os
import json
import datetime
import sys
import isodate
import ssl
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Dict
from dataclasses import dataclass, field
from .tools import jsonify, I4CException


@dataclass
class Schema:
    title: str = None
    description: str = None
    is_array: bool = None
    required: bool = None
    type: str = None
    type_fmt: str = None
    type_enum: List[str] = None
    sch_obj: str = None
    properties: Dict[str, Schema] = None

    def __repr__(self):
        # TODO can we do it smarter?
        # basically we are having this func only to omit the properties on non-objects
        flds = (f"{f}={repr(v)}" for f,v in self.__dict__.items() if f != "properties" or self.type == "object")
        flds = ", ".join(flds)
        return f"{self.__class__.__name__}({flds})"

    def type_desc(self, *, brief=True):
        type_name = self.sch_obj or self.type
        if not self.is_array and brief:
            return type_name
        if self.is_array and not brief:
            return f"A list of {type_name}."
        if not self.is_array and not brief:
            return type_name + "."
        if self.is_array and brief:
            return f"{type_name}[]"

    def describe(self, *, brief=False):
        if brief:
            return self.title or self.description or self.type_desc(brief=brief)
        else:
            return self.description or self.title or self.type_desc(brief=brief)


@dataclass
class Response(Schema):
    content_type: str = None


@dataclass
class Body(Schema):
    content_type: str = None


@dataclass
class Param(Schema):
    location: str = None # path | query


def nice_name(s):
    return " ".join(word.capitalize() for word in s.split("_"))


@dataclass
class Action:
    summary: str = None
    description: str = None
    authentication: str = None  # noauth, basic, unknown
    response: Response = None
    params: Dict[str, Param] = None
    body: Body = None
    path: str = field(repr=False, default=None)
    method: str = field(repr=False, default=None)
    raw: dict = field(repr=False, default=None)

    def help(self):
        s = []
        if self.description:
            s.append(self.description)
        if not s:
            return nice_name(self.raw["operationId"])
        if self.response is not None:
            if self.response.sch_obj is not None:
                typedesc = self.response.sch_obj
                if self.response.is_array:
                    typedesc = f"a list of {typedesc}"
                s.append(f"Returns {typedesc}, see `doc\xa0{self.response.sch_obj}` for details.")
            else:
                if self.response.content_type == "application/json": ct = "json"
                elif self.response.content_type == "application/octet-stream": ct = "binary"
                elif self.response.content_type == "text/plain": ct = "text"
                elif self.response.content_type == "text/html": ct = "html"
                else: ct = self.response.content_type
                s.append(f"Returns {ct}.")
        s.append(f"Calls {self.method.upper()}\xa0{self.path}")
        return "\n".join(s)

    def short_help(self):
        return self.summary or  self.description or  nice_name(self.raw["operationId"])

    def assemble_url(self, **kwargs):
        method = self.method.upper()
        url = self.path

        for pn, p in self.params.items():
            if p.location == "path":
                if pn not in kwargs:
                    raise I4CException(f"Missing argument: {pn}")
                value = kwargs[pn]
                if not isinstance(value, str) and not isinstance(value, bytes):
                    value = str(value)
                illegal = "".join(c for c in ":\\?&+=\"" if c in value)
                if illegal:
                    raise I4CException(f"Illegal character '{illegal}' in path parameter.")
                if "/" in value:
                    sys.stderr.write("Warning: using '/' in path parameters can lead to unintended results.\n")
                value = urllib.parse.quote(value)
                url = url.replace("{" + pn + "}", value)

        queries = []
        for pn, p in self.params.items():
            if p.location == "query":
                val = kwargs.get(pn, None)
                if val:
                    if not isinstance(val, list) and not isinstance(val, tuple):
                        val = [val]
                    for i in val:
                        if isinstance(i, bool):
                            i = "1" if i else "0"
                        if any(isinstance(i, t) for t in (datetime.datetime, datetime.date, datetime.time)):
                            i = i.isoformat()
                        if isinstance(i, datetime.timedelta):
                            i = isodate.duration_isoformat(i)
                        elif not isinstance(i, str) and not isinstance(i, bytes):
                            i = str(i)
                        i = urllib.parse.quote(i, safe="")
                        queries.append(pn + "=" + i)
        if queries:
            url = url + "?" + "&".join(queries)

        return method, url

    def prepare_body(self, body):
        if self.body is None:
            return None, None
        
        content_type = self.body.content_type

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


@dataclass
class Obj:
    actions: Dict[str, Action] = None

    def __getitem__(self, item):
        return self.actions[item]

    def __getattr__(self, item):
        acts = (o for (k, o) in self.actions.items() if k.replace("_", "-") == item.replace("_", "-"))
        act = next(acts, None)
        act2 = next(acts, None)
        if act is None or act2 is not None:
            raise KeyError()
        return act


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
        target.required = False

    target.title = sch.get("title", None)
    target.description = sch.get("description", None)
    target.type = sch.get("type", "unknown")
    target.is_array = target.type == "array"
    if target.is_array:
        typeroot = sch.get("items", {})
        target.type = typeroot.get("type", "unknown")
    else:
        typeroot = sch
    target.sch_obj = typeroot.get("$ref", None)
    if target.sch_obj and target.sch_obj.startswith("#/components/schemas/"):
        target.sch_obj = target.sch_obj[21:]
    target.type_fmt = typeroot.get("format", None)
    target.type_enum = typeroot.get("enum", None)

    props = sch.get("properties", None)
    if props is not None:
        required = sch.get("required", [])
        target.properties = {}
        for prop_name, prop in props.items():
            propo = Schema()
            _proc_sch(prop, propo)
            propo.required = prop_name in required
            target.properties[prop_name] = propo


def preproc_def(apidef):
    # this could lead to infinite recursion. not an issue with our API.
    def descend(level):
        if "allOf" in level:
            for sub in level["allOf"]:
                for k, v in sub.items():
                    level[k] = v
            del level["allOf"]

        if "anyOf" in level:
            subs = level["anyOf"]
            if len(subs) == 1:
                sub = subs[0]
                for k, v in sub.items():
                    level[k] = v
                del level["anyOf"]
            # TODO what can we do with multivalued anyOf?

        if "$ref" in level:
            refd = level["$ref"]
            if refd.startswith("#/components/schemas/"):
                refd = refd[21:]
            refd = apidef["components"]["schemas"][refd]
            for (k, v) in refd.items():
                if k not in level:
                    level[k] = v
        for (k, v) in level.items():
            if isinstance(v, list):
                for i in v:
                    if isinstance(i, dict):
                        descend(i)
            elif isinstance(v, dict):
                descend(v)

    descend(apidef)


class I4CDef:
    content = None
    objects: Dict[str, Obj] = {}
    schema: Dict[str, Schema] = {}

    def __init__(self, *, base_url=None, def_file=None, insecure=None):
        if def_file:
            def_file = os.path.expanduser(def_file)
            with open(def_file, "r") as f:
                self.content = json.load(f)
        elif base_url:
            url = base_url
            if not url.endswith("/"):
                url = url + "/"
            url = url + "openapi.json"

            ctx = ssl.create_default_context()
            if insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(url, context=ctx) as u:
                self.content = json.load(u)
        else:
            raise I4CException("Either base url or definition file required.")

        preproc_def(self.content)

        self.schema = {}
        for (sch_name, sch) in self.content["components"]["schemas"].items():
            scho = Schema()
            _proc_sch(sch, scho)
            self.schema[sch_name] = scho

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
                    action.authentication = 'noauth'
                elif "basic" in sec:
                    action.authentication = 'basic'
                else:
                    action.authentication = 'unknown'

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

                resp = info.get("responses", None)
                resp = resp and (resp.get("200", None) or resp.get("201", None))
                resp = resp and resp.get("content", None)
                if resp:
                    ct, ctdef = next(iter(resp.items()), (None, None))
                    ctdef = ctdef and ctdef.get("schema", None)
                    resp = Response()
                    resp.content_type = ct
                    _proc_sch(ctdef, resp)
                    action.response = resp

                obj.actions[action_name] = action

    def __getitem__(self, item):
        return self.objects[item]

    def __getattr__(self, item):
        objs = (o for (k, o) in self.objects.items() if k.replace("_", "-") == item.replace("_", "-"))
        obj = next(objs, None)
        obj2 = next(objs, None)
        if obj is None or obj2 is not None:
            raise KeyError()
        return obj

    def assemble_url(self, obj, action=None, **kwargs):
        obj = self.objects[obj]

        if action is None and len(obj.actions) == 1:
            action = list(obj.actions.values())[0]
        else:
            action = obj.actions[action]

        return action.assemble_url(**kwargs)

    def prepare_body(self, obj, action, body):
        obj = self.objects[obj]

        if action is None and len(obj) == 1:
            action = list(obj.values())[0]
        else:
            action = obj.actions[action]

        return action.prepare_body(body)

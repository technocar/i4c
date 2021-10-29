import json
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Dict


class Param:
    name: str
    title: str
    description: str
    location: str # path | query
    is_array: bool
    required: bool


class Action:
    title: str
    description: str
    authentication: str  # none, basic, unknown
    response_type: str
    response_class: str
    params: Dict[str, Param]
    body_required: bool
    body_class: str
    raw: dict


class Obj:
    actions: Dict[str, Action]


class I4CDef:
    content = None
    objects: Dict[str, Obj]

    def __init__(self, *, base_url=None, def_file=None):
        if def_file:
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

        for (path, methods) in self.content["paths"].items():
            for (method, info) in methods.items():
                action_name = info.get("x-mincl-action", None) or info.get("x-action", None) or method
                obj_name = info.get("x-mincl-object", None) or info.get("x-object", None) or \
                    path[1:].replace("/", "_").replace("{", "by").replace("}", "")

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
                # TODO fill in params, body, response, etc
                obj.actions[action_name] = action

        # TODO collect schema objects

    def assemble_url(self, obj, action=None, **params):
        obj = self.objects[obj]

        if action is None and len(obj) == 1:
            action = list(obj.values())[0]
        else:
            action = obj.actions[action]

        method = action.method.upper()
        url = action.path

        for p in action.params:
            if p["in"] == "path":
                pn = p["name"]
                if pn not in params:
                    raise Exception(f"Missing argument: {pn}")
                value = params[pn]
                if not isinstance(value, str) and not isinstance(value, bytes):
                    value = str(value)
                value = urllib.parse.quote(value)
                url = url.replace("{" + pn + "}", value)

        queries = []
        for p in ep.get("parameters", []):
            if p["in"] == "query":
                pn = p["name"]
                val = params.get(pn, None)
                if val:
                    if not isinstance(val, list) and not isinstance(val, tuple):
                        val = [val]
                    for i in val:
                        if not isinstance(i, str) and not isinstance(i, bytes):
                            i = str(i)
                        i = urllib.parse.quote(i)
                        queries.append(pn + "=" + i)
        if queries:
            url = url + "?" + "&".join(queries)

        return method, url

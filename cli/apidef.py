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


class I4CDef:
    content = None
    objects: Dict[str, Obj]
    schema: Dict[str, Schema]

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

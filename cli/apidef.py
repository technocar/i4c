import json
import urllib.request
import urllib.error
import urllib.parse


class I4CDef:
    content = None
    command_mapping = {}

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
                action = info.get("x-mincl-action", None) or info.get("x-action", None) or method
                obj = info.get("x-mincl-object", None) or info.get("x-object", None) or \
                    path[1:].replace("/", "_").replace("{", "by").replace("}", "")
                self.command_mapping.setdefault(obj, {})[action] = (path, method, info)

    def assemble_url(self, obj, action=None, **params):
        obj = self.command_mapping[obj]
        if action is None and len(obj) == 1:
            url, method, ep = list(obj.values())[0]
        else:
            url, method, ep = obj[action]
        method = method.upper()

        for p in ep.get("parameters", []):
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

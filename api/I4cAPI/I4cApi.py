from fastapi import FastAPI

from .I4cApiRouter import I4cApiRouter


class I4cApi(FastAPI):
    def __init__(self, *args, **kwargs):
        self.openapi_extra = []
        super().__init__(*args, **kwargs)

    def openapi(self):
        res = super().openapi()
        paths = res["paths"]
        for (m, p, xtra) in self.openapi_extra:
            for (k, v) in xtra.items():
                paths[p][m][f"x-{k}"] = v
        return res

    def get(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("get", path, kwargs.pop("x_properties")))
        return super().get(path, *args, **kwargs)

    def put(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("put", path, kwargs.pop("x_properties")))
        return super().put(path, *args, **kwargs)

    def post(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("post", path, kwargs.pop("x_properties")))
        return super().post(path, *args, **kwargs)

    def delete(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("delete", path, kwargs.pop("x_properties")))
        return super().delete(path, *args, **kwargs)

    def options(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("options", path, kwargs.pop("x_properties")))
        return super().options(path, *args, **kwargs)

    def head(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("head", path, kwargs.pop("x_properties")))
        return super().head(path, *args, **kwargs)

    def patch(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("patch", path, kwargs.pop("x_properties")))
        return super().patch(path, *args, **kwargs)

    def trace(self, path: str, *args, **kwargs):
        if "x_properties" in kwargs:
            self.openapi_extra.append(("trace", path, kwargs.pop("x_properties")))
        return super().trace(path, *args, **kwargs)

    def include_router(self, router, *args, **kwargs):
        super().include_router(router, *args, **kwargs)
        if isinstance(router, I4cApiRouter):
            if "prefix" not in kwargs:
                self.openapi_extra.extend(router.openapi_extra)
            else:
                for m, p, x in router.openapi_extra:
                    self.openapi_extra.append((m, kwargs["prefix"]+p, x))

import re

from fastapi import FastAPI

from .I4cApiRouter import I4cApiRouter


class I4cApi(FastAPI):
    def __init__(self, *args, **kwargs):
        self.openapi_extra = []
        super().__init__(*args, **kwargs)

    def get(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def put(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def post(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def delete(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def options(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def head(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def patch(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def trace(self, path: str, *args, **kwargs):
        raise Exception("use I4cApiRouter")

    def include_router(self, router, *args, **kwargs):
        super().include_router(router, *args, **kwargs)
        if isinstance(router, I4cApiRouter):
            applied_prefix = kwargs.get("prefix", "")
            if applied_prefix != router.include_path:
                raise Exception(f"applied_prefix=\"{applied_prefix}\" should be \"{router.include_path}\"")
            router.router_included = True
            if "prefix" not in kwargs:
                self.openapi_extra.extend(router.openapi_extra)
            else:
                for m, p, x in router.openapi_extra:
                    self.openapi_extra.append((m, kwargs["prefix"]+p, x))

import functools
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter
from fastapi.types import DecoratedCallable
from common import log
from common.exceptions import I4cClientError
from common.tools import deepdict
from models.log import put_log_write, DataPoint


class I4cApiRouterPath:
    path: str
    features: List[str]

    def __init__(self, path, features):
        self.path = path
        self.features = features


class I4cApiRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        self.openapi_extra = []
        self.router_included = False
        self.include_path = kwargs.get("include_path", "")
        self.path_list = []
        if "include_path" in kwargs:
            del kwargs["include_path"]
        super().__init__(*args, **kwargs)

    @staticmethod
    def func_extra(func, path: str, rest_method: str = None, allow_log: bool = True):
        @functools.wraps(func)
        def log_decorator(f) -> DecoratedCallable:
            @functools.wraps(f)
            async def log_result(*a, **b):
                if allow_log:
                    params = ', '.join((str(x) for x in a))
                    bmasked = deepdict(b, json_compat=True, hide_bytes=True)
                    user = ""
                    noaudit = ("noaudit" in bmasked) and bmasked["noaudit"]
                    noaudit_priv = False
                    if "credentials" in bmasked:
                        bmasked["credentials"]["password"] = "****"
                        user = bmasked["credentials"]["username"]
                        if "info_features" in bmasked["credentials"]:
                            noaudit_priv = "noaudit" in bmasked["credentials"]["info_features"]
                    if noaudit and not noaudit_priv:
                        raise I4cClientError("""Missing "noaudit" privilege.""")
                    if not noaudit:
                        try:
                            kwparams = ', '.join((f"{x}= \"{y}\"" for x,y in bmasked.items()))
                            log_str = f"{rest_method} - {path}{' - '+params if params else ''} - {kwparams}"
                            log.info(log_str)

                            d = DataPoint(timestamp=datetime.now(), sequence=1, device='audit', data_id=f"{rest_method}{path}",
                                          value_text=user,
                                          value_add={k:v for (k, v) in bmasked.items() if k != "credentials"})
                            await put_log_write(None, [d])
                        except Exception as e:
                            raise I4cClientError(f"Error while logging: {e}")
                return await f(*a, **b)
            return func(log_result)
        return log_decorator

    def calc_full_path(self, path):
        return self.include_path + path

    def check_router_add(self):
        if self.router_included:
            raise Exception("router already included. Do not add new methods or include again.")

    def proc_special(self, method, path, kwargs):
        self.check_router_add()
        if "x_properties" in kwargs:
            self.openapi_extra.append((method, path, kwargs.pop("x_properties")))
        allow_log = True
        if "allow_log" in kwargs:
            allow_log = kwargs.pop("allow_log")
        features = []
        if "features" in kwargs:
            features = kwargs.pop("features")
        self.path_list.append(I4cApiRouterPath(method + self.calc_full_path(path), features))
        return allow_log, kwargs


    def get(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('get',path,kwargs)
        func = super().get(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'GET', allow_log=allow_log)

    def put(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('put',path,kwargs)
        func = super().put(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'PUT', allow_log=allow_log)

    def post(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('post',path,kwargs)
        func = super().post(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'POST', allow_log=allow_log)

    def delete(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('delete',path,kwargs)
        func = super().delete(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'DELETE', allow_log=allow_log)

    def options(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('options',path,kwargs)
        func = super().options(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'OPTIONS', allow_log=allow_log)

    def head(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('head',path,kwargs)
        func = super().head(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'HEAD', allow_log=allow_log)

    def patch(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('patch',path,kwargs)
        func = super().patch(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'PATCH', allow_log=allow_log)

    def trace(self, path: str, *args, **kwargs):
        allow_log, kwargs = self.proc_special('trace',path,kwargs)
        func = super().trace(path, *args, **kwargs)
        return self.func_extra(func, self.calc_full_path(path), 'TRACE', allow_log=allow_log)

    def include_router(self, router, *args, **kwargs):
        self.check_router_add()
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

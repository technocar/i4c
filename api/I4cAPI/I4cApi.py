import re

from fastapi import Depends, FastAPI, Request
from .I4cApiRouter import I4cApiRouter
from typing import Awaitable, TypeVar
import asyncio

T = TypeVar("T")


class CancelOnDisconnect:
    """
    Dependency that can be used to wrap a coroutine,
    to cancel it if the request disconnects
    """

    def __init__(self, request: Request) -> None:
        self.request = request

    async def _poll(self):
        """
        Poll for a disconnect.
        If the request disconnects, stop polling and return.
        """
        try:
            while not await self.request.is_disconnected():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def __call__(self, awaitable: Awaitable[T]) -> T:
        """Run the awaitable and cancel it if the request disconnects"""

        # Create two tasks, one to poll the request and check if the
        # client disconnected, and another which wraps the awaitable
        poller_task = asyncio.ensure_future(self._poll())
        main_task = asyncio.ensure_future(awaitable)

        _, pending = await asyncio.wait(
            [poller_task, main_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel any outstanding tasks
        for t in pending:
            t.cancel()

            try:
                await t
            except asyncio.CancelledError:
                pass  # print(f"{t} was cancelled")
            except Exception as exc:
                pass  # print(f"{t} raised {exc} when being cancelled")

        # This will:
        # - Raise asyncio.CancelledError if the handler was cancelled
        # - Return the value if it ran to completion
        # - Raise any other stored exception, if the task raised it
        return await main_task


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

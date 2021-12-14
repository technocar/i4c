# -*- coding: utf-8 -*-
from typing import List
from common import I4cBaseModel

path_list = []


class Priv(I4cBaseModel):
    endpoint: str
    features: List[str]


class Role(I4cBaseModel):
    name: str
    subroles: List[str]
    privs: List[Priv]


async def get_roles(credentials):
    # todo 1: *****
    pass


async def get_priv(credentials):
    return [Priv(endpoint=p.path, features=p.features) for p in path_list]

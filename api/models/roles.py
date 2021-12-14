# -*- coding: utf-8 -*-
from typing import List
from common import I4cBaseModel


class Priv(I4cBaseModel):
    endpoint: str
    features: List[str]


class Role(I4cBaseModel):
    name: str
    subroles: List[str]
    privs: List[Priv]


async def get_roles(credentials, path_list):
    res = [Role(name="aaa", subroles=[], privs=[Priv(endpoint=p.path, features=p.features) for p in path_list])]
    # todo 1: *****
    return res

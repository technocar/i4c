from typing import Union
from fastapi import UploadFile
from fastapi.security import HTTPBasicCredentials
from common import I4cBaseModel


class FileDetail(I4cBaseModel):
    name:str
    ver: int
    size: int
    hash: str


async def intfiles_list(credentials, name, min_ver, max_ver, hash):
    # todo 1: **********
    pass


async def intfiles_get(credentials, ver, path):
    # todo 1: **********
    return r'c:\Gy\SQL\truncate_log.ssr'


async def intfiles_put(
    credentials: HTTPBasicCredentials,
    ver: int,
    path: str,
    file: Union[UploadFile, bytes]
):
    print(type(file))
    print(f'{ver=}, {path=}')
    if isinstance(file, UploadFile):
        str = await file.read()
        print(f'{file.filename=}')
    else:
        str = file
    print(f'len={len(str)} - {str[:100]}')
    return len(str), str[:100].hex()


async def intfiles_delete(credentials, ver, path):
    # todo 1: **********
    pass

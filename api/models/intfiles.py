from typing import Union
from fastapi import UploadFile
from fastapi.security import HTTPBasicCredentials


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

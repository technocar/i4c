from fastapi import UploadFile
from fastapi.security import HTTPBasicCredentials


async def intfiles_put(
    credentials: HTTPBasicCredentials,
    ver: int,
    path: str,
    file: UploadFile
):
    print(f'{ver=}, {path=}')
    str = await file.read()
    print(f'{file.filename=} len={len(str)} - {str[:100]}')

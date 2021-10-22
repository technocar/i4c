# coding=utf-8
import sys
from textwrap import dedent

from fastapi import HTTPException, status
from datetime import datetime, timezone
import hashlib
import secrets
import base64
import nacl
import nacl.encoding
import nacl.signing
from .db_pool import DatabaseConnection
from common import log


def check_password(password, verifier):
    if type(password) == str:
        password = str.encode(password)
    salt, good_digest = verifier[:24], verifier[24:]
    salt = base64.b64decode(salt)
    good_digest = base64.b64decode(good_digest)
    given_digest = hashlib.pbkdf2_hmac('sha512', password, salt, 10000)[0:18]   # truncated to 144 bits, which is b64 aligned and >128
    return secrets.compare_digest(good_digest, given_digest)


def create_password(password):
    if type(password) == str:
        password = str.encode(password)
    salt = secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac('sha512', password, salt, 10000)[0:18]   # truncated to 144 bits, which is b64 aligned and >128
    verifier = base64.b64encode(salt).decode('ascii') + base64.b64encode(digest).decode('ascii')
    return verifier


async def authenticate(login, password, *, pconn=None):
    log.debug(f"Auth check user {login}")
    sql = dedent("""\
            select 
              u."password_verifier" as verifier, 
              u.public_key
            from public."user"
            where 
              u."login_name" = $1
              and u."status" = 'active'
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetch(sql, login)
    if not res:
        log.info(f"Auth unknown user {login}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Basic"} )
    res = res[0]

    pubkey = res["public_key"]
    if pubkey:
        try:
            timestr, signature = password[0:14], password[14:]
            tm = datetime.strptime(timestr, "%Y%m%d%H%M%S")
            tm = tm.replace(tzinfo=timezone.utc)
            now = datetime.now().astimezone(timezone.utc)
        except:
            log.info(f"Auth wrong timestamp for user {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"} )

        if not (-60 < (now - tm).total_seconds() < 60):
            log.info(f"Auth timestamp too old for user {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"} )

        try:
            verify = nacl.signing.VerifyKey(pubkey, encoder=nacl.encoding.Base64Encoder)
            signature = base64.b64decode(signature)
            timestr = timestr.encode()
            verify.verify(timestr, signature)
            log.debug(f"Authentication signature ok for {login}")
            return
        except:
            log.info(f"Auth signature verify for user {login} throws {sys.exc_info()[0]}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed")

    verifier = res["verifier"]
    if verifier:
        if not check_password(password, verifier):
            log.info("Auth password wrong")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"} )
        return

    log.info(f"Auth method undefined for user {login}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed",
        headers={"WWW-Authenticate": "Basic"} )

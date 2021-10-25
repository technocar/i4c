# coding=utf-8
from functools import reduce
from datetime import datetime, timezone
import hashlib
import secrets
import base64
import logging
import nacl
import nacl.encoding
import nacl.exceptions
import nacl.signing
from .db_pool import DatabaseConnection

log = None


def pbkdf(password, salt):
    return hashlib.pbkdf2_hmac('sha512', password, salt, 10000)[0:18]    # truncated to 144 bits, which is b64 aligned and >128


def check_password(password, verifier):
    if type(password) == str:
        password = str.encode(password)
    salt, good_digest = verifier[:24], verifier[24:]
    salt = base64.b64decode(salt)
    good_digest = base64.b64decode(good_digest)
    given_digest = pbkdf(password, salt)
    return secrets.compare_digest(good_digest, given_digest)


def create_password(password):
    if type(password) == str:
        password = str.encode(password)
    salt = secrets.token_bytes(18)
    digest = pbkdf(password, salt)
    verifier = base64.b64encode(salt).decode('ascii') + base64.b64encode(digest).decode('ascii')
    return verifier


async def authenticate(login, password=None, endpoint=None, need_features=None, ask_features=None):
    """ Authenticate and/or authorize user/endpoint

    If password is given, it will be checked against the verifier or public key, whichever is configured for the user.
    If the user is inactive, the authentication will fail. If the user does not have access to any endpoints, the
    authentication will fail even if the endpoint parameter is None.

    If endpoint is given, authorization will be checked for that endpoint. If need_features are given, all the features
    are required, or else the authentication fails.

    :param login: login name
    :param password: password if authentication is requested
    :param endpoint: endpoint if authorization is requested
    :param need_features: if these features are not configured, fail
    :param ask_features: check if these features are granted
    :return: tuple (user_id, features) user_id is None if the authentication fails
    """

    global log
    if not log:
        log = logging.getLogger("api")

    log.debug(f"auth user {login}")

    # getting data for user/endpoint

    sql = """with
              recursive deep_role_r as
                (select distinct role as toprole, role as midrole, role as subrole from role_subrole
                 union
                 select deep_role_r.toprole, role_subrole.role as midrole, role_subrole.subrole
                 from deep_role_r join role_subrole on deep_role_r.subrole = role_subrole.role),
              deep_role as (select distinct toprole as role, subrole from deep_role_r)
            select role_grant.features, "user".id, "user".status, "user".password_verifier, "user".public_key
            from "user"
            join user_role on "user".id = user_role."user"
            join deep_role on deep_role.role = user_role."role"
            join role_grant on deep_role.subrole = role_grant."role"
            where "user".login_name = $1
            """
    params = (login,)

    if endpoint is not None:
        sql = sql + " and role_grant.endpoint = $2"
        params = (*params, endpoint)

    log.debug(f"auth acquiring")
    async with DatabaseConnection() as connection:
        log.debug(f"auth selecting")
        rs = await connection.fetch(sql, *params)
        log.debug(f"auth select fin")

    if not rs:
        log.debug(f"auth fail, no user-endpoint")
        return None, set()

    r = rs[0]
    uid = r["id"]
    status = r["status"]
    verifier = r["password_verifier"]
    pubkey = r["public_key"]

    if status != "active":
        log.debug(f"auth fail, user inactive")
        return None, set()

    # check authentication

    if password is not None:
        if pubkey:
            try:
                timestr, signature = password[0:14], password[14:]
                tm = datetime.strptime(timestr, "%Y%m%d%H%M%S")
                tm = tm.replace(tzinfo=timezone.utc)
                now = datetime.now().astimezone(timezone.utc)
            except:
                log.debug(f"auth fail, timestamp fmt bad")
                return None, set()

            if not (-60 < (now - tm).total_seconds() < 60):
                log.debug(f"auth fail, timestamp old")
                return None, set()

            try:
                verify = nacl.signing.VerifyKey(pubkey, encoder=nacl.encoding.Base64Encoder)
                signature = base64.b64decode(signature)
                timestr = timestr.encode()
                verify.verify(timestr, signature)
                log.debug(f"auth signature ok")
            except nacl.exceptions.BadSignatureError:
                log.debug(f"auth fail, signature bad")
                return None
            except Exception as e:
                log.error(f"auth fail, signature verify for user {login} throws {e}")
                return None, set()

        elif verifier:
            if not check_password(password, verifier):
                log.debug("auth password bad")
                return None, set()
            log.debug("auth password ok")

        else:
            log.debug(f"auth fail, method undefined")
            return None, set()

    # check authorization

    info_features = set()
    granted_features = None
    if endpoint:
        if need_features or ask_features:
            granted_features = reduce(lambda a1, a2: a1 + a2, (r["features"] for r in rs))

        if need_features:
            if any(f not in granted_features for f in need_features):
                log.debug(f"auth fail, missing feature")
                return None, set()
        log.debug(f"auth endpoint pass")
        
        if ask_features:
            info_features = set(f for f in ask_features if f in granted_features)

    log.debug(f"auth ok")
    return uid, info_features

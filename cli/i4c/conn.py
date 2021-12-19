import os
import yaml
import json
import base64
import datetime
import urllib.request
import nacl.signing
import nacl.encoding
from .apidef import I4CDef
from .tools import jsonify


def public_key(private_key):
    if isinstance(private_key, str):
        private_key = nacl.signing.SigningKey(private_key, encoder=nacl.encoding.Base64Encoder)
    elif not isinstance(private_key, nacl.signing.SigningKey):
        private_key = nacl.signing.SigningKey(private_key)
    pub = private_key.verify_key
    pub = pub.encode(encoder=nacl.encoding.Base64Encoder).decode()
    return pub


def keypair_create():
    pri = nacl.signing.SigningKey.generate()
    pub = public_key(pri)
    pri = pri.encode(encoder=nacl.encoding.Base64Encoder).decode()
    return pri, pub


def _load_profile(profile_file, require_exist=True):
    if not os.path.isfile(profile_file):
        if require_exist:
            raise Exception("Unable to read profile information")
        else:
            return None
    # on linux, check file attrs
    if os.name == "posix":
        mode = os.stat(profile_file).st_mode
        if mode & 0o177 != 0:
            raise Exception("Profile refused because of improper access rights")

    with open(profile_file, "r") as f:
        data = yaml.safe_load(f)

    return data


def sign(private_key, data):
    """
    Signs `data` with `private_key`, and returns the signature.

    :param private_key: the private key, can be bytes, base64 encoded str or SigningKey
    :param data: the data to sign, str or bytes
    :return: base64 encoded signature
    """
    if isinstance(private_key, str):
        private_key = nacl.signing.SigningKey(private_key, encoder=nacl.encoding.Base64Encoder)
    elif not isinstance(private_key, nacl.signing.SigningKey):
        private_key = nacl.signing.SigningKey(private_key)
    if isinstance(data, str):
        data = data.encode()
    signature = private_key.sign(data) # sign return a weirdo bytes derived class that combines message and signature
    signature = signature.signature # we only need the signature
    signature = base64.b64encode(signature).decode()
    return signature


class I4CConnection:
    _api_def: I4CDef
    api_def_file: str
    profile_file: str
    base_url: str
    profile: str
    user: str
    password: str
    private_key: str

    def __init__(self, *, profile_file=None, api_def=None, base_url=None, api_def_file=None, profile=None, user=None, password=None, private_key=None):
        if not profile_file:
            profile_file = os.environ.get("i4c-profile", None)
        if not profile_file:
            profile_file = os.path.expanduser("~") + "/.i4c/profiles"

        if not user or not (password or private_key) or not base_url or not profile:
            p = _load_profile(profile_file, require_exist=True)
            if not profile:
                profile = p.get("default", None)
            if not profile:
                raise Exception("Authentication is incomplete, and no profile is given")
            p = p.get(profile, {})
            if not user:
                user = p.get("user", profile)
            if not password:
                password = p.get("password", None)
            if not private_key:
                private_key = p.get("private-key", None)
            if not base_url:
                base_url = p.get("base-url")
            if not api_def_file:
                api_def_file = p.get("api-def-file")
            # TODO openapi file to the profile and then store

        if base_url.endswith("/"):
            base_url = base_url[:-1]

        self._api_def = api_def
        self.api_def_file = api_def_file
        self.base_url = base_url
        self.profile = profile
        self.user = user
        self.password = password
        self.private_key = private_key

    def invoke_url(self, url, method=None, data=None, bindata=None, jsondata=None, data_content_type=None):
        """
        Call the specified sub-url. Base url is prepended, and authentication is taken care of.

        :param url: relative url including path and query. Initial / can be included or omitted.
        :param method: GET | PUT | POST | PATCH | DEL. If omitted, defaults to GET if no data, POST if there is data.
        :param data: request body. Content type and transformations are heuristic. For more control, consider using
                     jsondata or bindata instead, and/or specify data_content_type.
                     Dict or list will be converted to json, submitted as application/json.
                     Bytes will be submitted verbatim as application/octet-stream.
                     Str will be submitted as plain/text.
        :param bindata: will be passed as request body. Content-Type will be application/octet-stream
        :param jsondata: will be converted to json, and passed as request body. Content type will be application/json.
        :param data_content_type: if given, it will override the automatic Content-Type for the body.
        :return: Dict for json payloads, None for 204, otherwise the HTTPResponse.
        """

        if not method:
            if data is None and jsondata is None and bindata is None:
                method = "GET"
            else:
                method = "POST"

        headers = {}
        if self.private_key:
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            signature = sign(self.private_key, timestamp)
            token = f"{self.user}:{timestamp}{signature}"
            token = token.encode()
            token = base64.b64encode(token).decode()
            headers["Authorization"] = f"Basic {token}"
        elif self.password:
            token = f"{self.user}:{self.password}"
            token = token.encode()
            token = base64.b64encode(token).decode()
            headers["Authorization"] = f"Basic {token}"

        if jsondata is not None:
            body = jsonify(jsondata).encode()
            headers["Content-Type"] = "application/json"
        elif bindata is not None:
            body = bindata
            headers["Content-Type"] = "application/octet-stream"
        elif isinstance(data, dict) or isinstance(data, list):
            body = jsonify(data).encode()
            headers["Content-Type"] = "application/json"
        elif isinstance(data, bytes):
            headers["Content-Type"] = "application/octet-stream"
            body = data
        elif isinstance(data, str):
            headers["Content-Type"] = "text/plain"
            body = data
        else:
            body = data

        if data_content_type is not None:
            headers["Content-Type"] = data_content_type

        if not url.startswith("/"):
            url = "/" + url
        url = self.base_url + url

        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        conn = urllib.request.urlopen(req)

        if conn.getcode() == 204:
            response = None
        elif conn.headers.get_content_type() == "application/json":
            response = json.load(conn)
        else:
            response = conn

        return response

    def api_def(self):
        if self._api_def is None:
            self._api_def = I4CDef(base_url=self.base_url, def_file=self.api_def_file)
        return self._api_def

    def invoke(self, obj, action=None, **params):
        """
        Invokes a logical function, as defined by the interface. Logical functions and objects are defined in the api
        as x-properties (x-object and x-action). If the interface does not define logical objects, they will be
        automatically generated from paths. Get information about the available logical functions with
        .api_def().objects()

        :param obj: logical object, as defined by the interface.
        :param action: logical action, as defined by the interface.
        :param body: request body.
        :param params: all other named parameters represent path and query parameters, and the body.
        :return: Dict for json payloads, None for 204, otherwise the HTTPResponse.
        """

        if "body" in params:
            body = params.pop("body")
        else:
            body = None

        method, url = self.api_def().assemble_url(obj, action, **params)
        body, content_type = self.api_def().prepare_body(obj, action, body)

        return self.invoke_url(url, method, bindata=body, data_content_type=content_type)
import sys
import i4c
import json
from urllib.error import HTTPError
from py_vapid.utils import b64urlencode
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization

i4c_conn = None
overwrite_key = False


def init_globals():
    global i4c_conn
    global overwrite_key

    overwrite_key = "--overwrite" in sys.argv
    i4c_conn = i4c.I4CConnection(profile=None)


def main():
    vapid = Vapid()
    vapid.generate_keys()

    priv_key = (ln for ln in vapid.private_pem().split(b"\n") if not ln.startswith(b"--") and ln != b"")
    priv_key = b"".join(priv_key).decode()

    pub_key = vapid.public_key
    pub_key = pub_key.public_bytes(serialization.Encoding.X962,
                                   serialization.PublicFormat.UncompressedPoint)
    pub_key = b64urlencode(pub_key)

    try:
        key_exists = i4c_conn.settings.get(key="push_priv_key") is not None
        key_exists = key_exists or i4c_conn.settings.get(key="push_public_key") is not None
    except Exception as err:
        print(f"{err}")
        exit(1)

    if not key_exists or overwrite_key:
        try:
            i4c_conn.settings.set(key="push_priv_key", body={"value": priv_key})
            i4c_conn.settings.set(key="push_public_key", body={"value": pub_key})
            print(f"Keys are set")
            exit(0)
        except Exception as err:
            print(f"{err}")
            exit(2)
    else:
        print(f"Keys already set. Add --overwrite if you wish.")

if __name__ == '__main__':
    try:
        init_globals()
        main()

    except Exception as e:
        print(f"error: {e}")
        raise
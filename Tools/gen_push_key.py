import sys
import i4c
from urllib.error import HTTPError
from py_vapid.utils import b64urlencode
from py_vapid import Vapid

from cryptography.hazmat.primitives import serialization

i4c_conn = None
overwrite_key = False


def init_globals():
    global i4c_conn
    global overwrite_key

    overwrite_key = not (next((opt for opt in sys.argv if opt == "--overwrite"), None) is None)
    i4c_conn = i4c.I4CConnection(profile=None)

def main():
    vapid = Vapid()
    vapid.generate_keys()
    priv_key = b"".join(ln for ln in (vapid.private_pem().split(b"\n")) if not ln.startswith(b"--") and ln != b"").decode()
    pub_key = b64urlencode(vapid.public_key.public_bytes(serialization.Encoding.X962,
                                            serialization.PublicFormat.UncompressedPoint
    ))

    key_exists = True
    try:
        i4c_conn.settings.get(key="push_priv_key")
    except HTTPError as err:
        if err.code == 404:
            key_exists = False
    except Exception as err:
        print(f"Error: {err}")
        exit(1)

    if not key_exists or overwrite_key:
        try:
            body = {"value": priv_key}
            i4c_conn.settings.set(key="push_priv_key", body=body)
            body = {"value": pub_key}
            i4c_conn.settings.set(key="push_public_key", body=body)
            print(f"Keys are set")
            exit(0)
        except HTTPError as err:
            if not err.fp is None:
                print(err.code, err.fp.read())
            else:
                print(err.code, err.msg)
        except Exception as err:
            print(f"Error: {err}")
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
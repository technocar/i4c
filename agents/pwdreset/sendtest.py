import os
import re
import sys
import base64
import time
import yaml
import logging.config
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import jinja2
import i4c


log = None # will be filled in from main


def fail(msg, exit_code=1):
    global log
    if msg is not None:
        print(f"{msg}")
    log.debug(f"fail {exit_code} {msg}")
    sys.exit(exit_code)


def main():
    if os.path.isfile("pwdreset.conf"):
        with open("pwdreset.conf", "r") as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
    else:
        conf = {}

    if "log" in conf:
        logging.config.dictConfig(conf["log"])

    global log
    log = logging.getLogger()
    log.debug("start")

    svr = conf.get("smtp-server", None)
    port = conf.get("smtp-port", None)
    uid = conf.get("smtp-user", None)
    pwd = conf.get("smtp-password", None)
    sender = conf.get("smtp-from", None)
    protocol = conf.get("smtp-protocol", None)

    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    if not profile and "profile" in conf:
        profile = conf["profile"]
    log.debug(f"profile: {profile}")

    log.debug("accessing profile")
    conn = i4c.I4CConnection(profile=profile)
    extra = conn.profile_data.get("extra", {})
    svr = svr or extra.get("smtp-server", None)
    port = port or extra.get("smtp-port", None)
    uid = uid or extra.get("smtp-user", None)
    pwd = pwd or extra.get("smtp-password", None)
    sender = sender or extra.get("smtp-from", None)
    protocol = protocol or extra.get("smtp-protocol", "starttls")

    if svr is None:
        log.debug("no server is given, falling back to localhost")
        svr = "127.0.0.1"

    if protocol not in ("ssl", "starttls", "plain"):
        fail(f"Smtp protocol must be tls, starttls or plain. '{protocol}' was given.")

    log.debug(f"smtp settings: {protocol} {svr}:{port} user:{uid} from:{sender}")

    if os.path.isfile("test.json"):
        with open("test.json", encoding="UTF-8") as f:
            r = json.load(f)
    elif os.path.isfile("test.txt"):
        with open("test.txt", encoding="UTF-8") as f:
            r = f.read()
            r = r.strip()
            r = {"email": r}
    else:
        r = {"email": "info@technocar.hu"}

    sep = base64.urlsafe_b64encode(os.urandom(15)).decode()

    email = r["email"]
    token = r.get("token", "XXTOKENXX")
    login = r.get("loginname", "LOGIN@NAME")
    log.info(f"sending to {email} for {login}")

    if os.path.isfile("pwdreset.subj"):
        with open("pwdreset.subj", "r", encoding="utf-8") as f:
            subject = f.readline()
    else:
        subject = "I4C jelszó"

    if os.path.isfile("pwdreset.text"):
        with open("pwdreset.text", "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = None

    if os.path.isfile("pwdreset.html"):
        with open("pwdreset.html", "r", encoding="utf-8") as f:
            html = f.read()
    else:
        html = None

    log.debug("rendering")
    env = jinja2.Environment()
    if text:
        text = env.from_string(text)
        text = text.render(token=token, login=login)
    if html:
        html = env.from_string(html)
        html = html.render(token=token, login=login)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email
    if text and html:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    elif text:
        msg.set_content(text)
    elif html:
        msg.set_content(html, subtype="html")
    else:
        fail("Missing pwdreset.text and/or pwdreset.html")

    with open("outgoing.eml", "wb") as f:
        f.write(msg.as_bytes())

    log.debug("connecting")
    if protocol == "ssl":
        mailer = smtplib.SMTP_SSL(svr, port=port)
    elif protocol == "starttls":
        mailer = smtplib.SMTP(svr, port=port)
        mailer.starttls()
    else:
        mailer = smtplib.SMTP(svr, port=port)
    if uid:
        log.debug("authenticating")
        mailer.login(uid, pwd)

    mailer.send_message(msg)

    log.debug("finished")


if __name__ == '__main__':
    main()

import os
import re
import sys
import base64
import time
import yaml
import logging.config
import smtplib
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

    if not os.path.isfile("pwdreset.template"):
        fail("Missing pwdreset.template")

    with open("pwdreset.template", "r", encoding="utf-8") as f:
        tmpl = f.read()

    env = jinja2.Environment()
    tmpl = env.from_string(tmpl)

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
    token = r.get("token", "TOKEN")
    login = r.get("loginname", "LOGINNAME")
    log.info(f"sending to {email} for {login}")

    log.debug("rendering")
    mail_body = tmpl.render(email=email, token=token, login=login, sep=sep, sender=sender)
    mail_body = mail_body.encode("utf-8")
    with open("outgoing.eml", "wb") as f:
        f.write(mail_body)

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

    mailer.ehlo_or_helo_if_needed()
    mailopt = ("BODY=8BITMIME",) if "8bitmime" in mailer.esmtp_features else ()
    log.debug(f"mail opt: {'|'.join(mailopt)}")

    log.debug("sending")
    mailer.sendmail(sender, [email], mail_body, mail_options=mailopt)

    log.debug("finished")


if __name__ == '__main__':
    main()

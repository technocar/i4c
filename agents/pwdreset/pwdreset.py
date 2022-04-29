import os
import re
import sys
import base64
import time
import yaml
import logging.config
import smtplib
from email.message import EmailMessage
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

    options = {opt: opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt.startswith("--")}

    poll = options.get("poll")
    if not poll and "poll" in conf:
        poll = conf["poll"]
    if poll:
        m = re.fullmatch(r"0*([1-9]\d*)\s*(m?s)", poll)
        if not m:
            fail(f"Poll must be positive integer seconds (5s) or milliseconds (200ms). {poll} was given.")
        poll = int(m[1])
        if m[2] == "ms":
            poll = poll / 1000.0
    log.debug(f"poll: {poll}")

    svr = conf.get("smtp-server", None)
    port = conf.get("smtp-port", None)
    uid = conf.get("smtp-user", None)
    pwd = conf.get("smtp-password", None)
    sender = conf.get("smtp-from", None)
    protocol = conf.get("smtp-protocol", None)

    profile = options.get("--profile")
    if not profile and "profile" in conf:
        profile = conf["profile"]
    log.debug(f"profile: {profile}")

    log.debug("accessing profile")
    conn = i4c.I4CConnection(profile=profile)
    extra = conn.profile_data.get("extra", {})
    svr = svr or extra.get("smtp-server")
    port = port or extra.get("smtp-port")
    uid = uid or extra.get("smtp-user")
    pwd = pwd or extra.get("smtp-password")
    sender = sender or extra.get("smtp-from")
    protocol = protocol or extra.get("smtp-protocol") or "starttls"

    if svr is None:
        log.debug("no server is given, falling back to 127.0.0.1")
        svr = "127.0.0.1"

    if protocol not in ("ssl", "starttls", "plain"):
        fail(f"Smtp protocol must be tls, starttls or plain. '{protocol}' was given.")

    log.debug(f"smtp settings: {protocol} {svr}:{port} user:{uid} from:{sender}")

    env = jinja2.Environment()

    if os.path.isfile("pwdreset.subj"):
        with open("pwdreset.subj", "r", encoding="utf-8") as f:
            subject = f.readline()
    else:
        subject = "I4C jelszó"

    if os.path.isfile("pwdreset.text"):
        with open("pwdreset.text", "r", encoding="utf-8") as f:
            log.debug("reading pwdreset.text")
            text_tmpl = f.read()
            log.debug("parsing")
            text_tmpl = env.from_string(text_tmpl)
    else:
        text_tmpl = None

    if os.path.isfile("pwdreset.html"):
        with open("pwdreset.html", "r", encoding="utf-8") as f:
            log.debug("reading pwdreset.html")
            html_tmpl = f.read()
            log.debug("parsing")
            html_tmpl = env.from_string(html_tmpl)
    else:
        html_tmpl = None

    if text_tmpl is None and html_tmpl is None:
        fail("Missing pwdreset.text and/or pwdreset.html")

    while True:
        log.debug("getting pwdreset list")
        try:
            resets = conn.pwdreset.list(noaudit=True)
            log.debug(f"got {len(resets)} items")
        except Exception as e:
            log.error(f"Error reading pwdreset list: {e}")
            resets = []

        for r in resets:
            email = r["email"]
            token = r["token"]
            login = r["loginname"]
            log.info(f"sending to {email} for {login}")

            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = email

            text = None
            html = None
            if text_tmpl:
                log.debug("rendering text")
                text = text_tmpl.render(token=token, login=login)
            if html_tmpl:
                log.debug("rendering html")
                html = html_tmpl.render(token=token, login=login)

            if text_tmpl and html_tmpl:
                msg.set_content(text)
                msg.add_alternative(html, subtype="html")
            elif text_tmpl:
                msg.set_content(text)
            elif html_tmpl:
                msg.set_content(html, subtype="html")

            try:
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

                log.debug("sending")
                mailer.send_message(msg)

                try:
                    log.debug("marking as sent")
                    conn.pwdreset.mark_sent(body={"loginname": login})
                except Exception as e:
                    log.error(f"failed to mark {login} as sent: {e}")

            except smtplib.SMTPRecipientsRefused as e:
                try:
                    log.debug("marking as fail")
                    conn.pwdreset.mark_fail(body={"loginname": login})
                except Exception as e2:
                    log.error(f"failed to mark as failed: {e2}")

                log.error(f"failed mailing for {login}: {e}")

            except Exception as e:
                log.error(f"failed mailing for {login}: {type(e)} {e}")

        if not poll:
            break

        log.debug("waiting")
        time.sleep(poll)

    log.debug("finished")


if __name__ == '__main__':
    main()

import sys
import os
import re
import time
import json
import i4c
import urllib.parse
import yaml
import logging.config
import smtplib
import jinja2
import base64

cfg = None
log = None
poll = 0
i4c_conn = None
svr = None
port = None
uid = None
pwd = None
sender = None
protocol = None
tmpl = ""


def fail(msg, exit_code=1):
    global log
    if msg is not None:
        print(f"{msg}")
    log.debug(f"fail {exit_code} {msg}")
    sys.exit(exit_code)

def init_globals():
    global cfg
    global log
    global poll
    global i4c_conn
    global svr
    global port
    global uid
    global pwd
    global sender
    global protocol
    global tmpl

    with open("alarm_email.conf", "r") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)

    if "log" in cfg:
        logging.config.dictConfig(cfg["log"])

    log = logging.getLogger("email_notif_agent")

    poll = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--poll"), None)
    poll = poll or cfg.get("poll", None)
    if poll:
        m = re.fullmatch(r"0*([1-9]\d*)\s*(m?s)", poll)
        if not m:
            raise Exception(f"Poll must be positive integer seconds (5s) or milliseconds (200ms). {poll} was given.")
        poll = int(m[1])
        if m[2] == "ms":
            poll = poll / 1000.0
    log.debug(f"poll: {poll}s")

    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    profile = profile or cfg.get("profile", None)
    log.debug(f"using profile {profile}")
    i4c_conn = i4c.I4CConnection(profile=profile)

    svr = cfg.get("smtp-server", None)
    port = cfg.get("smtp-port", None)
    uid = cfg.get("smtp-user", None)
    pwd = cfg.get("smtp-password", None)
    sender = cfg.get("smtp-from", None)
    protocol = cfg.get("smtp-protocol", None)

    extra = i4c_conn.profile_data.get("extra", {})
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

    if not os.path.isfile("alarm_email.template"):
        fail("Missing alarm_email.template")
    with open("alarm_email.template", "r", encoding="utf-8") as f:
        tmpl = f.read()
    env = jinja2.Environment()
    tmpl = env.from_string(tmpl)


def main():
    while True:
        log.debug("get alarm recips")
        #notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=email&noaudit=1')
        notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=email')
        for notif in notifs:
            ev = notif["event"]

            log.debug("rendering")
            sep = base64.urlsafe_b64encode(os.urandom(15)).decode()
            mail_body = tmpl.render(email=notif["address"], alarm=ev["alarm"], created=ev["created"], sep=sep,
                                    sender=sender, summary=ev["summary"])
            mail_body = mail_body.encode("utf-8")

            log.info(f'sending to {notif["address"]} for {ev["alarm"]}')
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
                mailer.sendmail(sender, notif["address"], mail_body)

                try:
                    log.debug("marking as sent")

                    chg = {"conditions": [{"status": ["outbox"]}],
                           "change": {"status": "sent"}}

                    i4c_conn.invoke_url(f'alarm/recips/{urllib.parse.quote(str(notif["id"]))}', 'PATCH',
                                        jsondata=chg)
                except Exception as e:
                    log.error(f'failed to mark {notif["address"]} as sent: {e}')

            except smtplib.SMTPRecipientsRefused as e:
                try:
                    log.debug("marking as fail")
                    chg = {"conditions": [{"status": ["outbox"]}],
                           "change": {"status": "failed"}}
                    i4c_conn.invoke_url(f'alarm/recips/{urllib.parse.quote(str(notif["id"]))}', 'PATCH',
                                        jsondata=chg)
                except Exception as e2:
                    log.error(f"failed to mark as failed: {e2}")

                log.error(f'failed mailing for {notif["address"]}: {e}')

        if not poll:
            break

        time.sleep(poll)

    log.debug("finished")


if __name__ == '__main__':
    try:
        init_globals()
        main()
    except Exception as e:
        log.error(f"error: {e}")
        raise


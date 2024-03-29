import sys
import re
import datetime
import time
import i4c
import urllib.parse
import yaml
import logging.config
import smtplib
from email.message import EmailMessage


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
    if poll: log.debug(f"poll: {poll} s")

    profile = next((opv for (opt, opv) in zip(sys.argv, sys.argv[1:]) if opt == "--profile"), None)
    profile = profile or cfg.get("profile", None)
    log.debug(f"using profile {profile}")
    i4c_conn = i4c.I4CConnection(profile=profile)
    extra = i4c_conn.profile_data.get("extra", {})

    svr = cfg.get("smtp-server", None) or extra.get("smtp-server", None)
    port = cfg.get("smtp-port", None) or extra.get("smtp-port", None)
    uid = cfg.get("smtp-user", None) or extra.get("smtp-user", None)
    pwd = cfg.get("smtp-password", None) or extra.get("smtp-password", None)
    sender = cfg.get("smtp-from", None) or extra.get("smtp-from", None)
    protocol = cfg.get("smtp-protocol", None) or extra.get("smtp-protocol", "starttls")

    if svr is None:
        log.debug("no server is given, falling back to localhost")
        svr = "127.0.0.1"

    if protocol not in ("ssl", "starttls", "plain"):
        fail(f"Smtp protocol must be tls, starttls or plain. '{protocol}' was given.")

    log.debug(f"smtp settings: {protocol} {svr}:{port} user:{uid} from:{sender}")


def set_status(id, status):
    try:
        log.debug(f"marking as {status}")
        chg = {"conditions": [{"status": ["outbox"]}], "change": {"status": status}}
        i4c_conn.invoke_url(f'alarm/recips/{id}', 'PATCH', jsondata=chg)
    except Exception as e:
        log.error(f"error while marking as {status}: {e}")


def set_backoff(id, fail_count, backoff):
    try:
        log.debug(f"setting backoff")
        chg = {"conditions": [{"status": ["outbox"]}],
               "change": {"backoff_until": backoff.isoformat(), "fail_count": fail_count}}
        i4c_conn.invoke_url(f'alarm/recips/{id}', 'PATCH', jsondata=chg)
    except Exception as e:
        log.error(f"error while setting backoff: {e}")


def main():
    while True:
        log.debug("get alarm recips")
        notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=email&noaudit=1&no_backoff=1')
        for notif in notifs:
            ev = notif["event"]
            id = notif["id"]

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

                msg = EmailMessage()
                msg['Subject'] = ev["summary"]
                msg['From'] = sender
                msg['To'] = notif["address"]
                msg.set_content(ev["description"])

                log.debug("sending")
                mailer.send_message(msg)

                set_status(id, "sent")

            except smtplib.SMTPRecipientsRefused as e:
                log.error(f'failed mailing for {notif["address"]}: {e}')
                set_status(id, 'failed')
            except Exception as e:
                fail_count = notif["fail_count"]
                if  fail_count > 3:
                    log.error(f'too many fails, giving up for {notif["address"]}: {e}')
                    set_status(id, 'failed')
                else:
                    log.error(f'temporary fail, retrying later for {notif["address"]}: {e}')
                    fail_count += 1
                    backoff = datetime.datetime.now().astimezone() + datetime.timedelta(seconds=10**fail_count)
                    set_backoff(id, fail_count, backoff)

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

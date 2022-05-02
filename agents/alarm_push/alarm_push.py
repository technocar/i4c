import sys
import re
import time
import datetime
import json
import i4c
import yaml
import logging.config
from pywebpush import webpush, WebPushException

cfg = None
log = None
poll = 0
i4c_conn = None

def init_globals():
    global cfg
    global log
    global poll
    global i4c_conn

    with open("alarm_push.conf", "r") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)

    if "log" in cfg:
        logging.config.dictConfig(cfg["log"])
    log = logging.getLogger("push_notif_agent")

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
        log.debug("get setting push_email")
        email = i4c_conn.invoke_url('settings/push_email?noaudit=1')

        log.debug("get setting push_priv_key")
        private_key = i4c_conn.invoke_url('settings/push_priv_key?noaudit=1')

        log.debug("get alarm recips")
        notifs = i4c_conn.invoke_url('alarm/recips?status=outbox&method=push&noaudit=1&no_backoff=1')
        for notif in notifs:
            ev = notif["event"]
            data = {
                "notification": {
                    "title": f'{ev["alarm"]} ({ev["created"]})',
                    "body": f'{ev["summary"]}',
                    "timestamp": f'{ev["created"]}',
                    "icon": "/assets/logo.png"
                }
            }

            log.info(f'Sending notif {notif["id"]} to {notif["user"]}')
            try:
                webpush(json.loads(notif["address"]),
                        json.dumps(data),
                        vapid_private_key=private_key,
                        vapid_claims={"sub": f"mailto:{email}"})
                try:
                    log.debug("marking as sent")
                    set_status(notif["id"], "sent")
                except Exception as e:
                    log.error(f"can't mark notif as sent: {e}")
            except WebPushException as e:
                fail_count = notif["fail_count"]
                if fail_count > 4:
                    log.error(f'too many fails, giving up for {notif["address"]}: {e}')
                    set_status(notif["id"], 'failed')
                else:
                    log.error(f'temporary fail, retrying later for {notif["address"]}: {e}')
                    fail_count += 1
                    backoff = datetime.datetime.now().astimezone() + \
                              datetime.timedelta(seconds=[1, 5, 10, 60, 240][fail_count - 1])
                    set_backoff(notif["id"], fail_count, backoff)
            except Exception as e:
                log.error(f"error while sending notification: {e}")
                set_status(notif["id"], 'failed')

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

